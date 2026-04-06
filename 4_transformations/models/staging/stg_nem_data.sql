-- =============================================================
-- Staging Model: stg_nem_data
-- 清洗层模型：stg_nem_data
-- =============================================================
-- Type / 类型: VIEW (no data stored, always fresh)
--              视图（不存数据，每次查询时实时计算）
--
-- Purpose / 用途:
--   English: Clean raw data, rename columns, add derived time fields
--   中文：清洗原始数据，重命名列，添加派生时间字段
--
-- Source / 数据来源: nem_partitioned table in BigQuery
-- =============================================================

{{ config(materialized='view') }}

with source as (
    -- Read from the partitioned BigQuery table
    -- 从BigQuery分区表读取数据
    select * from {{ source('aemo_electricity', 'nem_partitioned') }}
),

renamed as (
    select
        -- Core fields / 核心字段
        settlement_date,
        region_id,
        total_demand_mw,
        price_aud_per_mwh,
        period_type,

        -- Derived time fields for easier analysis
        -- 派生时间字段，方便后续分析
        DATE(settlement_date)                as settlement_date_day,  -- Date only / 只保留日期
        EXTRACT(YEAR FROM settlement_date)   as year,                 -- Year / 年
        EXTRACT(MONTH FROM settlement_date)  as month,                -- Month 1-12 / 月份1-12
        EXTRACT(HOUR FROM settlement_date)   as hour                  -- Hour 0-23 / 小时0-23

    from source
    where
        -- Filter out null timestamps / 过滤掉空时间戳
        settlement_date is not null
        -- Filter out zero demand (data quality) / 过滤需求量为0的行（数据质量）
        and total_demand_mw > 0
        -- Filter out null prices / 过滤空电价
        and price_aud_per_mwh is not null
)

select * from renamed
