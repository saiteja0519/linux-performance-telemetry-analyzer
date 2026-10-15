from __future__ import annotations

from typing import Any, Iterable


def format_bytes_per_second(value: float) -> str:
    value = float(value)
    units = ("B/s", "KB/s", "MB/s", "GB/s", "TB/s")
    for unit in units:
        if abs(value) < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} TB/s"


def print_report(metrics: dict[str, Any], observations: Iterable[dict[str, Any]]) -> None:
    print("\n" + "=" * 64)
    print("LINUX PERFORMANCE TELEMETRY REPORT")
    print("=" * 64)
    print(f"Host:       {metrics.get('hostname', 'unknown')}")
    print(f"Timestamp:  {metrics.get('timestamp', 'n/a')}")
    print(f"CPU:        {float(metrics.get('cpu_percent', 0.0)):.1f}%")
    print(f"Memory:     {float(metrics.get('memory_percent', 0.0)):.1f}%")
    print(f"Available:  {float(metrics.get('memory_available_mb', 0.0)):.1f} MB")
    print(f"Swap:       {float(metrics.get('swap_percent', 0.0)):.1f}%")
    print(f"Disk used:  {float(metrics.get('disk_percent', 0.0)):.1f}%")
    print("Disk read:  " + format_bytes_per_second(metrics.get("disk_read_bytes_per_sec", 0.0)))
    print("Disk write: " + format_bytes_per_second(metrics.get("disk_write_bytes_per_sec", 0.0)))
    print("Network in: " + format_bytes_per_second(metrics.get("network_recv_bytes_per_sec", 0.0)))
    print("Network out:" + format_bytes_per_second(metrics.get("network_sent_bytes_per_sec", 0.0)))

    load = metrics.get("load_average") or []
    if load:
        values = list(load)
        while len(values) < 3:
            values.append(0.0)
        print(f"Load avg:   1m={values[0]:.2f}, 5m={values[1]:.2f}, 15m={values[2]:.2f}")

    top_processes = metrics.get("top_memory_processes", [])
    print("\nTop processes by memory:")
    for process in top_processes:
        print(
            f"  PID {process.get('pid', 0):<7} "
            f"{str(process.get('name', 'unknown'))[:24]:<24} "
            f"{float(process.get('memory_percent', 0.0)):.2f}%"
        )

    print("\nObservations:")
    for item in observations:
        print(f"  [{str(item.get('severity', 'normal')).upper()}] {item.get('category', 'SYSTEM')}: {item.get('message', '')}")
    print("=" * 64)
