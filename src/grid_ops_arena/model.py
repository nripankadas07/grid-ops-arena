"""Versioned data models for Grid Ops Arena."""

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from . import SCHEMA_VERSION


SYNTHETIC_NOTICE = (
    "All loads, generation, prices, emissions factors, and outage events in "
    "the bundled examples are synthetic demonstration data, not current facts."
)


def _require_exact_fields(value: Dict[str, Any], expected: set, label: str) -> None:
    actual = set(value)
    if actual == expected:
        return
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    details = []
    if missing:
        details.append("missing: {0}".format(", ".join(missing)))
    if unknown:
        details.append("unknown: {0}".format(", ".join(unknown)))
    raise ValueError("{0} fields do not match schema ({1})".format(label, "; ".join(details)))


@dataclass(frozen=True)
class GridConfig:
    battery_capacity_kwh: float = 120.0
    battery_max_power_kw: float = 45.0
    battery_initial_soc_kwh: float = 72.0
    charge_efficiency: float = 0.94
    discharge_efficiency: float = 0.94
    peaker_capacity_kw: float = 60.0
    peaker_cost_per_kwh: float = 0.38
    peaker_emissions_kg_per_kwh: float = 0.72
    value_of_lost_load_per_kwh: float = 12.0
    timestep_hours: float = 1.0

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "GridConfig":
        if not isinstance(value, dict):
            raise ValueError("grid config must be an object")
        known = {item.name for item in cls.__dataclass_fields__.values()}
        _require_exact_fields(value, known, "grid config")
        supplied = {key: value[key] for key in known}
        invalid = [
            key
            for key, candidate in supplied.items()
            if isinstance(candidate, bool) or not isinstance(candidate, (int, float))
        ]
        if invalid:
            raise ValueError(
                "grid configuration values must be numeric: {0}".format(
                    ", ".join(sorted(invalid))
                )
            )
        return cls(**supplied)


@dataclass(frozen=True)
class Event:
    kind: str
    start_step: int
    end_step: int
    description: str


