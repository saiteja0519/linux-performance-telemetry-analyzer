from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _metric_percent(snapshot: Dict[str, Any], key: str) -> float:
    section = snapshot.get(key, {})
    if isinstance(section, dict):
        return float(section.get("percent", 0.0) or 0.0)
    return float(section or 0.0)


def _safe_lookup(snapshot: Dict[str, Any], key: str, default: Any = 0.0) -> Any:
    return snapshot.get(key, default)


def _score_value(metric: float) -> float:
    return max(0.0, min(100.0, metric))


def compute_health_score(snapshot: Dict[str, Any]) -> float:
    """Return a 0-100 health score, with higher values being healthier."""
    cpu = _score_value(_metric_percent(snapshot, "cpu_percent"))
    memory = _score_value(_metric_percent(snapshot, "memory"))
    disk = _score_value(_metric_percent(snapshot, "disk"))
    network = 0.0
    network_info = snapshot.get("network", {})
    if isinstance(network_info, dict):
        sent = float(network_info.get("bytes_sent", 0) or 0)
        received = float(network_info.get("bytes_recv", 0) or 0)
        network = min(100.0, (sent + received) / (1024 * 1024 * 10.0))

    process_count = float(_safe_lookup(snapshot, "process_count", 0) or 0)
    process_penalty = 0.0
    if process_count > 500:
        process_penalty = min(30.0, (process_count - 500) / 50.0)

    score = 100.0 - (cpu * 0.4) - (memory * 0.35) - (disk * 0.2) - (network * 0.03) - process_penalty
    return round(max(0.0, min(100.0, score)), 2)


def identify_bottlenecks(snapshot: Dict[str, Any]) -> List[str]:
    """Return the main performance bottleneck categories detected in the snapshot."""
    metrics: List[Tuple[str, float]] = []
    cpu = _metric_percent(snapshot, "cpu_percent")
    memory = _metric_percent(snapshot, "memory")
    disk = _metric_percent(snapshot, "disk")

    for label, value in (("CPU", cpu), ("Memory", memory), ("Disk", disk)):
        if value >= 80.0:
            metrics.append((label, value))

    if not metrics:
        return []

    metrics.sort(key=lambda item: item[1], reverse=True)
    return [label for label, _ in metrics[:3]]


def summarize_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    score = compute_health_score(snapshot)
    bottlenecks = identify_bottlenecks(snapshot)

    if score >= 80:
        status = "Healthy"
    elif score >= 60:
        status = "Warning"
    else:
        status = "Critical"

    summary = {
        "status": status,
        "health_score": score,
        "bottlenecks": bottlenecks,
        "cpu_percent": round(_metric_percent(snapshot, "cpu_percent"), 2),
        "memory_percent": round(_metric_percent(snapshot, "memory"), 2),
        "disk_percent": round(_metric_percent(snapshot, "disk"), 2),
        "process_count": int(_safe_lookup(snapshot, "process_count", 0) or 0),
    }

    if not bottlenecks:
        summary["message"] = "No major bottleneck detected; system resources are in a healthy range."
    elif len(bottlenecks) == 1:
        summary["message"] = f"Primary bottleneck: {bottlenecks[0]} consumption is high but manageable."
    else:
        summary["message"] = f"Primary bottlenecks: {', '.join(bottlenecks)} are elevated."

    return summary


def analyse_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return summarize_snapshot(snapshot)


def analyze_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return summarize_snapshot(snapshot)


def analyse_file(path: str | Path) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    return summarize_snapshot(snapshot)


def analyze_file(path: str | Path) -> Dict[str, Any]:
    return analyse_file(path)


class PerformanceAnalyzer:
    def __init__(self, snapshot: Dict[str, Any]):
        self.snapshot = snapshot

    def analyze(self) -> Dict[str, Any]:
        return summarize_snapshot(self.snapshot)

    def analyse(self) -> Dict[str, Any]:
        return summarize_snapshot(self.snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze performance telemetry and report bottlenecks.")
    parser.add_argument("path", nargs="?", default="telemetry.json", help="Path to a telemetry JSON file.")
    args = parser.parse_args()

    report = analyse_file(args.path)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
