"""
AEMO NEM Data Pipeline DAG
===========================

English: Automated pipeline to download electricity price and demand data
         from AEMO (Australian Energy Market Operator) and load it into GCP.

中文：自动化数据管道，从澳洲能源市场运营商（AEMO）下载电力价格和需求数据，
      并加载到谷歌云平台（GCP）。

Pipeline Steps / 管道步骤:
    1. Download 300 CSV files from AEMO website / 从AEMO官网下载300个CSV文件
    2. Upload raw files to GCS (data lake) / 上传原始文件到GCS（数据湖）
    3. Load GCS files into BigQuery raw table / 从GCS加载数据到BigQuery原始表
    4. Create partitioned + clustered table / 创建分区+聚簇优化表

Author / 作者: KD
Project / 项目: DE Zoomcamp Final Project
Date / 日期: 2024
"""

import os
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


# ============================================================
# Configuration / 配置区
# Modify these values for your own GCP project
# 根据你自己的GCP项目修改以下配置
# ============================================================
GCP_PROJECT_ID = "taxi-rides-ny-v2"       # Your GCP project ID / 你的GCP项目ID
GCP_BUCKET = "aemo-nem-data-lake-v2"      # Your GCS bucket name / 你的GCS桶名
BIGQUERY_DATASET = "aemo_electricity"     # BigQuery dataset name / 数据集名
BIGQUERY_TABLE_RAW = "raw_nem_data"       # Raw table name / 原始表名
BIGQUERY_TABLE_FINAL = "nem_partitioned"  # Final optimised table / 优化后的分区表名

# The 5 states in Australia's NEM / 澳洲国家电力市场的5个州
REGIONS = ["NSW1", "VIC1", "QLD1", "SA1", "TAS1"]

# Date range: 5 years of data / 时间范围：5年数据
START_YEAR, START_MONTH = 2020, 1   # Start: January 2020 / 开始：2020年1月
END_YEAR, END_MONTH = 2024, 12      # End: December 2024 / 结束：2024年12月

# Temporary local storage inside Airflow container
# Airflow容器内的临时本地存储路径
LOCAL_STORAGE_PATH = "/tmp/aemo_data"

# AEMO base URL / AEMO数据URL前缀
AEMO_BASE_URL = "https://aemo.com.au/aemo/data/nem/priceanddemand"


# ============================================================
# Task 1: Download CSV files from AEMO
# 任务1：从AEMO下载CSV文件
# ============================================================
def download_aemo_data(**context):
    """
    English: Download all AEMO CSV files to local storage inside the container.
             Uses a loop over time periods and regions to generate all 300 URLs.
             Supports resume — skips files that already exist.

    中文：把所有AEMO CSV文件下载到容器本地存储。
          用双层循环（时间×州）自动生成300个文件的URL。
          支持断点续传——已存在的文件自动跳过。
    """
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)

    downloaded = 0
    failed = 0

    # Loop through all months from start to end date
    # 循环遍历从开始到结束的所有月份
    current = datetime(START_YEAR, START_MONTH, 1)
    end_date = datetime(END_YEAR, END_MONTH, 1)

    while current <= end_date:
        year_month = current.strftime("%Y%m")  # e.g. 202001 / 例如：202001

        for region in REGIONS:
            filename = f"PRICE_AND_DEMAND_{year_month}_{region}.csv"
            local_path = f"{LOCAL_STORAGE_PATH}/{filename}"

            # Skip if file already exists (resume support)
            # 文件已存在则跳过（断点续传）
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                print(f"[SKIP / 跳过] Already exists: {filename}")
                downloaded += 1
                continue

            url = f"{AEMO_BASE_URL}/{filename}"

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(response.content)

                print(f"[OK / 成功] Downloaded: {filename}")
                downloaded += 1

            except Exception as e:
                print(f"[FAIL / 失败] {filename}: {e}")
                failed += 1
                # Continue with other files, don't stop the whole task
                # 继续处理其他文件，不中断整个任务

        current += relativedelta(months=1)

    print(f"\nDownload complete / 下载完成: {downloaded} succeeded, {failed} failed")

    if downloaded == 0:
        raise Exception("No files downloaded. Check network or AEMO URL. / 没有下载到任何文件，请检查网络或AEMO URL")


