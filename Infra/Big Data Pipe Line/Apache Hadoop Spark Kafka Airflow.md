---
id: Big Data Pipeline (Hadoop, Spark, Kafka, Airflow)
started: 2025-11-10
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Big Data Pipeline (Hadoop, Spark, Kafka, Airflow)

## 1. 개요 (Overview)
현대의 데이터 엔지니어링은 단순히 데이터를 저장하는 것을 넘어, 실시간으로 수집(Ingest), 가공(Process), 적재(Store), 분석(Analyze)하는 거대한 파이프라인을 구축하는 것을 의미합니다.

이 문서에서는 가장 표준적이고 강력한 오픈 소스 데이터 파이프라인 스택인 **Kafka - Hadoop(HDFS) - Spark - Airflow**의 유기적인 연결과 각 컴포넌트의 역할, 그리고 아키텍처 패턴(Lambda, Kappa)을 다룹니다.

---

## 2. 아키텍처 패턴 (Architecture Patterns)

### 2.1 Lambda Architecture (람다 아키텍처)
전통적이고 안정적인 방식입니다. 시스템을 두 개의 레이어로 나눕니다.
- **Batch Layer (Hadoop+Spark)**: 원천 데이터(Master Dataset)를 저장하고 주기적으로 일괄 처리하여 정확한 뷰(Batch View)를 만듭니다. (정확성 보장).
- **Speed Layer (Kafka+Spark Streaming)**: 실시간 데이터를 처리하여 실시간 뷰(Real-time View)를 만듭니다. (빠른 응답 보장, 약간의 오차 허용).
- **Serving Layer**: 두 뷰를 합쳐서 사용자에게 제공합니다.

### 2.2 Kappa Architecture (카파 아키텍처)
람다 아키텍처의 복잡성(로직 중복)을 해결하기 위해 고안되었습니다.
- **Batch Layer를 제거**하고, 모든 데이터를 **Log(Kafka)** 로 취급합니다.
- 배치 처리가 필요하면 Kafka의 데이터를 처음부터 다시 스트리밍(Replay)하여 처리합니다.

---

## 3. 핵심 컴포넌트 상세 (Components Detail)

### 3.1 Apache Kafka (Ingestion Layer)
- **역할**: 고성능 분산 메시지 버퍼.
- **특징**:
    - 모든 데이터 파이프라인의 **입구** 역할을 합니다.
    - 데이터가 폭주(Spike)해도 디스크 기반 로그 구조 덕분에 유실 없이 받아냅니다 (Backpressure 해소).
    - Spark Streaming이나 Logstash 같은 컨슈머들이 각자의 속도로 데이터를 가져갈 수 있게 해줍니다(Decoupling).

### 3.2 Apache Hadoop HDFS (Storage Layer)
- **역할**: 데이터 레이크(Data Lake). 페타바이트급 영구 저장소.
- **특징**:
    - **Namenode**: 파일의 메타데이터(위치 정보)를 관리.
    - **Datanode**: 실제 데이터 블록(Block)을 저장. 보통 3-way Replication으로 데이터 유실을 방지합니다.
    - 최근에는 S3, GCS 같은 클라우드 스토리지로 대체되는 추세입니다.

### 3.3 Apache Spark (Processing Layer)
- **역할**: 메모리 기반의 초고속 분산 데이터 처리 엔진.
- **특징**:
    - **RDD(Resilient Distributed Dataset)**: 불변성(Immutable)을 가진 분산 객체. 메모리 내에서 연산을 수행하므로 MapReduce(디스크 기반)보다 10~100배 빠릅니다.
    - **Spark SQL (DataFrame)**: SQL 문법으로 데이터를 쉽게 다룰 수 있습니다.
    - **Spark Streaming**: Kafka 등에서 데이터를 받아 마이크로 배치(Micro-batch) 단위로 실시간 처리합니다.

### 3.4 Apache Airflow (Workflow/Scheduling Layer)
- **역할**: 파이프라인의 오케스트레이션(지휘자). "Spark 작업이 끝나면 -> 결과를 DB에 넣고 -> 슬랙으로 알림을 보내라"와 같은 순서와 의존성을 관리합니다.
- **특징**:
    - **DAG (Directed Acyclic Graph)**: 파이프라인을 Python 코드로 정의합니다 (Infrastructure as Code).
    - **Backfill**: 과거 날짜의 데이터를 다시 처리(재실행)하는 기능이 강력합니다.

