"""Three-timescale OR adaptation.

  S(t)   = state ∈ [0,1]    (1 = fully adapted, 0 = naive)
  τ_fast = 100 ms (Ca²⁺-CaM CNG closure)
  τ_med  = 30 s   (CaMKII attenuation of AC)
  τ_slow = 300 s  (GRK internalisation)

We track three components per OR; total attenuation = max of the three (the
slowest one to release dominates recovery).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(slots=True)
class AdaptationState:
    fast: dict[str, float] = field(default_factory=dict)
    med: dict[str, float] = field(default_factory=dict)
    slow: dict[str, float] = field(default_factory=dict)

    def attenuation(self, or_gene: str) -> float:
        """Combined attenuation ∈ [0,1]. Use max to model dominant slowest pool."""
        return max(
            self.fast.get(or_gene, 0.0), self.med.get(or_gene, 0.0), self.slow.get(or_gene, 0.0)
        )

    def all_attenuations(self) -> dict[str, float]:
        keys = set(self.fast) | set(self.med) | set(self.slow)
        return {k: self.attenuation(k) for k in keys}


_TAU = {"fast": 0.1, "med": 30.0, "slow": 300.0}
# Per-component max gain rate per second of full-occupancy stimulation.
# Slow component is the most "permanent" adaptation; fast clears almost instantly.
_GAIN = {"fast": 5.0, "med": 0.05, "slow": 0.005}


def step_adaptation(
    state: AdaptationState,
    occupancy: Mapping[str, float],
    dt_seconds: float,
) -> AdaptationState:
    """Advance state by `dt_seconds` given current OR-occupancy R(k).

    Each pool: dS/dt = gain·R·(1−S) − S/τ
    """
    new = AdaptationState()
    keys = set(state.fast) | set(state.med) | set(state.slow) | set(occupancy)
    for k in keys:
        R = max(0.0, min(1.0, occupancy.get(k, 0.0)))  # noqa: N806
        for label, target in (("fast", new.fast), ("med", new.med), ("slow", new.slow)):
            cur = getattr(state, label).get(k, 0.0)
            tau = _TAU[label]
            g = _GAIN[label]
            ds = (g * R * (1.0 - cur) - cur / tau) * dt_seconds
            target[k] = max(0.0, min(1.0, cur + ds))
    return new


if __name__ == "__main__":
    s = AdaptationState()
    # Hold OR7D4 at 80% for 5 minutes
    for i in range(60):
        s = step_adaptation(s, {"OR7D4": 0.8}, dt_seconds=5.0)
    print(f"After 5 min strong stim: {s.attenuation('OR7D4'):.3f}")
    # Recovery: 5 minutes off
    for i in range(60):
        s = step_adaptation(s, {"OR7D4": 0.0}, dt_seconds=5.0)
    print(f"After 5 min recovery:    {s.attenuation('OR7D4'):.3f}")
