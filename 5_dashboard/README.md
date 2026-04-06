# Step 5: Dashboard & Data Storytelling
# 第5步：数据可视化与故事展示

## Overview / 概述

This dashboard visualizes 5 years of Australian electricity market data (2020-2024) across 5 states, uncovering 4 counter-intuitive stories hidden in the data.

本仪表板可视化了澳洲5个州、5年的电力市场数据（2020-2024），揭示了4个隐藏在数据中的反常识故事。

**Data source / 数据来源:** `fact_daily_electricity` table in BigQuery (9,140 rows, aggregated from ~3M raw records)

---

## 4 Key Findings / 4大核心发现

### Finding 1: COVID Crashed Victoria's Demand (2020)
VIC1 2020 daily demand dropped ~14% vs 2019. Victoria's strict lockdowns shut factories and offices — commercial demand fell harder than residential demand rose.

### Finding 2: Negative Electricity Prices Are Real
SA1 recorded 155+ days with negative average prices. South Australia's ~65% renewables create supply surges that exceed grid demand.

### Finding 3: NSW Peak Price Is in July, Not Summer
July 2022 averaged ~AUD 520/MWh. Coal outages + global energy crisis (Ukraine war) hit the grid harder in winter than summer.

### Finding 4: Tasmania Most Stable, SA Most Volatile
Hydro (TAS) is controllable → stable prices. Wind/solar (SA) is intermittent → volatile prices.

---

## Tools Used / 使用工具

| Tool | Purpose |
|------|---------|
| BigQuery SQL | Data exploration & story discovery |
| HTML + Chart.js | Dashboard with consistent visual style |

---

## How to Reproduce / 如何复现

1. Complete Steps 1–4 (data ingestion → dbt)
2. Open `aemo_dashboard_v2.html` in Chrome
3. Screenshot with `Win + Shift + S`
4. Save to `screenshots/` folder
