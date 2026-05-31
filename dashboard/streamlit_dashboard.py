"""Live Streamlit dashboard for store intelligence."""
from __future__ import annotations

import os
import time

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
STORE_ID = os.getenv("STORE_ID", "ST1008")
REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "10"))


def fetch_json(path: str) -> dict | list | None:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE}{path}")
            if response.status_code == 503:
                st.error("API database unavailable (503)")
                return None
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        st.warning(f"Could not reach API: {exc}")
        return None


st.set_page_config(page_title="Purplle Store Intelligence", layout="wide")
st.title("Purplle Store Intelligence — Live Dashboard")
st.caption(f"Store: **{STORE_ID}** | API: `{API_BASE}`")

placeholder = st.empty()
auto = st.sidebar.checkbox("Auto-refresh", value=False)
if st.sidebar.button("Refresh now"):
    st.rerun()

with placeholder.container():
    health = fetch_json("/health")
    metrics = fetch_json(f"/stores/{STORE_ID}/metrics")
    funnel = fetch_json(f"/stores/{STORE_ID}/funnel")
    heatmap = fetch_json(f"/stores/{STORE_ID}/heatmap")
    anomalies = fetch_json(f"/stores/{STORE_ID}/anomalies")

    col1, col2, col3, col4 = st.columns(4)
    if metrics:
        col1.metric("Unique Visitors", metrics.get("unique_visitors", 0))
        col2.metric("Conversion Rate", f"{metrics.get('conversion_rate', 0) * 100:.1f}%")
        col3.metric("Queue Depth", metrics.get("queue_depth", 0))
        col4.metric("Abandonment Rate", f"{metrics.get('abandonment_rate', 0) * 100:.1f}%")
    else:
        for c in (col1, col2, col3, col4):
            c.metric("—", "N/A")

    st.subheader("Conversion Funnel")
    if funnel and funnel.get("stages"):
        df = pd.DataFrame(funnel["stages"])
        st.bar_chart(df.set_index("stage")["count"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No funnel data yet. Run the pipeline or ingest events.")

    left, right = st.columns(2)
    with left:
        st.subheader("Zone Heatmap")
        if heatmap and heatmap.get("zones"):
            hz = pd.DataFrame(heatmap["zones"])
            st.dataframe(hz, use_container_width=True)
            st.caption(f"Data confidence: {heatmap.get('data_confidence', 0):.0%}")
            if not hz.empty:
                st.bar_chart(hz.set_index("zone_id")["normalized_score"])
        else:
            st.info("Heatmap awaiting zone events.")

    with right:
        st.subheader("Active Anomalies")
        if anomalies and anomalies.get("anomalies"):
            for item in anomalies["anomalies"]:
                severity = item.get("severity", "low")
                st.error(f"**{item['anomaly_type']}** ({severity}): {item['message']}")
                st.caption(f"Action: {item['suggested_action']}")
        else:
            st.success("No active anomalies detected.")

    st.subheader("System Health")
    if health:
        status = health.get("status", "unknown")
        color = "green" if status == "healthy" else "orange"
        st.markdown(f"Status: :{color}[{status}] | DB: {health.get('database')} | Stale feed: {health.get('stale_feed')}")
        if health.get("last_event_timestamp"):
            st.write(f"Last event: {health['last_event_timestamp']}")

if auto:
    time.sleep(REFRESH_SECONDS)
    st.rerun()
