"""Agent base: a rule-driven ``ActionSource`` with balances, PnL and a decision trace.

Agents are structured actors, not free-form personalities. Each step:

=====================  ==========================================================
Phase                  Agent does
=====================  ==========================================================
``STATE_OBSERVATION``  ``observe(ctx)`` -> ``last_obs`` (prices, deviation, balances)
``AGENT_DECISION``     the kernel calls ``decide(ctx)``; one ``record(...)`` per call
``METRIC_UPDATE``      ``settle(ctx)``: balances from this step's results and fills
=====================  ==========================================================

Agents read protocol state through ``ctx.registry.get("amm" | "oracle" |
"redemption")`` and only ever change it by emitting actions. (The defender's
``redemption.set_spread_bps`` is the one sanctioned exception.) They never draw from
``ctx.rng``.

Balances are plain floats keyed ``"stable"`` and ``"reference"``. ``settle`` applies:

- each ``ok`` swap in ``ctx.execution_results`` whose ``action.source`` is this agent
  (``sell_stable``: stable -= amount_in, reference += amount_out; ``buy_stable``: the
  reverse), and
- each ``redeem_fulfilled`` event at this step whose ``payload["source"]`` is this agent
  (stable -= amount_stable, reference += paid_reference).

Stable that has been queued for redemption but not yet filled stays in
``balances["stable"]`` (the agent still owns it) and is also counted in
``queued_redeem``. ``available_stable`` is the part not already committed to the queue.

``initial_value`` is reference-denominated at ``peg_price``; ``mark_to_market`` uses the
AMM spot at call time; ``pnl_last`` is the PnL computed at the latest ``settle``.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

from depeg_sim.kernel.interfaces import Action, ActionSource
from depeg_sim.kernel.scheduler import Phase

if TYPE_CHECKING:
    from depeg_sim.kernel.context import RunContext

STABLE = "stable"
REFERENCE = "reference"
DUST = 1e-9  # balances below this are treated as empty


def action_record(action: Action) -> dict:
    """An ``Action`` in decision-trace form."""
    return {"target": action.target, "kind": action.kind, "params": dict(action.params)}


class Agent(ActionSource):
    type: ClassVar[str] = "agent"

    def __init__(
        self, agent_id: str, stable: float, reference: float, peg_price: float = 1.0
    ) -> None:
        if not agent_id:
            raise ValueError("agent_id must be non-empty")
        if not peg_price > 0:
            raise ValueError(f"peg_price must be > 0, got {peg_price}")
        self.agent_id = agent_id
        self.name = agent_id
        self.phases = frozenset(
            {Phase.STATE_OBSERVATION, Phase.AGENT_DECISION, Phase.METRIC_UPDATE}
        )
        self.peg_price = float(peg_price)
        self.balances: dict[str, float] = {STABLE: float(stable), REFERENCE: float(reference)}
        self.initial_value = self.balances[REFERENCE] + self.balances[STABLE] * self.peg_price
        self.queued_redeem = 0.0
        self.last_obs: dict[str, Any] = {}
        self.pnl_last = 0.0

    # -- registry helpers ----------------------------------------------------

    @staticmethod
    def _get(ctx: RunContext, name: str) -> Any | None:
        return ctx.registry.get(name) if name in ctx.registry else None

    def _amm(self, ctx: RunContext) -> Any | None:
        return self._get(ctx, "amm")

    def _oracle(self, ctx: RunContext) -> Any | None:
        return self._get(ctx, "oracle")

    def _redemption(self, ctx: RunContext) -> Any | None:
        return self._get(ctx, "redemption")

    @property
    def available_stable(self) -> float:
        """Stable held and not already queued for redemption."""
        return max(self.balances[STABLE] - self.queued_redeem, 0.0)

    # -- phases --------------------------------------------------------------

    def on_phase(self, ctx: RunContext, phase: Phase) -> None:
        if phase is Phase.STATE_OBSERVATION:
            self.last_obs = self.observe(ctx)
        elif phase is Phase.METRIC_UPDATE:
            self.settle(ctx)
        # AGENT_DECISION: the kernel calls decide() after this hook.

    def observe(self, ctx: RunContext) -> dict:
        """Prices, deviation and balances as of now. Subclasses extend it."""
        amm, oracle = self._amm(ctx), self._oracle(ctx)
        return {
            "step": ctx.clock.step_index,
            "spot_price": None if amm is None else amm.spot_price,
            "oracle_price": None if oracle is None else oracle.price,
            "peg_deviation": None if amm is None else amm.peg_deviation,
            "balances": dict(self.balances),
        }

    @abstractmethod
    def decide(self, ctx: RunContext) -> list[Action]: ...

    def settle(self, ctx: RunContext) -> None:
        for action, result in ctx.execution_results:
            if action.source != self.agent_id or not result.ok:
                continue
            if action.kind == "swap":
                d = result.detail
                if d["side"] == "sell_stable":
                    self.balances[STABLE] -= d["amount_in"]
                    self.balances[REFERENCE] += d["amount_out"]
                else:
                    self.balances[REFERENCE] -= d["amount_in"]
                    self.balances[STABLE] += d["amount_out"]
                self._on_swap(d)
            elif action.kind == "redeem":
                self.queued_redeem += result.detail["queued"]
        for event in ctx.events.at_step(ctx.clock.step_index):
            if event.kind == "redeem_fulfilled" and event.payload["source"] == self.agent_id:
                self.balances[STABLE] -= event.payload["amount_stable"]
                self.balances[REFERENCE] += event.payload["paid_reference"]
                self.queued_redeem = max(self.queued_redeem - event.payload["amount_stable"], 0.0)
        if self._amm(ctx) is not None:
            self.pnl_last = self.pnl(ctx)

    def _on_swap(self, detail: dict) -> None:
        """Hook for type-specific counters after one of this agent's swaps settles."""

    # -- valuation -------------------------------------------------------------

    def mark_to_market(self, ctx: RunContext) -> float:
        return self.balances[REFERENCE] + self.balances[STABLE] * self._amm(ctx).spot_price

    def pnl(self, ctx: RunContext) -> float:
        return self.mark_to_market(ctx) - self.initial_value

    # -- trace -----------------------------------------------------------------

    def record(
        self,
        ctx: RunContext,
        rule: str,
        observed: dict,
        action: dict | list[dict] | None,
    ) -> None:
        """Append one ``Decision`` when ``metrics.trace_decisions`` is on. Several
        actions in one step are passed as a list; the trace stores them as
        ``{"actions": [...]}`` (ADR-0011)."""
        if not ctx.config.metrics.trace_decisions:
            return
        ctx.decisions.record(
            step=ctx.clock.step_index,
            agent_id=self.agent_id,
            rule=rule,
            observed=observed,
            action=action,
        )

    def _swap(self, side: str, amount_in: float) -> Action:
        return Action(
            source=self.agent_id,
            target="amm",
            kind="swap",
            params={"amount_in": amount_in, "side": side},
        )

    # -- snapshot --------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "type": self.type,
            "balances": dict(self.balances),
            "initial_value": self.initial_value,
            "pnl_last": self.pnl_last,
            **self._snapshot_extra(),
        }

    def _snapshot_extra(self) -> dict:
        return {}
