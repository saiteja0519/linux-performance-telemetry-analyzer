
from database import get_recent_snapshots, get_snapshot_count
import json
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Linux Performance Monitor",
    page_icon="📊",
    layout="wide",
)

TELEMETRY_FILE = Path(__file__).with_name("telemetry.json")
ANALYSIS_FILE = Path(__file__).with_name("analysis.json")
DATABASE_FILE = Path(__file__).with_name("telemetry.db")


# --------------------------------------------------
# Dashboard heading
# --------------------------------------------------
st.title("Linux Performance Telemetry Dashboard")
st.caption("Monitor system health, resource utilization, and processes.")

refresh = st.sidebar.checkbox(
    "Auto-refresh every 5 seconds",
    value=False,
)


# --------------------------------------------------
# Load current telemetry
# --------------------------------------------------
if not TELEMETRY_FILE.exists():
    st.warning("No telemetry file found. Run python3 run_analyser.py first.")
    st.stop()

try:
    with TELEMETRY_FILE.open("r", encoding="utf-8") as file:
        metrics = json.load(file)
except (json.JSONDecodeError, OSError) as error:
    st.error(f"Could not read telemetry: {error}")
    st.stop()


# --------------------------------------------------
# Extract metrics
# --------------------------------------------------
memory = metrics.get("memory", {})
disk = metrics.get("disk", {})
swap = metrics.get("swap", {})
network = metrics.get("network", {})
disk_io = metrics.get("disk_io", {})

cpu = float(metrics.get("cpu_percent", 0) or 0)
mem = float(
    metrics.get("memory_percent", memory.get("percent", 0)) or 0
)
disk_pct = float(
    metrics.get("disk_percent", disk.get("percent", 0)) or 0
)
swap_pct = float(
    metrics.get("swap_percent", swap.get("percent", 0)) or 0
)


# --------------------------------------------------
# System information
# --------------------------------------------------
st.subheader("System Information")

st.write(
    f"**Host:** {metrics.get('hostname', 'Unknown')}  |  "
    f"**OS:** {metrics.get('system', 'Unknown')}  |  "
    f"**Updated:** {metrics.get('timestamp', 'Unknown')}"
)


# --------------------------------------------------
# Main metric cards
# --------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("CPU Usage", f"{cpu:.1f}%")
c2.metric("Memory Usage", f"{mem:.1f}%")
c3.metric("Disk Usage", f"{disk_pct:.1f}%")
c4.metric("Swap Usage", f"{swap_pct:.1f}%")


# --------------------------------------------------
# Resource utilization chart
# --------------------------------------------------
st.subheader("Resource Utilization")

chart_data = pd.DataFrame({
    "Resource": ["CPU", "Memory", "Disk", "Swap"],
    "Usage (%)": [cpu, mem, disk_pct, swap_pct],
})

fig = px.bar(
    chart_data,
    x="Resource",
    y="Usage (%)",
    range_y=[0, 100],
    title="Current Resource Utilization",
    text="Usage (%)",
)

st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# Network and disk throughput
# --------------------------------------------------
st.subheader("Throughput")

n1, n2 = st.columns(2)

n1.metric(
    "Network Received",
    f"{network.get('recv_bytes_per_sec', 0) / 1024:.2f} KB/s",
)

n2.metric(
    "Network Sent",
    f"{network.get('sent_bytes_per_sec', 0) / 1024:.2f} KB/s",
)

d1, d2 = st.columns(2)

d1.metric(
    "Disk Read",
    f"{disk_io.get('read_bytes_per_sec', 0) / 1024:.2f} KB/s",
)

d2.metric(
    "Disk Write",
    f"{disk_io.get('write_bytes_per_sec', 0) / 1024:.2f} KB/s",
)


# --------------------------------------------------
# Top memory-consuming processes
# --------------------------------------------------
st.subheader("Top Memory-Consuming Processes")

processes = metrics.get("top_memory_processes", [])

if processes:
    process_df = pd.DataFrame(processes)

    st.dataframe(
        process_df,
        width="stretch",
        hide_index=True,
    )

    if {"name", "memory_mb"}.issubset(process_df.columns):
        process_chart = px.bar(
            process_df,
            x="name",
            y="memory_mb",
            title="Memory Usage by Process",
            labels={
                "name": "Process",
                "memory_mb": "Memory (MB)",
            },
        )

        st.plotly_chart(process_chart, width="stretch")
else:
    st.info("No process-level memory data is available.")


# --------------------------------------------------
# System health analysis
# --------------------------------------------------
st.subheader("System Health")

if ANALYSIS_FILE.exists():
    try:
        with ANALYSIS_FILE.open("r", encoding="utf-8") as file:
            analysis = json.load(file)

        health_score = float(analysis.get("health_score", 0) or 0)

        st.metric(
            "Health Score",
            f"{health_score:.1f}/100",
        )

        st.write(analysis.get("message", ""))

        st.write("**Detected Bottlenecks:**")

        bottlenecks = analysis.get("bottlenecks", [])

        if bottlenecks:
            for item in bottlenecks:
                st.warning(str(item))
        else:
            st.success("No bottlenecks reported.")

    except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
        st.error(f"Could not load system analysis: {error}")
else:
    st.info(
        "Analysis file not found. Run python3 run_analyser.py "
        "to generate the latest system analysis."
    )


# --------------------------------------------------
# Historical performance
# --------------------------------------------------
st.divider()
st.header("Historical Performance")

try:
    history = get_recent_snapshots(
        limit=100,
        database_path=DATABASE_FILE,
    )

    total_snapshots = get_snapshot_count(
        database_path=DATABASE_FILE,
    )

    st.metric("Total Recorded Snapshots", total_snapshots)

    if history:
        history_df = pd.DataFrame(history)

        if "timestamp" in history_df.columns:
            history_df["timestamp"] = pd.to_datetime(
                history_df["timestamp"],
                errors="coerce",
            )

            history_df = history_df.dropna(subset=["timestamp"])

        if not history_df.empty and "timestamp" in history_df.columns:
            history_df = history_df.sort_values("timestamp")

            for column, label in [
                ("cpu_percent", "CPU Usage (%)"),
                ("memory_percent", "Memory Usage (%)"),
                ("disk_percent", "Disk Usage (%)"),
            ]:
                if column in history_df.columns:
                    fig = px.line(
                        history_df,
                        x="timestamp",
                        y=column,
                        markers=True,
                        title=f"{label} Over Time",
                        labels={
                            "timestamp": "Time",
                            column: label,
                        },
                    )

                    st.plotly_chart(fig, width="stretch")
        else:
            st.info("No valid historical timestamps were found.")
    else:
        st.info(
            "No snapshots found. Run python3 run_analyser.py "
            "to record performance data."
        )

except (ValueError, OSError, KeyError, TypeError) as error:
    st.error(f"Could not load historical performance: {error}")


# --------------------------------------------------
# Auto-refresh dashboard
# --------------------------------------------------
if refresh:
    time.sleep(5)
    st.rerun()