@dataclass
class Scenario:
    scenario_id: str
    seed: int
    load_kw: List[float]
    renewable_kw: List[float]
    grid_available: List[bool]
    peaker_available: List[bool]
    grid_price_per_kwh: List[float]
    grid_emissions_kg_per_kwh: List[float]
    events: List[Event]
    config: GridConfig = field(default_factory=GridConfig)
    synthetic_notice: str = SYNTHETIC_NOTICE

    def validate(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        lengths = {
            len(self.load_kw),
            len(self.renewable_kw),
            len(self.grid_available),
            len(self.peaker_available),
            len(self.grid_price_per_kwh),
            len(self.grid_emissions_kg_per_kwh),
        }
        if len(lengths) != 1 or not lengths or next(iter(lengths)) == 0:
            raise ValueError("scenario time series must be non-empty and equal length")
        numeric_series = (
            self.load_kw,
            self.renewable_kw,
            self.grid_price_per_kwh,
            self.grid_emissions_kg_per_kwh,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for series in numeric_series
            for value in series
        ):
            raise ValueError("scenario numeric series must contain only finite numbers")
        if any(value < 0 for series in numeric_series for value in series):
            raise ValueError("load, renewable, price, and emissions values must be non-negative")
        if any(type(value) is not bool for value in self.grid_available + self.peaker_available):
            raise ValueError("availability series must contain booleans")

        config_values = (
            self.config.battery_capacity_kwh,
            self.config.battery_max_power_kw,
            self.config.battery_initial_soc_kwh,
            self.config.charge_efficiency,
            self.config.discharge_efficiency,
            self.config.peaker_capacity_kw,
            self.config.peaker_cost_per_kwh,
            self.config.peaker_emissions_kg_per_kwh,
            self.config.value_of_lost_load_per_kwh,
            self.config.timestep_hours,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            for value in config_values
        ):
            raise ValueError("grid configuration values must be numeric")
        if any(not math.isfinite(float(value)) for value in config_values):
            raise ValueError("grid configuration values must be finite")
        if self.config.battery_capacity_kwh <= 0 or self.config.battery_max_power_kw <= 0:
            raise ValueError("battery capacity and power must be positive")
        if not 0 < self.config.charge_efficiency <= 1 or not 0 < self.config.discharge_efficiency <= 1:
            raise ValueError("battery efficiencies must be in (0, 1]")
        if self.config.peaker_capacity_kw < 0 or self.config.timestep_hours <= 0:
            raise ValueError("peaker capacity must be non-negative and timestep must be positive")
        if any(
            value < 0
            for value in (
                self.config.peaker_cost_per_kwh,
                self.config.peaker_emissions_kg_per_kwh,
                self.config.value_of_lost_load_per_kwh,
            )
        ):
            raise ValueError("cost and emissions configuration values must be non-negative")
        if not 0 <= self.config.battery_initial_soc_kwh <= self.config.battery_capacity_kwh:
            raise ValueError("initial battery state of charge is outside capacity")
        step_count = next(iter(lengths))
        for event in self.events:
            if not isinstance(event, Event):
                raise ValueError("events must contain Event values")
            if not isinstance(event.kind, str) or not event.kind.strip():
                raise ValueError("event kind must be a non-empty string")
            if not isinstance(event.description, str):
                raise ValueError("event description must be a string")
            if (
                isinstance(event.start_step, bool)
                or not isinstance(event.start_step, int)
                or isinstance(event.end_step, bool)
                or not isinstance(event.end_step, int)
            ):
                raise ValueError("event bounds must be integers")
            if (
                event.start_step < 0
                or event.end_step < event.start_step
                or event.end_step >= step_count
            ):
                raise ValueError("event bounds must fall within the scenario time series")

    def to_artifact(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "grid-ops-arena.scenario",
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "synthetic_notice": self.synthetic_notice,
            "config": asdict(self.config),
            "series": {
                "load_kw": self.load_kw,
                "renewable_kw": self.renewable_kw,
                "grid_available": self.grid_available,
                "peaker_available": self.peaker_available,
                "grid_price_per_kwh": self.grid_price_per_kwh,
                "grid_emissions_kg_per_kwh": self.grid_emissions_kg_per_kwh,
            },
            "events": [asdict(event) for event in self.events],
        }

    @classmethod
    def from_artifact(cls, value: Dict[str, Any]) -> "Scenario":
        if not isinstance(value, dict):
            raise ValueError("scenario artifact must be an object")
        _require_exact_fields(
            value,
            {
                "schema_version",
                "artifact_type",
                "scenario_id",
                "seed",
                "synthetic_notice",
                "config",
                "series",
                "events",
            },
            "scenario artifact",
        )
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported scenario schema_version")
        if value.get("artifact_type") != "grid-ops-arena.scenario":
            raise ValueError("unexpected artifact_type")
        series = value.get("series")
        if not isinstance(series, dict):
            raise ValueError("scenario series must be an object")
        _require_exact_fields(
            series,
            {
                "load_kw",
                "renewable_kw",
                "grid_available",
                "peaker_available",
                "grid_price_per_kwh",
                "grid_emissions_kg_per_kwh",
            },
            "scenario series",
        )

        def numeric_series(name: str) -> List[float]:
            values = series.get(name)
            if not isinstance(values, list):
                raise ValueError("series.{0} must be an array".format(name))
            if any(
                isinstance(item, bool) or not isinstance(item, (int, float))
                for item in values
            ):
                raise ValueError("series.{0} must contain numbers".format(name))
            return [float(item) for item in values]

        def availability_series(name: str) -> List[bool]:
            values = series.get(name)
            if not isinstance(values, list) or any(type(item) is not bool for item in values):
                raise ValueError("series.{0} must contain booleans".format(name))
            return list(values)

        scenario_id = value.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        seed = value["seed"]
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        raw_notice = value["synthetic_notice"]
        if not isinstance(raw_notice, str):
            raise ValueError("synthetic_notice must be a string")
        raw_events = value["events"]
        if not isinstance(raw_events, list):
            raise ValueError("events must be an array")
        events: List[Event] = []
        for item in raw_events:
            if not isinstance(item, dict):
                raise ValueError("events must contain objects")
            required = {"kind", "start_step", "end_step", "description"}
            if set(item) != required:
                raise ValueError("event fields must be kind, start_step, end_step, and description")
            events.append(Event(**item))
        scenario = cls(
            scenario_id=scenario_id,
            seed=seed,
            load_kw=numeric_series("load_kw"),
            renewable_kw=numeric_series("renewable_kw"),
            grid_available=availability_series("grid_available"),
            peaker_available=availability_series("peaker_available"),
            grid_price_per_kwh=numeric_series("grid_price_per_kwh"),
            grid_emissions_kg_per_kwh=numeric_series("grid_emissions_kg_per_kwh"),
            events=events,
            config=GridConfig.from_dict(value["config"]),
            synthetic_notice=raw_notice,
        )
        scenario.validate()
        return scenario


@dataclass(frozen=True)
class Action:
    """Agent action protocol; positive battery power discharges, negative charges."""

    battery_kw: float = 0.0
    peaker_kw: float = 0.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
