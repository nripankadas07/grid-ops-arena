import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grid_ops_arena.model import Action, GridConfig, Scenario
from grid_ops_arena.policies import get_policy
from grid_ops_arena.simulator import build_demo_scenario, simulate


class RecklessPolicy:
    name = "reckless-test"

    def decide(self, observation):
        return Action(battery_kw=9999.0, peaker_kw=9999.0)


class NonFinitePolicy:
    name = "non-finite-test"

    def decide(self, observation):
        return Action(battery_kw=float("nan"), peaker_kw=float("inf"))


class ChargeDuringOutagePolicy:
    name = "charge-during-outage-test"

    def decide(self, observation):
        return Action(battery_kw=-10.0)


class SimulatorTests(unittest.TestCase):
    def test_seeded_demo_is_deterministic(self):
        first = simulate(build_demo_scenario(9, 36), get_policy("balanced"))
        second = simulate(build_demo_scenario(9, 36), get_policy("balanced"))
        self.assertEqual(first, second)

    def test_constraints_clamp_reckless_actions(self):
        result = simulate(build_demo_scenario(4, 24), RecklessPolicy())
        capacity = result["scenario"]["config"]["battery_capacity_kwh"]
        self.assertGreater(result["metrics"]["constraint_violations"], 0)
        self.assertTrue(all(0.0 <= row["battery_soc_kwh"] <= capacity for row in result["steps"]))
        self.assertTrue(all(row["peaker_actual_kw"] <= 60.0 for row in result["steps"]))

    def test_non_finite_actions_are_safely_rejected(self):
        result = simulate(build_demo_scenario(4, 24), NonFinitePolicy())
        codes = {item["constraint"] for item in result["violations"]}
        self.assertIn("finite_battery_action", codes)
        self.assertIn("finite_peaker_action", codes)
        json.dumps(result, allow_nan=False)

    def test_scenario_round_trip(self):
        scenario = build_demo_scenario(3, 24)
        restored = Scenario.from_artifact(json.loads(json.dumps(scenario.to_artifact())))
        self.assertEqual(scenario.to_artifact(), restored.to_artifact())

    def test_checked_in_scenario_matches_the_strict_artifact_schema(self):
        artifact = json.loads(
            (ROOT / "examples" / "synthetic_scenario.json").read_text(encoding="utf-8")
        )
        restored = Scenario.from_artifact(artifact)
        self.assertEqual(restored.scenario_id, "synthetic-community-microgrid-12h")

    def test_outages_are_present(self):
        scenario = build_demo_scenario(1, 24)
        self.assertIn(False, scenario.grid_available)
        self.assertTrue(any(event.kind == "grid_outage" for event in scenario.events))

    def test_charging_cannot_use_unserved_energy(self):
        scenario = Scenario(
            scenario_id="source-less-charge-test",
            seed=1,
            load_kw=[10.0],
            renewable_kw=[0.0],
            grid_available=[False],
            peaker_available=[False],
            grid_price_per_kwh=[0.0],
            grid_emissions_kg_per_kwh=[0.0],
            events=[],
            config=GridConfig(
                battery_capacity_kwh=100.0,
                battery_max_power_kw=20.0,
                battery_initial_soc_kwh=0.0,
                charge_efficiency=1.0,
                discharge_efficiency=1.0,
                peaker_capacity_kw=0.0,
                timestep_hours=1.0,
            ),
        )
        result = simulate(scenario, ChargeDuringOutagePolicy())
        row = result["steps"][0]
        self.assertEqual(row["battery_actual_kw"], 0.0)
        self.assertEqual(row["battery_soc_kwh"], 0.0)
        self.assertEqual(row["unserved_kw"], 10.0)
        self.assertIn(
            "battery_charge_energy_availability",
            {item["constraint"] for item in result["violations"]},
        )
        self.assertLess(result["metrics"]["safety_score"], 100.0)
        for name in ("reliability_fraction",):
            self.assertGreaterEqual(result["metrics"][name], 0.0)
            self.assertLessEqual(result["metrics"][name], 1.0)
        self.assertGreaterEqual(result["metrics"]["composite_score"], 0.0)
        self.assertLessEqual(result["metrics"]["composite_score"], 100.0)

    def test_every_demo_step_closes_bus_energy_balance(self):
        result = simulate(build_demo_scenario(8, 36), get_policy("balanced"))
        for row in result["steps"]:
            source = (
                row["renewable_kw"]
                + row["grid_import_kw"]
                + row["peaker_actual_kw"]
                + max(0.0, row["battery_actual_kw"])
            )
            sink = (
                row["load_kw"]
                - row["unserved_kw"]
                + max(0.0, -row["battery_actual_kw"])
                + row["curtailed_kw"]
            )
            self.assertAlmostEqual(source, sink, places=5, msg="step {0}".format(row["step"]))

    def test_artifact_availability_requires_json_booleans(self):
        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["series"]["grid_available"] = ["false"] * 12
        with self.assertRaisesRegex(ValueError, "must contain booleans"):
            Scenario.from_artifact(artifact)

    def test_config_rejects_numeric_strings_with_value_error(self):
        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["config"]["battery_capacity_kwh"] = "120"
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            Scenario.from_artifact(artifact)

    def test_artifact_requires_exact_root_series_and_config_fields(self):
        mutations = []
        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact.pop("seed")
        mutations.append((artifact, "scenario artifact fields"))

        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["unexpected_root"] = True
        mutations.append((artifact, "scenario artifact fields"))

        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["series"]["load_kw_typo"] = artifact["series"]["load_kw"]
        mutations.append((artifact, "scenario series fields"))

        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["config"].pop("battery_capacity_kwh")
        mutations.append((artifact, "grid config fields"))

        artifact = build_demo_scenario(1, 12).to_artifact()
        artifact["config"]["battery_capacity_kwh_typo"] = 120.0
        mutations.append((artifact, "grid config fields"))

        for mutated, message in mutations:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    Scenario.from_artifact(mutated)

    def test_derived_non_finite_math_fails_closed(self):
        scenario = Scenario(
            scenario_id="overflow-test",
            seed=1,
            load_kw=[1e308],
            renewable_kw=[0.0],
            grid_available=[True],
            peaker_available=[False],
            grid_price_per_kwh=[1.0],
            grid_emissions_kg_per_kwh=[1.0],
            events=[],
            config=GridConfig(timestep_hours=1e308),
        )
        with self.assertRaisesRegex(ValueError, "non-finite derived value"):
            simulate(scenario, get_policy("grid-first"))


if __name__ == "__main__":
    unittest.main()