# ============================================================
# Task 2: Upload local CSV files to GCS
# 任务2：把本地CSV文件上传到GCS
# ============================================================
def upload_to_gcs(**context):
    """
    English: Upload all downloaded CSV files to GCS (data lake).
             Why GCS? Cheap object storage, raw data preserved permanently,
             can reload to BigQuery anytime without re-downloading from AEMO.

    中文：把所有下载好的CSV文件上传到GCS（数据湖）。
          为什么用GCS？廉价对象存储，原始数据永久保留，
          随时可重新加载到BigQuery，无需重新从AEMO下载。
    """
    from google.cloud import storage

    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCP_BUCKET)

    uploaded = 0
    files = [f for f in os.listdir(LOCAL_STORAGE_PATH) if f.endswith(".csv")]

    print(f"Uploading {len(files)} files to gs://{GCP_BUCKET}/raw/")
    print(f"准备上传 {len(files)} 个文件到 gs://{GCP_BUCKET}/raw/")

    for filename in files:
        local_path = f"{LOCAL_STORAGE_PATH}/{filename}"
        gcs_path = f"raw/{filename}"  # Store under raw/ folder / 存放在raw/文件夹下

        blob = bucket.blob(gcs_path)

        # Skip if already exists in GCS / 已在GCS中存在则跳过
        if blob.exists():
            print(f"[SKIP / 跳过] Already in GCS: {gcs_path}")
            uploaded += 1
            continue

        blob.upload_from_filename(local_path)
        print(f"[OK / 成功] {filename} → gs://{GCP_BUCKET}/{gcs_path}")
        uploaded += 1

    print(f"\nUpload complete / 上传完成: {uploaded} files")


# ============================================================
# Task 3: Load GCS files into BigQuery raw table
# 任务3：从GCS批量加载数据到BigQuery原始表
# ============================================================
def load_gcs_to_bigquery(**context):
    """
    English: Load all CSV files from GCS into BigQuery raw table using a wildcard URI.
             Uses WRITE_TRUNCATE to overwrite on each run — prevents duplicate data.
             autodetect=True lets BigQuery infer column types automatically.

    中文：用通配符URI把GCS里所有CSV文件一次性加载到BigQuery原始表。
          使用WRITE_TRUNCATE（覆盖写）确保每次运行数据不重复。
          autodetect=True让BigQuery自动推断列的数据类型。
    """
    from google.cloud import bigquery

    client = bigquery.Client(project=GCP_PROJECT_ID)

    # Wildcard URI matches all AEMO files in GCS
    # 通配符URI匹配GCS里所有AEMO文件
    gcs_uri = f"gs://{GCP_BUCKET}/raw/PRICE_AND_DEMAND_*.csv"
    table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE_RAW}"

    job_config = bigquery.LoadJobConfig(
        autodetect=True,            # Auto-detect column types / 自动检测列类型
        skip_leading_rows=1,        # Skip CSV header row / 跳过CSV标题行
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Overwrite / 覆盖写
        source_format=bigquery.SourceFormat.CSV,
    )

    print(f"Loading: gs://{GCP_BUCKET}/raw/ → {table_id}")
    print(f"加载中：gs://{GCP_BUCKET}/raw/ → {table_id}")

    load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()  # Wait for job to complete / 等待任务完成

    table = client.get_table(table_id)
    print(f"Load complete / 加载完成: {table.num_rows:,} rows / 行")