---

## 4. 데이터 흐름 시나리오 (End-to-End Scenario)

**시나리오**: 쇼핑몰의 사용자 클릭 로그(Clickstream) 분석

1. **로그 생성**: 웹 서버(Nginx)가 사용자의 클릭 로그를 JSON 형태로 생성.
2. **수집 (Fluentd/Filebeat -> Kafka)**:
   - 로그 에이전트가 파일을 읽어 Kafka의 `user_clicks` 토픽으로 전송.
3. **실시간 처리 (Spark Streaming)**:
   - `user_clicks` 토픽을 구독.
   - 1분 단위로 "상품별 클릭 수"를 집계하여 Redis에 저장 (실시간 대시보드용).
4. **장기 적재 (Kafka Connect -> HDFS/S3)**:
   - 동시에 원본 로그는 HDFS의 `/data/raw/clicks/YYYY/MM/DD/` 경로에 Parquet 포맷으로 적재.
5. **배치 분석 (Airflow -> Spark Batch)**:
   - 매일 새벽 2시에 Airflow가 DAG를 실행.
   - 어제 날짜의 HDFS 데이터를 읽어 "일간 베스트 상품 랭킹"을 계산하고, 결과를 RDBMS(MySQL)에 적재.
   - 완료 후 마케팅 팀에 이메일 발송.

---

## 5. 예제 코드 (Example)

### 5.1 Airflow DAG (Python)
복잡한 의존성을 관리하는 Airflow DAG 예제입니다.

```python
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.email import EmailOperator
from airflow.sensors.filesystem import FileSensor
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-eng',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'daily_sales_batch',
    default_args=default_args,
    schedule_interval='0 2 * * *', # 매일 새벽 2시
    start_date=datetime(2025, 1, 1),
    catchup=False
) as dag:

    # 1. 원본 데이터 파일이 도착했는지 감지
    wait_for_file = FileSensor(
        task_id='wait_for_raw_data',
        filepath='/data/raw/sales/{{ ds }}/*.parquet',
        fs_conn_id='hdfs_default',
        poke_interval=60,
        timeout=3600
    )

    # 2. 스파크 잡 실행 (집계)
    process_sales = SparkSubmitOperator(
        task_id='process_sales_data',
        application='/apps/spark/jobs/daily_sales_agg.py',
        conn_id='spark_default',
        conf={'spark.driver.memory': '4g'},
        application_args=['--date', '{{ ds }}']
    )

    # 3. 성공 알림 메일
    send_email = EmailOperator(
        task_id='send_success_email',
        to='manager@example.com',
        subject='Daily Sales Batch Complete ({{ ds }})',
        html_content='Batch job finished successfully.'
    )

    # 의존성 설정
    wait_for_file >> process_sales >> send_email
```

### 5.2 Spark Job (PySpark)
```python
from pyspark.sql import SparkSession
import sys

# Spark Session 초기화
spark = SparkSession.builder.appName("DailySalesAgg").getOrCreate()

# Airflow에서 넘겨준 날짜 인자
target_date = sys.argv[1] # ex: 2025-01-01

# HDFS에서 데이터 읽기 (Parquet)
df = spark.read.parquet(f"hdfs://namenode:9000/data/raw/sales/{target_date}/*.parquet")

# 비즈니스 로직: 상품별 매출 합계 계산
result_df = df.groupBy("product_id") \
              .sum("amount") \
              .withColumnRenamed("sum(amount)", "total_sales")

# 결과를 RDBMS에 저장 (JDBC)
result_df.write \
    .format("jdbc") \
    .option("url", "jdbc:mysql://db-server:3306/mart") \
    .option("dbtable", "daily_product_sales") \
    .option("user", "etl_user") \
    .option("password", "secret") \
    .mode("append") \
    .save()

spark.stop()
```

# Reference
- [Designing Data-Intensive Applications (Martin Kleppmann)](https://dataintensive.net/)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [Spark Programming Guide](https://spark.apache.org/docs/latest/rdd-programming-guide.html)