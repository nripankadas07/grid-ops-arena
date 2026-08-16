"""JSON, Markdown, and single-file HTML report emitters."""

import html
import json
import re
from pathlib import Path
from typing import Any, Dict


def _markdown_text(value: Any) -> str:
    """Render untrusted values as one inert Markdown line."""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "".join(
        character
        if character.isalnum() or character == " "
        else "&#{0};".format(ord(character))
        for character in text
    )


def _markdown(result: Dict[str, Any]) -> str:
    metrics = result["metrics"]
    energy = result["energy"]
    lines = [
        "# Grid Ops Arena report",
        "",
        "> **Synthetic demo:** {0}".format(_markdown_text(result["synthetic_notice"])),
        "",
        "- Scenario: `{0}`".format(_markdown_text(result["scenario"]["scenario_id"])),
        "- Policy: `{0}`".format(_markdown_text(result["policy"])),
        "- Schema: `{0}`".format(_markdown_text(result["schema_version"])),
        "",
        "## Scorecard",
        "",
        "| Metric | Value |",
        "|---|---:|",
        "| Composite score | {0:.2f} |".format(metrics["composite_score"]),
        "| Reliability | {0:.3%} |".format(metrics["reliability_fraction"]),
        "| Safety score | {0:.2f} |".format(metrics["safety_score"]),
        "| Total synthetic cost | {0:.2f} |".format(metrics["total_cost"]),
        "| Emissions | {0:.2f} kg |".format(metrics["emissions_kg"]),
        "| Unserved energy | {0:.3f} kWh |".format(energy["unserved_kwh"]),
        "| Constraint violations | {0} |".format(metrics["constraint_violations"]),
        "",
        "## Event log",
        "",
    ]
    for event in result["scenario"]["events"]:
        lines.append(
            "- Steps {0}–{1}: **{2}** — {3}".format(
                event["start_step"],
                event["end_step"],
                _markdown_text(event["kind"]),
                _markdown_text(event["description"]),
            )
        )
    lines.extend(
        [
            "",
            "## Dispatch excerpt",
            "",
            "| Step | Load | Renewable | Battery | Peaker | Grid | Unserved | SOC |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in result["steps"][:24]:
        lines.append(
            "| {step} | {load_kw:.1f} | {renewable_kw:.1f} | {battery_actual_kw:.1f} | "
            "{peaker_actual_kw:.1f} | {grid_import_kw:.1f} | {unserved_kw:.1f} | "
            "{battery_soc_kwh:.1f} |".format(**row)
        )
    lines.extend(["", "Generated deterministically by Grid Ops Arena.", ""])
    return "\n".join(lines)


def _html(result: Dict[str, Any]) -> str:
    metrics = result["metrics"]
    rows = "".join(
        "<tr><td>{step}</td><td>{load_kw:.1f}</td><td>{renewable_kw:.1f}</td>"
        "<td>{battery_actual_kw:.1f}</td><td>{peaker_actual_kw:.1f}</td>"
        "<td>{grid_import_kw:.1f}</td><td>{unserved_kw:.1f}</td>"
        "<td>{battery_soc_kwh:.1f}</td></tr>".format(**row)
        for row in result["steps"]
    )
    embedded = html.escape(json.dumps(result, sort_keys=True, allow_nan=False))
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grid Ops Arena report</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18212b}}h1{{margin-bottom:.2rem}}.notice{{background:#fff3cd;padding:1rem;border-left:4px solid #e0a800}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin:1.5rem 0}}.card{{padding:1rem;border:1px solid #ccd5df;border-radius:10px}}.value{{font-size:1.6rem;font-weight:700}}table{{border-collapse:collapse;width:100%;font-size:.85rem}}th,td{{padding:.45rem;border-bottom:1px solid #dde3e9;text-align:right}}th:first-child,td:first-child{{text-align:left}}details{{margin-top:2rem}}code{{word-break:break-all}}</style>
<body><h1>Grid Ops Arena</h1><p>Scenario <strong>{scenario}</strong> · policy <strong>{policy}</strong></p>
<p class="notice"><strong>Synthetic demo.</strong> {notice}</p>
<div class="cards"><div class="card"><div>Composite</div><div class="value">{composite:.2f}</div></div><div class="card"><div>Reliability</div><div class="value">{reliability:.2%}</div></div><div class="card"><div>Safety</div><div class="value">{safety:.1f}</div></div><div class="card"><div>Cost</div><div class="value">{cost:.2f}</div></div><div class="card"><div>Emissions kg</div><div class="value">{emissions:.1f}</div></div></div>
<h2>Dispatch</h2><table><thead><tr><th>Step</th><th>Load</th><th>Renewable</th><th>Battery</th><th>Peaker</th><th>Grid</th><th>Unserved</th><th>SOC</th></tr></thead><tbody>{rows}</tbody></table>
<details><summary>Embedded versioned JSON artifact</summary><code>{embedded}</code></details></body></html>""".format(
        scenario=html.escape(result["scenario"]["scenario_id"]),
        policy=html.escape(result["policy"]),
        notice=html.escape(result["synthetic_notice"]),
        composite=metrics["composite_score"],
        reliability=metrics["reliability_fraction"],
        safety=metrics["safety_score"],
        cost=metrics["total_cost"],
        emissions=metrics["emissions_kg"],
        rows=rows,
        embedded=embedded,
    )


def write_reports(result: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_dir / "grid_ops_report.json",
        "markdown": output_dir / "grid_ops_report.md",
        "html": output_dir / "grid_ops_report.html",
    }
    paths["json"].write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths["markdown"].write_text(_markdown(result), encoding="utf-8")
    paths["html"].write_text(_html(result), encoding="utf-8")
    return paths
