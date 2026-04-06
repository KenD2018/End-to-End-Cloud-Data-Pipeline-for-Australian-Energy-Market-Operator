# End-to-End Cloud Data Pipeline for Australian Energy Market Operator (AEMO)

> 端到端云数据管道项目 — 澳洲国家电力市场数据工程

## Project Overview / 项目概述

This project builds an automated, end-to-end data pipeline that ingests 5 years of electricity price and demand data from Australia's National Electricity Market (AEMO), processes it through a cloud-based architecture, and visualises insights via Power BI.

本项目构建了一条全自动的端到端数据管道，从澳洲国家电力市场（AEMO）获取5年电力价格和需求数据，经过云端架构处理后，通过Power BI生成可视化洞察。

## Architecture / 技术架构
```
AEMO Website (300 CSV files)
    ↓  Step 1: Ingestion / 数据摄取
Apache Airflow (Orchestration / 编排)
    ↓  Step 2: Data Lake / 数据湖
Google Cloud Storage (GCS)
    ↓  Step 3: Data Warehouse / 数据仓库
BigQuery (raw table → partitioned + clustered table)
    ↓  Step 4: Transformation / 数据转换
dbt (staging view + daily aggregation table)
    ↓  Step 5: Visualisation / 可视化
Dashboard
```

## Key Findings / 核心数据发现

**1. 2022 Energy Crisis / 2022年能源危机**
Prices tripled across all states — average $163/MWh vs $48/MWh in 2020.
电价涨至3倍，平均从2020年的$48/MWh飙升至$163/MWh。

**2. Negative Prices / 负电价现象**
SA1 had negative prices on 75% of days (1,368 out of 1,825) due to renewable energy oversupply.
南澳75%的天数出现负电价，可再生能源产出已超过市场消化能力。

**3. Seasonal Anomaly / 季节性异常**
May is the most expensive month — not July (winter). Supply shocks from coal plant outages matter more than seasonal demand.
5月是全年最贵月份而非冬天7月，供应侧冲击影响大于季节性需求。

**4. Volatility Surprise / 波动性意外**
QLD1 is the most price-volatile state, not SA1. Extreme summer heat and heavy industrial load create sudden demand spikes.
昆士兰州价格波动最大，极端夏季高温加重工业负荷是主因。

## Technology Stack / 技术栈

| Tool / 工具 | Purpose / 用途 |
|------------|---------------|
| Apache Airflow | Pipeline orchestration / 管道编排调度 |
| Google Cloud Storage | Data lake / 数据湖 |
| BigQuery | Data warehouse / 数据仓库 |
| dbt | Data transformation / 数据转换 |
| Docker | Airflow containerisation / 容器化 |

## Repository Structure / 仓库结构
```
├── 1_dataset/          # Data source info / 数据集说明
├── 2_data_lake/        # Airflow DAG + GCS / 数据湖与编排
├── 3_data_warehouse/   # BigQuery tables / 数据仓库
├── 4_transformations/  # dbt models / dbt转换
├── 5_dashboard/        # Dashboard screenshots / 可视化截图
└── README.md
```

## Dataset / 数据集

- **Source:** [AEMO NEM Aggregated Data](https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/aggregated-data)
- **States / 覆盖州:** NSW1, VIC1, QLD1, SA1, TAS1
- **Period / 时间范围:** January 2020 – December 2024
- **Volume / 数据量:** 300 CSV files, ~3 million rows

---
*DE Zoomcamp Final Project · KD · 2024*
