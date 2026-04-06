-- =============================================================
-- Core Model: fact_daily_electricity
-- 汇总层模型：fact_daily_electricity
-- =============================================================
-- Type / 类型: TABLE (pre-aggregated for fast dashboard queries)
--              实体表（预聚合，dashboard查询快）
--
-- Purpose / 用途:
--   English: Aggregate 5-minute interval data into daily summaries per state.
--            Reduces ~3 million rows to 9,140 rows (5 years x 5 states x ~365 days)
--   中文：把每5分钟一条的数据聚合成每州每日汇总。
--         从约300万行减少到9,140行（5年×5州×约365天）
--
-- Also partitioned by date and clustered by region_id
-- 同样按日期分区、按州聚簇
-- =============================================================

{{ config(
    materialized='table',
    partition_by={
        "field": "settlement_date_day",
        "data_type": "date"
    },
    cluster_by=["region_id"]
) }}

with daily_agg as (
    select
        -- Time dimensions / 时间维度
        settlement_date_day,    -- Date / 日期
        region_id,              -- State / 州
        year,                   -- Year / 年
        month,                  -- Month / 月

        -- Price aggregations / 电价聚合
        -- Average price for the day / 当日平均电价
        avg(price_aud_per_mwh)  as avg_price_aud_per_mwh,

        -- Highest price of the day (captures price spikes) / 当日最高电价（捕捉价格峰值）
        max(price_aud_per_mwh)  as max_price_aud_per_mwh,

        -- Lowest price of the day (captures negative prices) / 当日最低电价（捕捉负电价）
        min(price_aud_per_mwh)  as min_price_aud_per_mwh,

        -- Demand aggregations / 需求聚合
        -- Average demand for the day / 当日平均需求
        avg(total_demand_mw)    as avg_demand_mw,

        -- Peak demand of the day / 当日峰值需求
        max(total_demand_mw)    as max_demand_mw,

        -- Number of 5-minute intervals in the day (should be 288)
        -- 当天的5分钟间隔数量（应为288个）
        count(*)                as interval_count

    from {{ ref('stg_nem_data') }}  -- Reference staging model / 引用清洗层模型
    group by 1, 2, 3, 4
)

select * from daily_agg
