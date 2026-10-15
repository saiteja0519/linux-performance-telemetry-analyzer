
import argparse
import json
from pathlib import Path

from collector import collect_system_metrics
from Analyser import summarize_snapshot
from database import initialize_database, save_snapshot
from reporter import print_report


def normalize_metrics(raw):
    """Convert collected metrics into the format expected by other modules."""
    memory = raw.get("memory", {})
    disk = raw.get("disk", {})
    network = raw.get("network", {})
    swap = raw.get("swap", {})
    disk_io = raw.get("disk_io", {})

    return {
        **raw,
        "memory_percent": float(memory.get("percent", 0.0)),
        "memory_available_mb": float(memory.get("available_mb", 0.0)),
        "disk_percent": float(disk.get("percent", 0.0)),
        "swap_percent": float(swap.get("percent", 0.0)),
        "network_recv_bytes_per_sec": float(
            network.get("recv_bytes_per_sec", 0.0)
        ),
        "network_sent_bytes_per_sec": float(
            network.get("sent_bytes_per_sec", 0.0)
        ),
        "disk_read_bytes_per_sec": float(
            disk_io.get("read_bytes_per_sec", 0.0)
        ),
        "disk_write_bytes_per_sec": float(
            disk_io.get("write_bytes_per_sec", 0.0)
        ),
        "load_average": raw.get("load_average", []),
        "top_memory_processes": raw.get("top_memory_processes", []),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Linux Performance Telemetry & Bottleneck Analyzer"
    )
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--output", default="telemetry.json")
    parser.add_argument("--database", default="telemetry.db")
    args = parser.parse_args()

    print("Collecting Linux system metrics...")

    raw_metrics = collect_system_metrics(interval=args.interval)
    metrics = normalize_metrics(raw_metrics)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    print(f"Telemetry saved to {output_path}")

    # Analyze the collected metrics.
    analysis = summarize_snapshot(metrics)

    # Save the telemetry snapshot to SQLite.
    initialize_database(args.database)
    snapshot_id = save_snapshot(metrics, args.database)

    # Prepare observations for the report.
    observations = analysis.get("observations", [])

    if not observations:
        observations = [
            {
                "severity": "INFO",
                "category": "SYSTEM",
                "message": str(item),
            }
            for item in analysis.get("bottlenecks", [])
        ]

    print_report(metrics, observations)

    print(f"\nDatabase snapshot ID: {snapshot_id}")

    # Save analysis for the Streamlit dashboard.
    analysis_path = Path(__file__).with_name("analysis.json")

    with analysis_path.open("w", encoding="utf-8") as file:
        json.dump(analysis, file, indent=2, sort_keys=True)

    print(f"Analysis saved to {analysis_path}")
    print("\nAnalysis summary:")
    print(json.dumps(analysis, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
