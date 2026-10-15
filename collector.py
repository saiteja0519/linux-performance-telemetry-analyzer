from __future__ import annotations

import json
import os
import platform
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    import psutil
except ImportError:
    psutil = None


def _bytes_to_gb(value: float) -> float:
    return value / (1024 ** 3)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_cpu_usage(interval: float = 0.0) -> float:
    if psutil is not None:
        return float(psutil.cpu_percent(interval=interval))

    try:
        load = os.getloadavg()[0]
        return min(max(load * 100.0 / (os.cpu_count() or 1), 0.0), 100.0)
    except (AttributeError, OSError):
        return 0.0


def _get_memory_usage() -> Dict[str, Any]:
    if psutil is not None:
        memory = psutil.virtual_memory()
        return {
            "total_gb": round(_bytes_to_gb(memory.total), 2),
            "used_gb": round(_bytes_to_gb(memory.used), 2),
            "percent": float(memory.percent),
            "available_mb": round(memory.available / (1024 ** 2), 2),
        }

    values = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                key, value = line.split(":", 1)
                values[key] = float(value.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "percent": 0.0,
            "available_mb": 0.0,
        }

    total = values.get("MemTotal", 0.0)
    available = values.get("MemAvailable", 0.0)
    used = max(total - available, 0.0)

    return {
        "total_gb": round(_bytes_to_gb(total), 2),
        "used_gb": round(_bytes_to_gb(used), 2),
        "percent": round(used * 100 / total, 2) if total else 0.0,
        "available_mb": round(available / (1024 ** 2), 2),
    }


def _get_disk_usage() -> Dict[str, Any]:
    try:
        disk = psutil.disk_usage("/") if psutil else None
        if disk:
            return {
                "total_gb": round(_bytes_to_gb(disk.total), 2),
                "used_gb": round(_bytes_to_gb(disk.used), 2),
                "percent": float(disk.percent),
            }

        stat = os.statvfs("/")
        total = stat.f_frsize * stat.f_blocks
        free = stat.f_frsize * stat.f_bavail
        used = total - free
        return {
            "total_gb": round(_bytes_to_gb(total), 2),
            "used_gb": round(_bytes_to_gb(used), 2),
            "percent": round(used * 100 / total, 2) if total else 0.0,
        }
    except (OSError, AttributeError):
        return {"total_gb": 0.0, "used_gb": 0.0, "percent": 0.0}


def _get_swap_usage() -> Dict[str, Any]:
    if psutil is not None:
        swap = psutil.swap_memory()
        return {
            "total_gb": round(_bytes_to_gb(swap.total), 3),
            "used_gb": round(_bytes_to_gb(swap.used), 3),
            "percent": float(swap.percent),
        }

    values = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                if line.startswith(("SwapTotal:", "SwapFree:")):
                    key, value = line.split(":", 1)
                    values[key] = float(value.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        pass

    total = values.get("SwapTotal", 0.0)
    free = values.get("SwapFree", 0.0)
    used = max(total - free, 0.0)

    return {
        "total_gb": round(_bytes_to_gb(total), 3),
        "used_gb": round(_bytes_to_gb(used), 3),
        "percent": round(used * 100 / total, 2) if total else 0.0,
    }


def _get_network_counters() -> Dict[str, int]:
    if psutil is None:
        return {
            "bytes_sent": 0,
            "bytes_recv": 0,
            "packets_sent": 0,
            "packets_recv": 0,
        }

    counters = psutil.net_io_counters()
    return {
        "bytes_sent": int(counters.bytes_sent),
        "bytes_recv": int(counters.bytes_recv),
        "packets_sent": int(counters.packets_sent),
        "packets_recv": int(counters.packets_recv),
    }


def _get_disk_counters() -> Dict[str, int]:
    if psutil is None:
        return {"read_bytes": 0, "write_bytes": 0}

    counters = psutil.disk_io_counters()
    if counters is None:
        return {"read_bytes": 0, "write_bytes": 0}

    return {
        "read_bytes": int(counters.read_bytes),
        "write_bytes": int(counters.write_bytes),
    }


def _get_load_average() -> list[float]:
    try:
        return [round(float(value), 2) for value in os.getloadavg()]
    except (AttributeError, OSError):
        return []


def _get_top_memory_processes(limit: int = 5) -> list[Dict[str, Any]]:
    if psutil is None:
        return []

    processes = []
    for process in psutil.process_iter(
        ["pid", "name", "memory_info", "memory_percent"]
    ):
        try:
            info = process.info
            memory_info = info.get("memory_info")
            processes.append({
                "pid": info.get("pid", 0),
                "name": info.get("name") or "Unknown",
                "memory_mb": round(memory_info.rss / (1024 ** 2), 2)
                if memory_info else 0.0,
                "memory_percent": round(
                    float(info.get("memory_percent") or 0.0), 2
                ),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return sorted(
        processes,
        key=lambda item: item["memory_mb"],
        reverse=True,
    )[:limit]


def collect_system_metrics(interval: float = 0.0) -> Dict[str, Any]:
    """Collect system metrics and measure disk/network rates over one interval."""
    cpu_percent = _get_cpu_usage(interval=max(interval, 0.1))
    memory = _get_memory_usage()
    disk = _get_disk_usage()
    swap = _get_swap_usage()

    network_before = _get_network_counters()
    disk_before = _get_disk_counters()

    # A short sampling window is required to calculate bytes per second.
    sample_seconds = 1.0
    time.sleep(sample_seconds)

    network_after = _get_network_counters()
    disk_after = _get_disk_counters()

    network = {
        **network_after,
        "recv_bytes_per_sec": max(
            network_after["bytes_recv"] - network_before["bytes_recv"], 0
        ) / sample_seconds,
        "sent_bytes_per_sec": max(
            network_after["bytes_sent"] - network_before["bytes_sent"], 0
        ) / sample_seconds,
    }

    disk_io = {
        "read_bytes_per_sec": max(
            disk_after["read_bytes"] - disk_before["read_bytes"], 0
        ) / sample_seconds,
        "write_bytes_per_sec": max(
            disk_after["write_bytes"] - disk_before["write_bytes"], 0
        ) / sample_seconds,
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "cpu_percent": round(cpu_percent, 2),
        "memory": memory,
        "disk": disk,
        "swap": swap,
        "disk_io": disk_io,
        "network": network,
        "load_average": _get_load_average(),
        "top_memory_processes": _get_top_memory_processes(),
        "process_count": len(psutil.pids()) if psutil else 0,
    }


def collect_data(interval: float = 0.0) -> Dict[str, Any]:
    return collect_system_metrics(interval=interval)


def save_metrics(
    metrics: Dict[str, Any],
    destination: str | os.PathLike[str],
) -> Path:
    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2, sort_keys=True)
    return output_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Collect system telemetry for health analysis."
    )
    parser.add_argument("--output", default="telemetry.json")
    parser.add_argument("--interval", type=float, default=0.0)
    args = parser.parse_args()

    metrics = collect_system_metrics(interval=args.interval)
    saved_to = save_metrics(metrics, args.output)
    print(f"Telemetry saved to {saved_to}")
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
