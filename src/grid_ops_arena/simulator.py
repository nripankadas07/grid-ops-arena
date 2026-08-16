"""Deterministic microgrid scenario generation and dispatch simulation."""

import math
import random
from dataclasses import asdict
from typing import Any, Dict, List

from . import SCHEMA_VERSION, __version__
from .model import Action, Event, GridConfig, Scenario


def _round(value: float) -> float:
    return round(float(value), 6)


def _finite(value: float, label: str) -> float:
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError("non-finite derived value for {0}".format(label))
    return normalized


def _finite_sum(label: str, *values: float) -> float:
    total = 0.0
    try:
        for value in values:
            total = _finite(total + float(value), label)
    except OverflowError as exc:
        raise ValueError("non-finite derived value for {0}".format(label)) from exc
    return total


def _finite_product(label: str, *values: float) -> float:
    product = 1.0
    try:
        for value in values:
            product = _finite(product * float(value), label)
    except OverflowError as exc:
        raise ValueError("non-finite derived value for {0}".format(label)) from exc
    return product


def _finite_ratio(numerator: float, denominator: float, label: str) -> float:
    try:
        return _finite(float(numerator) / float(denominator), label)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("non-finite derived value for {0}".format(label)) from exc


def _accumulate(totals: Dict[str, float], name: str, value: float) -> None:
    totals[name] = _finite_sum("total {0}".format(name), totals[name], value)


def _finite_action_value(
    value: Any, step: int, constraint: str, violations: List[Dict[str, Any]]
) -> float:
    if isinstance(value, bool):
        violations.append({"step": step, "constraint": constraint})
        return 0.0
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError):
        violations.append({"step": step, "constraint": constraint})
        return 0.0
    if not math.isfinite(normalized):
        violations.append({"step": step, "constraint": constraint})
        return 0.0
    return normalized


