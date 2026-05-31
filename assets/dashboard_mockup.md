# Dashboard layout (Streamlit)

```
+------------------------------------------------------------------+
|  Purplle Store Intelligence — Live Dashboard    Store: ST1008  |
+------------------------------------------------------------------+
| [Unique Visitors] [Conversion %] [Queue Depth] [Abandonment %]   |
+------------------------------------------------------------------+
| Conversion Funnel (bar chart)                                    |
|  Entry | Zone Visit | Billing Queue | Purchase                   |
+------------------------------------------------------------------+
| Zone Heatmap (table + bar)     | Active Anomalies               |
| zone_id | freq | dwell | score | QUEUE_SPIKE / CONVERSION_DROP   |
+------------------------------------------------------------------+
| Health: healthy | DB: up | Last event: 2026-04-10T...             |
+------------------------------------------------------------------+
| Sidebar: [x] Auto-refresh   [Refresh now]                        |
+------------------------------------------------------------------+
```

Data source: `GET /stores/ST1008/*` and `/health` via `httpx`.
