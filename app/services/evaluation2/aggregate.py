"""Structural + comparison overview aggregation for Phase 2 results.

Adapted from the earlier Phase 2 prototype's `services/aggregate.py`
concept (a setting x family grid), but reworked for explicit mode names.
For real-only results (`real_only_overview`) this stays purely structural:
there is no synthetic side and therefore no distance score to aggregate.

For real+synthetic results (`real_synthetic_overview` / `distance_stats`),
querylib's own `run_pair` output already carries the per-instance `distance`
in [0, 1] - this module only aggregates that existing number (count, mean,
min, max, median per grid cell; a global mean/min/max; a worst-offenders
list). It never computes a distance itself, never applies Phase 1 metric
math, and never maps a distance onto an invented "good"/"bad"/"acceptable"
label - distance is 0 (more similar) to 1 (more different), nothing more.
"""
from __future__ import annotations

import statistics
from typing import Any

# The 3x4 taxonomy: three settings, four families (see the Phase 2 handout
# audit). Fixed, not derived from data, so every cell always appears in the
# overview even if a particular spec has zero instances for it.
SETTINGS = ("A", "B", "C")
FAMILIES = ("distributional", "trend", "seasonality", "local")


def real_only_overview(instances: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a setting x family grid of instance counts from serialized
    `run_real` rows (i.e. `serialize.rows(handout_adapter.run_real(...))`).

    Each grid cell is `{"count": <int>}` - structural metadata only, no
    score derived from `value`/`value_summary`. Instances with a
    setting/family combination outside the fixed 3x4 taxonomy (should not
    happen for a validated spec, but not assumed impossible) are counted in
    `unrecognized_instances` instead of silently dropped.
    """
    grid: dict[str, dict[str, dict[str, int]]] = {
        s: {f: {"count": 0} for f in FAMILIES} for s in SETTINGS
    }
    unrecognized = 0

    for inst in instances:
        setting = inst.get("setting")
        family = inst.get("family")
        if setting in grid and family in grid[setting]:
            grid[setting][family]["count"] += 1
        else:
            unrecognized += 1

    return {
        "settings": list(SETTINGS),
        "families": list(FAMILIES),
        "grid": grid,
        "total_instances": len(instances),
        "unrecognized_instances": unrecognized,
    }


WORST_INSTANCES_LIMIT = 5


def real_synthetic_overview(instances: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a setting x family grid of comparison statistics from serialized
    `run_pair` rows (i.e. `serialize.rows(handout_adapter.run_pair(...))`).

    Each grid cell aggregates the `distance` field ([0, 1], already computed
    by querylib - never recomputed here) of every instance in that cell:
    `count`, `mean_distance`, `min_distance`, `max_distance`, and
    `median_distance`. A cell with zero instances reports `count: 0` and
    `None` for every distance statistic (nothing to aggregate). Instances
    outside the fixed 3x4 taxonomy, or missing a numeric `distance`, are
    counted in `unrecognized_instances` instead of silently dropped or
    crashing the aggregation.

    Also includes `worst_instances`: up to `WORST_INSTANCES_LIMIT` instances
    with the highest `distance`, each reduced to a small identifying subset
    of fields (not the full row) so the overview stays compact.
    """
    cells: dict[str, dict[str, list[float]]] = {
        s: {f: [] for f in FAMILIES} for s in SETTINGS
    }
    unrecognized = 0
    distance_ranked: list[dict[str, Any]] = []

    for inst in instances:
        setting = inst.get("setting")
        family = inst.get("family")
        distance = inst.get("distance")
        valid_cell = setting in cells and family in cells[setting]
        valid_distance = isinstance(distance, (int, float))

        if valid_cell and valid_distance:
            cells[setting][family].append(float(distance))
        else:
            unrecognized += 1

        if valid_distance:
            distance_ranked.append(inst)

    grid: dict[str, dict[str, dict[str, Any]]] = {}
    for setting in SETTINGS:
        grid[setting] = {}
        for family in FAMILIES:
            distances = cells[setting][family]
            if distances:
                grid[setting][family] = {
                    "count": len(distances),
                    "mean_distance": statistics.fmean(distances),
                    "min_distance": min(distances),
                    "max_distance": max(distances),
                    "median_distance": statistics.median(distances),
                }
            else:
                grid[setting][family] = {
                    "count": 0,
                    "mean_distance": None,
                    "min_distance": None,
                    "max_distance": None,
                    "median_distance": None,
                }

    distance_ranked.sort(key=lambda inst: inst["distance"], reverse=True)
    worst_instances = [
        {
            k: inst.get(k)
            for k in (
                "instance_id",
                "view",
                "setting",
                "family",
                "qid",
                "distance",
            )
        }
        for inst in distance_ranked[:WORST_INSTANCES_LIMIT]
    ]

    return {
        "settings": list(SETTINGS),
        "families": list(FAMILIES),
        "grid": grid,
        "total_instances": len(instances),
        "unrecognized_instances": unrecognized,
        "worst_instances": worst_instances,
    }


def distance_stats(instances: list[dict[str, Any]]) -> dict[str, Any]:
    """Global distance_mean/distance_min/distance_max/distance_median across
    every instance with a numeric `distance` (does not filter by taxonomy
    cell - unlike `real_synthetic_overview`'s grid, this is a whole-result
    summary). Returns `None` for every stat if there are zero such instances,
    rather than raising or defaulting to 0.0 (which would be indistinguishable
    from a real all-zero-distance result).
    """
    distances = [
        float(inst["distance"])
        for inst in instances
        if isinstance(inst.get("distance"), (int, float))
    ]
    if not distances:
        return {
            "distance_mean": None,
            "distance_min": None,
            "distance_max": None,
            "distance_median": None,
        }
    return {
        "distance_mean": statistics.fmean(distances),
        "distance_min": min(distances),
        "distance_max": max(distances),
        "distance_median": statistics.median(distances),
    }


__all__ = [
    "SETTINGS",
    "FAMILIES",
    "WORST_INSTANCES_LIMIT",
    "real_only_overview",
    "real_synthetic_overview",
    "distance_stats",
]