def build_demo_scenario(seed: int = 17, hours: int = 48) -> Scenario:
    if hours < 12:
        raise ValueError("demo requires at least 12 hours")
    rng = random.Random(seed)
    load: List[float] = []
    renewable: List[float] = []
    price: List[float] = []
    emissions: List[float] = []
    for step in range(hours):
        hour = step % 24
        morning = 12.0 * max(0.0, math.sin(math.pi * (hour - 5) / 12.0))
        evening = 18.0 * math.exp(-((hour - 19.0) ** 2) / 12.0)
        load.append(_round(max(35.0, 48.0 + morning + evening + rng.uniform(-3.5, 3.5))))
        solar = 48.0 * max(0.0, math.sin(math.pi * (hour - 6) / 12.0))
        wind = 10.0 + rng.uniform(-4.0, 5.0)
        renewable.append(_round(max(0.0, solar + wind)))
        price.append(0.26 if 17 <= hour <= 21 else (0.11 if hour <= 5 else 0.17))
        emissions.append(0.52 if 17 <= hour <= 21 else 0.34)

    outage_a = max(4, hours // 3)
    outage_b = max(outage_a + 3, (3 * hours) // 4)
    grid_available = [True] * hours
    for step in range(outage_a, min(hours, outage_a + 3)):
        grid_available[step] = False
    for step in range(outage_b, min(hours, outage_b + 2)):
        grid_available[step] = False
    peaker_available = [True] * hours
    if outage_b < hours:
        peaker_available[outage_b] = False
    derate_start = max(2, hours // 2)
    for step in range(derate_start, min(hours, derate_start + 4)):
        renewable[step] = _round(renewable[step] * 0.35)

    events = [
        Event("grid_outage", outage_a, min(hours - 1, outage_a + 2), "Synthetic feeder outage A"),
        Event("renewable_derate", derate_start, min(hours - 1, derate_start + 3), "Synthetic cloud-and-wind lull"),
        Event("grid_outage", outage_b, min(hours - 1, outage_b + 1), "Synthetic feeder outage B"),
        Event("peaker_unavailable", outage_b, outage_b, "Synthetic peaker start failure"),
    ]
    scenario = Scenario(
        scenario_id="synthetic-microgrid-seed-{0}".format(seed),
        seed=seed,
        load_kw=load,
        renewable_kw=renewable,
        grid_available=grid_available,
        peaker_available=peaker_available,
        grid_price_per_kwh=price,
        grid_emissions_kg_per_kwh=emissions,
        events=events,
    )
    scenario.validate()
    return scenario


def simulate(scenario: Scenario, policy: Any) -> Dict[str, Any]:
    scenario.validate()
    config = scenario.config
    soc = config.battery_initial_soc_kwh
    records: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []
    totals = {
        "load_kwh": 0.0,
        "renewable_available_kwh": 0.0,
        "grid_import_kwh": 0.0,
        "battery_discharge_kwh": 0.0,
        "battery_charge_kwh": 0.0,
        "peaker_kwh": 0.0,
        "unserved_kwh": 0.0,
        "curtailed_kwh": 0.0,
        "cost": 0.0,
        "emissions_kg": 0.0,
    }
    dt = config.timestep_hours

    for step, load in enumerate(scenario.load_kw):
        renewable = scenario.renewable_kw[step]
        observation = {
            "step": step,
            "load_kw": load,
            "renewable_kw": renewable,
            "net_load_kw": load - renewable,
            "battery_soc_kwh": soc,
            "soc_fraction": soc / config.battery_capacity_kwh,
            "battery_max_power_kw": config.battery_max_power_kw,
            "grid_available": scenario.grid_available[step],
            "peaker_available": scenario.peaker_available[step],
            "grid_price_per_kwh": scenario.grid_price_per_kwh[step],
        }
        action = policy.decide(dict(observation))
        if not isinstance(action, Action):
            raise TypeError("policy must return grid_ops_arena.model.Action")

        requested_battery = _finite_action_value(
            action.battery_kw, step, "finite_battery_action", violations
        )
        requested_peaker = _finite_action_value(
            action.peaker_kw, step, "finite_peaker_action", violations
        )

        if requested_battery >= 0:
            energy_limit = _finite_ratio(
                _finite_product("battery discharge energy limit", soc, config.discharge_efficiency),
                dt,
                "battery discharge energy limit",
            )
            battery_limit = min(requested_battery, config.battery_max_power_kw, energy_limit)
        else:
            charge_request = -requested_battery
            capacity_remaining = _finite_sum(
                "battery remaining capacity", config.battery_capacity_kwh, -soc
            )
            charge_denominator = _finite_product(
                "battery charge energy limit", config.charge_efficiency, dt
            )
            capacity_limit = _finite_ratio(
                capacity_remaining, charge_denominator, "battery charge energy limit"
            )
            charge = min(charge_request, config.battery_max_power_kw, capacity_limit)
            battery_limit = -charge
        if abs(battery_limit - requested_battery) > 1e-9:
            violations.append({"step": step, "constraint": "battery_power_or_energy_limit"})

        peaker_limit = config.peaker_capacity_kw if scenario.peaker_available[step] else 0.0
        peaker_equipment = min(max(0.0, requested_peaker), peaker_limit)
        if abs(peaker_equipment - requested_peaker) > 1e-9:
            violations.append({"step": step, "constraint": "peaker_capacity_or_availability"})

        # Allocate only energy that has a source and a sink. Battery discharge has
        # priority over the peaker; charging may use renewable/peaker surplus or
        # an available grid, but can never consume energy recorded as unserved.
        if battery_limit >= 0:
            demand_after_renewable = max(0.0, load - renewable)
            battery = min(battery_limit, demand_after_renewable)
            if abs(battery - battery_limit) > 1e-9:
                violations.append({"step": step, "constraint": "battery_discharge_energy_demand"})
            useful_peaker = max(0.0, demand_after_renewable - battery)
            peaker = min(peaker_equipment, useful_peaker)
            if abs(peaker - peaker_equipment) > 1e-9:
                violations.append({"step": step, "constraint": "peaker_energy_demand_limit"})
            discharged_energy = _finite_ratio(
                _finite_product("battery discharged energy", battery, dt),
                config.discharge_efficiency,
                "battery discharged energy",
            )
            new_soc = _finite_sum("battery state of charge", soc, -discharged_energy)
        else:
            charge_limit = -battery_limit
            useful_peaker = max(
                0.0,
                _finite_sum("charging demand", load, charge_limit, -renewable),
            )
            peaker = min(peaker_equipment, useful_peaker)
            if abs(peaker - peaker_equipment) > 1e-9:
                violations.append({"step": step, "constraint": "peaker_energy_demand_limit"})
            if scenario.grid_available[step]:
                charge = charge_limit
            else:
                sourced_surplus = max(
                    0.0,
                    _finite_sum("chargeable surplus", renewable, peaker, -load),
                )
                charge = min(charge_limit, sourced_surplus)
            battery = -charge if charge > 0.0 else 0.0
            if abs(battery - battery_limit) > 1e-9:
                violations.append({"step": step, "constraint": "battery_charge_energy_availability"})
            charged_energy = _finite_product(
                "battery charged energy", charge, config.charge_efficiency, dt
            )
            new_soc = _finite_sum("battery state of charge", soc, charged_energy)

        residual = _finite_sum("bus residual", load, -renewable, -battery, -peaker)
        if residual > 0:
            grid_import = residual if scenario.grid_available[step] else 0.0
            unserved = residual - grid_import
            curtailed = 0.0
        else:
            grid_import = 0.0
            unserved = 0.0
            curtailed = -residual

        cost_rate = _finite_sum(
            "step cost rate",
            _finite_product("grid cost rate", grid_import, scenario.grid_price_per_kwh[step]),
            _finite_product("peaker cost rate", peaker, config.peaker_cost_per_kwh),
            _finite_product("unserved cost rate", unserved, config.value_of_lost_load_per_kwh),
        )
        step_cost = _finite_product("step cost", cost_rate, dt)
        emissions_rate = _finite_sum(
            "step emissions rate",
            _finite_product(
                "grid emissions rate", grid_import, scenario.grid_emissions_kg_per_kwh[step]
            ),
            _finite_product("peaker emissions rate", peaker, config.peaker_emissions_kg_per_kwh),
        )
        step_emissions = _finite_product("step emissions", emissions_rate, dt)

        _accumulate(totals, "load_kwh", _finite_product("load energy", load, dt))
        _accumulate(
            totals,
            "renewable_available_kwh",
            _finite_product("renewable available energy", renewable, dt),
        )
        _accumulate(
            totals, "grid_import_kwh", _finite_product("grid import energy", grid_import, dt)
        )
        _accumulate(
            totals,
            "battery_discharge_kwh",
            _finite_product("battery discharge energy", max(0.0, battery), dt),
        )
        _accumulate(
            totals,
            "battery_charge_kwh",
            _finite_product("battery charge energy", max(0.0, -battery), dt),
        )
        _accumulate(totals, "peaker_kwh", _finite_product("peaker energy", peaker, dt))
        _accumulate(totals, "unserved_kwh", _finite_product("unserved energy", unserved, dt))
        _accumulate(totals, "curtailed_kwh", _finite_product("curtailed energy", curtailed, dt))
        _accumulate(totals, "cost", step_cost)
        _accumulate(totals, "emissions_kg", step_emissions)

        records.append(
            {
                "step": step,
                "load_kw": _round(load),
                "renewable_kw": _round(renewable),
                "grid_available": scenario.grid_available[step],
                "battery_requested_kw": _round(requested_battery),
                "battery_actual_kw": _round(battery),
                "peaker_requested_kw": _round(requested_peaker),
                "peaker_actual_kw": _round(peaker),
                "grid_import_kw": _round(grid_import),
                "unserved_kw": _round(unserved),
                "curtailed_kw": _round(curtailed),
                "battery_soc_kwh": _round(new_soc),
                "step_cost": _round(step_cost),
                "step_emissions_kg": _round(step_emissions),
                "rationale": str(action.rationale),
            }
        )
        soc = min(config.battery_capacity_kwh, max(0.0, new_soc))

    totals = {key: _round(value) for key, value in totals.items()}
    reliability = min(
        1.0,
        max(
            0.0,
            _finite_sum(
                "reliability",
                1.0,
                -_finite_ratio(
                    totals["unserved_kwh"],
                    max(totals["load_kwh"], 1e-9),
                    "reliability",
                ),
            ),
        ),
    )
    safety_score = min(
        100.0,
        max(0.0, 100.0 * (1.0 - len(violations) / max(1.0, len(records) * 4.0))),
    )
    cost_denominator = max(
        1.0, _finite_product("cost score denominator", totals["load_kwh"], 0.20)
    )
    cost_score = _finite_ratio(
        100.0,
        _finite_sum(
            "cost score denominator",
            1.0,
            _finite_ratio(totals["cost"], cost_denominator, "cost score ratio"),
        ),
        "cost score",
    )
    emissions_denominator = max(
        1.0,
        _finite_product("emissions score denominator", totals["load_kwh"], 0.65),
    )
    emissions_score = max(
        0.0,
        _finite_product(
            "emissions score",
            100.0,
            _finite_sum(
                "emissions score",
                1.0,
                -_finite_ratio(
                    totals["emissions_kg"], emissions_denominator, "emissions score ratio"
                ),
            ),
        ),
    )
    composite = min(100.0, max(0.0, (
        reliability * 100.0 * 0.45
        + cost_score * 0.20
        + emissions_score * 0.15
        + safety_score * 0.20
    )))
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "grid-ops-arena.simulation-report",
        "generator": {"name": "grid-ops-arena", "version": __version__},
        "synthetic_notice": scenario.synthetic_notice,
        "scenario": {
            "scenario_id": scenario.scenario_id,
            "seed": scenario.seed,
            "hours": _finite_product("scenario hours", float(len(records)), dt),
            "events": [asdict(event) for event in scenario.events],
            "config": asdict(config),
        },
        "policy": getattr(policy, "name", policy.__class__.__name__),
        "metrics": {
            "reliability_fraction": _round(reliability),
            "total_cost": totals["cost"],
            "emissions_kg": totals["emissions_kg"],
            "safety_score": _round(safety_score),
            "cost_score": _round(cost_score),
            "emissions_score": _round(emissions_score),
            "composite_score": _round(composite),
            "constraint_violations": len(violations),
        },
        "energy": totals,
        "violations": violations,
        "steps": records,
    }
