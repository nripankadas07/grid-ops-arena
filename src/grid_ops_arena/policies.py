"""Dependency-free baseline policies implementing the action protocol."""

from typing import Any, Dict

from .model import Action


class GridFirstPolicy:
    name = "grid-first"

    def decide(self, observation: Dict[str, Any]) -> Action:
        net = observation["net_load_kw"]
        if net < 0:
            return Action(battery_kw=net, rationale="store renewable surplus")
        if observation["grid_available"]:
            return Action(rationale="use available grid and preserve storage")
        battery = min(net, observation["battery_max_power_kw"])
        return Action(
            battery_kw=battery,
            peaker_kw=max(0.0, net - battery),
            rationale="serve islanded load with battery then peaker",
        )


class BalancedPolicy:
    name = "balanced"

    def decide(self, observation: Dict[str, Any]) -> Action:
        net = observation["net_load_kw"]
        if net < 0:
            return Action(battery_kw=net, rationale="capture renewable surplus")
        if not observation["grid_available"]:
            battery = min(net, observation["battery_max_power_kw"])
            return Action(
                battery_kw=battery,
                peaker_kw=max(0.0, net - battery),
                rationale="island-mode reliability dispatch",
            )
        if observation["grid_price_per_kwh"] >= 0.22 and observation["soc_fraction"] > 0.35:
            return Action(
                battery_kw=min(net * 0.65, observation["battery_max_power_kw"]),
                rationale="discharge during synthetic high-price period",
            )
        return Action(rationale="use grid during lower-price period")


class ResiliencePolicy:
    name = "resilience"

    def decide(self, observation: Dict[str, Any]) -> Action:
        net = observation["net_load_kw"]
        if net < 0:
            return Action(battery_kw=net, rationale="charge from surplus")
        if observation["grid_available"]:
            return Action(rationale="reserve battery for outage")
        battery = min(net, observation["battery_max_power_kw"])
        return Action(
            battery_kw=battery,
            peaker_kw=max(0.0, net - battery),
            rationale="prioritize continuity during outage",
        )


POLICIES = {
    GridFirstPolicy.name: GridFirstPolicy,
    BalancedPolicy.name: BalancedPolicy,
    ResiliencePolicy.name: ResiliencePolicy,
}


def get_policy(name: str):
    try:
        return POLICIES[name]()
    except KeyError as exc:
        raise ValueError("unknown policy: {0}; choose from {1}".format(name, ", ".join(POLICIES))) from exc