# ============================================================
# Task 4: Create partitioned + clustered table
# 任务4：创建分区+聚簇优化表
# ============================================================
def create_partitioned_table(**context):
    """
    English: Transform the raw table into a partitioned + clustered optimised table.

             Partitioning by date: BigQuery only scans relevant date partitions.
             e.g. querying 2023 data only reads the 2023 partition, not all 5 years.

             Clustering by region_id: Within each partition, rows with the same
             state are stored together — faster filtering by state.

             Result: 80%+ reduction in data scanned for typical analytical queries.

    中文：把原始表转成按日期分区、按州聚簇的优化表。

          按日期分区：BigQuery只扫描相关日期的分区。
          例如查询2023年数据，只读2023年那块，不扫描全部5年。

          按region_id聚簇：同一州的数据物理上存在一起，
          按州筛选时BigQuery可跳过其他州的数据块。

          效果：典型分析查询的数据扫描量减少80%以上，省钱省时间。
    """
    from google.cloud import bigquery

    client = bigquery.Client(project=GCP_PROJECT_ID)
    table_id = f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE_FINAL}"

    sql = f"""
    CREATE OR REPLACE TABLE `{table_id}`
    PARTITION BY DATE(settlement_date)
    CLUSTER BY region_id
    AS
    SELECT
        -- Settlement timestamp / 结算时间戳
        SETTLEMENTDATE AS settlement_date,

        -- State code (NSW1, VIC1, QLD1, SA1, TAS1) / 州代码
        REGION AS region_id,

        -- Total electricity demand in megawatts / 总用电需求（兆瓦）
        SAFE_CAST(TOTALDEMAND AS FLOAT64) AS total_demand_mw,

        -- Regional reference price in AUD per MWh / 地区参考价格（澳元/兆瓦时）
        SAFE_CAST(RRP AS FLOAT64) AS price_aud_per_mwh,

        -- Period type / 时段类型
        PERIODTYPE AS period_type

    FROM `{GCP_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE_RAW}`
    WHERE SETTLEMENTDATE IS NOT NULL
      AND REGION IN ('NSW1', 'VIC1', 'QLD1', 'SA1', 'TAS1')
    """

    print(f"Creating partitioned table / 创建分区表: {table_id}")
    query_job = client.query(sql)
    query_job.result()

    table = client.get_table(table_id)
    print(f"Success / 成功: {table.num_rows:,} rows, "
          f"partitioned by settlement_date, clustered by region_id")
    print(f"成功：{table.num_rows:,} 行，按settlement_date分区，按region_id聚簇")


# ============================================================
# DAG Definition / DAG定义
# Connects the 4 tasks in sequence / 把4个任务串联起来
# ============================================================
with DAG(
    dag_id="aemo_nem_data_pipeline",
    description="AEMO NEM electricity data pipeline / 澳洲电力市场数据管道",
    schedule_interval="@monthly",   # Run monthly / 每月运行
    start_date=datetime(2020, 1, 1),
    catchup=False,       # Don't backfill / 不补跑历史
    max_active_runs=1,   # One run at a time / 同时只跑一个实例
    tags=["aemo", "final-project", "gcp"],
) as dag:

    # Task 1: Download / 下载
    t1_download = PythonOperator(
        task_id="download_aemo_data",
        python_callable=download_aemo_data,
        execution_timeout=None,  # No timeout — 300 files takes time / 不设超时，300个文件需要时间
    )

    # Task 2: Upload to GCS / 上传GCS
    t2_upload_gcs = PythonOperator(
        task_id="upload_to_gcs",
        python_callable=upload_to_gcs,
    )

    # Task 3: Load to BigQuery / 加载BigQuery
    t3_load_bq = PythonOperator(
        task_id="load_gcs_to_bigquery",
        python_callable=load_gcs_to_bigquery,
    )

    # Task 4: Create optimised table / 创建优化表
    t4_partition = PythonOperator(
        task_id="create_partitioned_table",
        python_callable=create_partitioned_table,
    )

    # Execution order / 执行顺序:
    # Download → Upload GCS → Load BigQuery → Create partitioned table
    # 下载 → 上传GCS → 加载BigQuery → 创建分区表
    t1_download >> t2_upload_gcs >> t3_load_bq >> t4_partition
