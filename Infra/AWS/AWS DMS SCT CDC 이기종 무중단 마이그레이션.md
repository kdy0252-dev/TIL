---
id: AWS DMS SCT CDC 이기종 무중단 마이그레이션
started: 2026-07-15
tags:
  - ✅DONE
  - AWS
  - DMS
  - Database
  - Migration
group:
  - "[[Infra AWS]]"
---

# AWS DMS, CDC와 AWS SCT로 무중단 Database Migration하기

운영 Database Engine을 바꾸는 일은 Data를 한 번 복사하는 작업이 아니다. Oracle의 Schema와 PL/SQL을 PostgreSQL 문법과 의미로 바꾸고, 수백 GB 이상의 기존 Data를 옮기며, 그동안 발생하는 변경도 놓치지 않아야 한다. 마지막에는 Application이 새 Database를 사용하도록 전환하고 문제가 생겼을 때 돌아갈 경로까지 준비해야 한다.

이 글은 다음 운영 사례를 처음부터 끝까지 다룬다.

```text
Source : Amazon RDS for Oracle
Target : Amazon Aurora PostgreSQL-Compatible
Schema : BOOKING -> booking
Data   : 예약·결제 업무 Table
Goal   : 기존 Data 전체 적재 + 실시간 CDC + 짧고 통제된 Cutover
```

후반부에서는 Database Engine은 같지만 물리적으로 떨어진 PostgreSQL을 Aurora PostgreSQL로 옮기면서 비정규화 Table을 여러 관계형 Table로 분리하는 사례도 다룬다. 같은 Engine이라고 Schema 구조까지 같다는 뜻은 아니다.

예제의 Resource 이름, ARN, Subnet, Security Group과 Database Endpoint는 환경에 맞게 바꿔야 한다. AWS DMS Engine과 Source·Target Version의 지원 조합도 작업 시점의 AWS 공식 호환성 표에서 다시 확인한다.

## 먼저 바로잡아야 할 말: 정말 Zero Downtime인가

AWS DMS의 `full-load-and-cdc`는 Source를 계속 운영하면서 기존 Data와 이후 변경을 Target으로 보낼 수 있다. 하지만 마지막 순간까지 두 Database에 자유롭게 쓰면서 아무 조정 없이 접속 주소만 바꾸면 다음 Race Condition이 생긴다.

```text
T1  DMS가 Source의 마지막 확인 Transaction까지 Target에 반영
T2  Application 설정을 Target으로 변경하기 시작
T3  아직 남은 구버전 Instance가 Source에 새 예약 저장
T4  DMS를 먼저 중지했다면 새 예약이 Target에 없음
T5  일부 요청은 Source, 일부 요청은 Target에 기록됨
```

따라서 일반적인 단방향 DMS 전환에는 짧은 **write fence**가 필요하다. 새 쓰기를 잠시 차단하거나 Durable Queue에 보관하고, Source의 마지막 변경이 Target에 반영된 것을 확인한 뒤 Writer를 Target으로 바꾼다. 읽기 서비스는 계속 제공할 수 있고 Queue를 사용하면 요청 접수도 계속할 수 있지만, 동기식 쓰기 응답까지 항상 유지되는 절대적 무중단과는 다르다.

이 글에서 말하는 무중단은 다음 목표다.

- 사전 전체 적재와 CDC 동안 기존 서비스는 정상적으로 Source를 읽고 쓴다.
- Cutover 동안 읽기는 유지한다.
- 쓰기는 수십 초 수준의 통제된 fence를 사용하거나 Durable Queue로 접수한다.
- RPO 0을 검증한 다음 Target Writer를 연다.
- 전환 전후의 Rollback 경계를 Runbook에 명시한다.

## 세 도구가 담당하는 범위

| 도구 | 담당하는 일 | 하지 않는 일 |
|---|---|---|
| AWS SCT | Schema 변환 평가, Table·Index·View·Procedure 등 DDL 변환 | 운영 중 변경 Data의 지속 복제 |
| AWS DMS Full Load | 기존 Row를 Source에서 Target으로 대량 적재 | 모든 Schema Object의 완전한 변환 |
| AWS DMS CDC | Redo Log의 INSERT·UPDATE·DELETE를 읽어 Target에 반영 | Application 전환과 업무 정합성 판단 |

AWS SCT는 Schema와 Code를 변환하고 AWS DMS는 Data를 옮긴다. DMS만 실행하면 Sequence, Secondary Index, Default, Trigger, Stored Procedure와 같은 Object가 기대대로 이관되지 않는다. 반대로 SCT만 실행하면 변환 시점 이후에 생긴 운영 Data가 Target에 없다.

```text
                       +----------------------+
                       | AWS SCT Workstation  |
                       | Assessment + DDL     |
                       +----------+-----------+
                                  |
                                  v
+------------------+   redo   +------------------+   apply   +------------------+
| RDS for Oracle   |--------->| DMS Replication |---------->| Aurora PostgreSQL|
| BOOKING Schema   |          | Full Load + CDC |           | booking Schema   |
+--------+---------+          +------------------+           +--------+---------+
         ^                                                           ^
         |                                                           |
         +---------------- Application Cutover ----------------------+
```

## 1단계: 변환보다 먼저 범위를 고정한다

Migration 대상은 “Database 전체”보다 업무 단위로 명시한다. 다음 Inventory를 먼저 만든다.

| 분류 | 확인할 내용 |
|---|---|
| Table | Row 수, 용량, PK, LOB, Partition, 변경량 |
| Code | Package, Procedure, Function, Trigger, Scheduler Job |
| 의존성 | DB Link, Synonym, 외부 File, Sequence, Materialized View |
| 의미 차이 | 빈 문자열, 날짜·시간대, 숫자 정밀도, 대소문자, 정렬 규칙 |
| 운영 목표 | 허용 CDC Lag, Cutover 시간, RPO, RTO, Rollback 시점 |

CDC 대상 Table에는 PK 또는 안정적인 Unique Key가 있어야 한다. Key가 없으면 UPDATE와 DELETE의 대상을 식별하기 어렵고, Oracle에서 모든 Column의 Supplemental Logging이 필요해져 Redo 양도 커진다. 먼저 다음 Query로 누락을 찾는다.

```sql
SELECT tables.owner,
       tables.table_name
FROM all_tables tables
LEFT JOIN all_constraints constraints
       ON constraints.owner = tables.owner
      AND constraints.table_name = tables.table_name
      AND constraints.constraint_type = 'P'
WHERE tables.owner = 'BOOKING'
  AND constraints.constraint_name IS NULL
ORDER BY tables.table_name;
```

실전 예제의 핵심 Table은 다음과 같다.

```sql
CREATE TABLE BOOKING.RESERVATION (
    RESERVATION_ID NUMBER(19) PRIMARY KEY,
    TENANT_ID      NUMBER(19) NOT NULL,
    CUSTOMER_NAME  VARCHAR2(100 CHAR) NOT NULL,
    STATUS         VARCHAR2(30 CHAR) NOT NULL,
    TOTAL_AMOUNT   NUMBER(19, 2) NOT NULL,
    NOTE           CLOB,
    CREATED_AT     TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    UPDATED_AT     TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    VERSION        NUMBER(19) DEFAULT 0 NOT NULL
);

CREATE SEQUENCE BOOKING.RESERVATION_SEQ START WITH 1000000 CACHE 1000;

CREATE INDEX BOOKING.IDX_RESERVATION_TENANT_CREATED
    ON BOOKING.RESERVATION (TENANT_ID, CREATED_AT);

CREATE TABLE BOOKING.MIGRATION_SENTINEL (
    ID          NUMBER(19) PRIMARY KEY,
    LAST_MARKER VARCHAR2(100 CHAR) NOT NULL,
    UPDATED_AT  TIMESTAMP(6) WITH TIME ZONE NOT NULL
);

INSERT INTO BOOKING.MIGRATION_SENTINEL (ID, LAST_MARKER, UPDATED_AT)
VALUES (1, 'INITIAL', SYSTIMESTAMP);

COMMIT;
```

## 2단계: Network와 보안 경로를 먼저 검증한다

DMS Replication Instance는 Source와 Target에 모두 TCP 연결할 수 있어야 한다.

```text
DMS Security Group -> Oracle Security Group : TCP 1521
DMS Security Group -> Aurora Security Group : TCP 5432
```

- DMS Replication Subnet Group에는 서로 다른 Availability Zone의 Private Subnet을 넣는다.
- On-premises Oracle이면 Direct Connect 또는 Site-to-Site VPN의 Route, DNS와 MTU까지 검증한다.
- Source와 Target을 Public으로 노출하지 않는다.
- Endpoint는 `ssl-mode=require` 이상을 사용한다. 인증서 검증이 가능한 환경이면 `verify-full`을 사용한다.
- Database Credential은 CLI와 Git에 쓰지 않고 Secrets Manager에 둔다.

AWS DMS용 Secret의 최소 형태는 다음과 같다. 실제 값이 들어간 파일은 만들거나 Commit하지 않는다.

```json
{
  "username": "dms_user",
  "password": "REPLACE_IN_SECRETS_MANAGER",
  "port": 1521,
  "host": "source-oracle.cluster-example.ap-northeast-2.rds.amazonaws.com"
}
```

Target도 같은 구조로 `dms_target` User, 5432 Port와 Aurora Writer Endpoint를 저장한다. RDS가 관리하는 Master Secret은 DMS에 필요한 Host와 Port가 없을 수 있으므로 DMS 전용 User와 Secret을 별도로 만든다. Secret 접근 Role은 해당 Secret의 `secretsmanager:GetSecretValue`와 해당 KMS Key의 복호화 권한만 갖게 한다.

## 3단계: Oracle Source를 CDC가 가능한 상태로 만든다

### Archive Redo와 Supplemental Logging

RDS for Oracle은 Automated Backup을 활성화한 뒤 Archive Redo 보존 시간을 CDC 중단을 복구할 수 있을 만큼 확보한다. 다음은 24시간 보존 예제다. 장애 대응 시간이 24시간보다 길 수 있다면 더 길게 잡고 Storage 증가를 감시한다.

```sql
BEGIN
    rdsadmin.rdsadmin_util.set_configuration(
        name  => 'archivelog retention hours',
        value => '24'
    );
END;
/

COMMIT;

BEGIN
    rdsadmin.rdsadmin_util.alter_supplemental_logging('ADD');
    rdsadmin.rdsadmin_util.alter_supplemental_logging('ADD', 'PRIMARY KEY');
END;
/
```

설정을 확인한다.

```sql
SELECT supplemental_log_data_min,
       supplemental_log_data_pk
FROM v$database;

SELECT NAME, VALUE
FROM rdsadmin.rds_configuration
WHERE NAME = 'archivelog retention hours';
```

Table 단위로 설정할 때는 다음처럼 적용한다.

```sql
ALTER TABLE BOOKING.RESERVATION
    ADD SUPPLEMENTAL LOG DATA (PRIMARY KEY) COLUMNS;
```

### DMS 전용 User와 권한

운영 Application User를 재사용하지 않는다. 다음은 RDS for Oracle에서 LogMiner를 사용하는 출발점이다.

```sql
CREATE USER dms_user IDENTIFIED BY "USE_A_SECRET_VALUE";

GRANT CREATE SESSION TO dms_user;
GRANT SELECT ANY TRANSACTION TO dms_user;
GRANT LOGMINING TO dms_user;
GRANT EXECUTE ON rdsadmin.rdsadmin_util TO dms_user;
GRANT SELECT ON BOOKING.RESERVATION TO dms_user;
GRANT SELECT ON BOOKING.PAYMENT TO dms_user;
GRANT SELECT ON BOOKING.MIGRATION_SENTINEL TO dms_user;

BEGIN
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_VIEWS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_TAB_PARTITIONS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_INDEXES', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_OBJECTS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_TABLES', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_USERS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_CATALOG', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_CONSTRAINTS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_CONS_COLUMNS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_TAB_COLS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_IND_COLUMNS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('ALL_LOG_GROUPS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$ARCHIVED_LOG', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$LOG', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$LOGFILE', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$DATABASE', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$THREAD', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$PARAMETER', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$NLS_PARAMETERS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$TIMEZONE_NAMES', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$TRANSACTION', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$LOGMNR_LOGS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('V_$LOGMNR_CONTENTS', 'DMS_USER', 'SELECT');
    rdsadmin.rdsadmin_util.grant_sys_object('DBMS_LOGMNR', 'DMS_USER', 'EXECUTE');
END;
/
```

Oracle Version, Multi-tenant 구성과 암호화 Column 사용 여부에 따라 추가 Grant가 필요하다. AWS의 Oracle Source 권한 표를 기준으로 사용 중인 Version에 필요한 `V_$CONTAINERS`, `DBA_REGISTRY`, `REGISTRY$SQLPATCH`, `ALL_ENCRYPTED_COLUMNS` 등을 추가하고 DMS Endpoint Test로 검증한다.

### LogMiner와 Binary Reader 선택

처음에는 설정이 단순한 LogMiner로 시작한다. Source의 Redo 발생량이 많고 LogMiner의 CPU·I/O 부담이나 CDC Lag가 문제라면 Binary Reader를 검토한다. Binary Reader는 권한과 Archive Log 접근 설정이 더 복잡하므로 운영 부하 시험 없이 단지 더 빠를 것이라는 이유로 선택하지 않는다.

## 4단계: AWS SCT로 Schema와 Code를 변환한다

AWS SCT는 Source와 Target을 연결한 Workstation에서 실행한다. 최신 JDBC Driver를 별도 보관하고, Production 작업 전에는 동일 Version의 복제 환경에서 Assessment를 수행한다.

1. Oracle Source와 Aurora PostgreSQL Target Project를 만든다.
2. `BOOKING` Schema만 Analysis Scope에 넣는다.
3. Database Migration Assessment Report를 생성한다.
4. 자동 변환 가능 Object와 수동 조치 Action Item을 분류한다.
5. Table, PK와 기본 Type을 먼저 변환한다.
6. Function, Procedure, Trigger와 View는 업무 Test를 거쳐 별도 적용한다.
7. 변환 SQL을 Version 관리되는 신규 Migration으로 저장한다.

SCT에서 변환된 Schema를 선택해도 즉시 Target에 적용되는 것은 아니다. 변환 결과를 검토한 다음 명시적으로 Target에 적용하거나 SQL로 내보낸다. 이미 운영에 실행된 Migration을 수정하지 말고 새 Migration을 추가한다.

### Type 변환은 문법보다 의미를 확인한다

```sql
CREATE SCHEMA IF NOT EXISTS booking;

CREATE TABLE booking.reservation (
    reservation_id BIGINT PRIMARY KEY,
    tenant_id      BIGINT NOT NULL,
    customer_name  VARCHAR(100) NOT NULL,
    status         VARCHAR(30) NOT NULL,
    total_amount   NUMERIC(19, 2) NOT NULL,
    note           TEXT,
    created_at     TIMESTAMPTZ NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL,
    version        BIGINT DEFAULT 0 NOT NULL,
    CONSTRAINT ck_reservation_status
        CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED'))
);
```

다음 차이는 자동 변환 성공 표시만 보고 넘기면 안 된다.

- Oracle의 빈 문자열은 `NULL`처럼 취급되지만 PostgreSQL의 `''`는 값이다.
- `NUMBER`는 실제 정밀도와 범위를 보고 `BIGINT` 또는 `NUMERIC(p, s)`로 정한다.
- Oracle `DATE`에는 시각이 있지만 Time Zone은 없다. 업무 기준 Zone을 먼저 정한다.
- `TIMESTAMP WITH LOCAL TIME ZONE`과 PostgreSQL `TIMESTAMPTZ`의 표시 의미를 Test한다.
- `CHAR`의 공백 Padding과 문자열 비교 결과가 달라질 수 있다.
- 따옴표로 만든 대소문자 식별자는 PostgreSQL 운영을 어렵게 하므로 소문자 Naming으로 변환한다.
- CLOB·BLOB의 최대 크기를 측정한 뒤 DMS LOB Mode를 정한다.

### PL/SQL은 수동 검토 대상이다

Oracle Package가 다음처럼 수수료를 계산한다고 가정한다.

```sql
CREATE OR REPLACE FUNCTION BOOKING.CALCULATE_CANCEL_FEE(
    P_TOTAL_AMOUNT IN NUMBER,
    P_DEPARTURE_AT IN TIMESTAMP WITH TIME ZONE,
    P_CANCELLED_AT IN TIMESTAMP WITH TIME ZONE
) RETURN NUMBER IS
BEGIN
    RETURN CASE
        WHEN P_CANCELLED_AT <= P_DEPARTURE_AT - INTERVAL '7' DAY THEN 0
        WHEN P_CANCELLED_AT <= P_DEPARTURE_AT - INTERVAL '1' DAY THEN ROUND(P_TOTAL_AMOUNT * 0.20, 2)
        ELSE ROUND(P_TOTAL_AMOUNT * 0.50, 2)
    END;
END;
/
```

PostgreSQL 변환 결과는 실행만 확인하지 않고 경계값을 Test한다.

```sql
CREATE OR REPLACE FUNCTION booking.calculate_cancel_fee(
    total_amount NUMERIC(19, 2),
    departure_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
) RETURNS NUMERIC(19, 2)
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT CASE
        WHEN cancelled_at <= departure_at - INTERVAL '7 days' THEN 0::NUMERIC(19, 2)
        WHEN cancelled_at <= departure_at - INTERVAL '1 day' THEN ROUND(total_amount * 0.20, 2)
        ELSE ROUND(total_amount * 0.50, 2)
    END
$$;
```

```sql
SELECT booking.calculate_cancel_fee(
    100000.00,
    TIMESTAMPTZ '2026-08-10 12:00:00+09',
    TIMESTAMPTZ '2026-08-03 12:00:00+09'
); -- expected: 0.00
```

FK, Trigger와 일부 Secondary Index는 Full Load 전에 활성화하면 적재 순서와 부하 때문에 실패하거나 느려질 수 있다. Table과 PK는 먼저 준비하되 FK와 업무 Trigger는 Post-load Script로 분리한다. 대형 Secondary Index는 Full Load 완료 뒤 CDC를 유지하는 구간에 미리 생성해 Cutover 시간을 줄이고, 그동안의 CDC Lag 변화를 관측한다.

## 5단계: Aurora PostgreSQL Target을 준비한다

DMS 전용 Role과 Control Schema를 만든다. 아래 권한은 예제 Schema 범위로 제한한다.

```sql
CREATE ROLE dms_target LOGIN PASSWORD 'USE_A_SECRET_VALUE';
CREATE SCHEMA IF NOT EXISTS dms_control AUTHORIZATION dms_target;

GRANT CONNECT ON DATABASE booking_db TO dms_target;
GRANT USAGE ON SCHEMA booking TO dms_target;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA booking TO dms_target;

ALTER DEFAULT PRIVILEGES IN SCHEMA booking
    GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO dms_target;
```

SCT가 적용할 DDL의 Owner와 DMS가 Data를 쓸 Role을 구분한다. Target Table을 SCT로 미리 만들었으므로 DMS의 `TargetTablePrepMode`는 `DO_NOTHING`을 사용한다. DMS가 Table을 Drop하고 다시 만들게 하면 SCT가 만든 Type, Constraint와 Storage 설정을 잃을 수 있다.

Full Load 중에는 FK와 업무 Trigger를 활성화하지 않는다. PostgreSQL Target은 Table별 적재 순서를 보장하지 않으므로 부모보다 자식 Row가 먼저 들어올 수 있다. DMS 전용 Session에만 `session_replication_role=replica`를 적용하는 방법도 있지만 권한과 Trigger 동작 범위를 정확히 이해한 경우에만 사용한다.

## 6단계: DMS Resource와 Endpoint를 만든다

환경값을 Shell에 설정한다. 비밀번호는 환경변수에도 두지 않는다.

```bash
export AWS_REGION=ap-northeast-2
export DMS_SUBNET_GROUP=booking-migration
export DMS_SECURITY_GROUP=sg-0123456789abcdef0
export DMS_SECRET_ROLE_ARN=arn:aws:iam::123456789012:role/dms-secret-access
export SOURCE_SECRET_ARN=arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:dms/oracle-source
export TARGET_SECRET_ARN=arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:dms/aurora-target
```

```bash
aws dms create-replication-subnet-group \
  --region "$AWS_REGION" \
  --replication-subnet-group-identifier "$DMS_SUBNET_GROUP" \
  --replication-subnet-group-description "Booking Oracle to Aurora migration" \
  --subnet-ids subnet-aaaaaaaa subnet-bbbbbbbb

aws dms create-replication-instance \
  --region "$AWS_REGION" \
  --replication-instance-identifier booking-migration \
  --replication-instance-class dms.r5.large \
  --allocated-storage 200 \
  --no-publicly-accessible \
  --multi-az \
  --vpc-security-group-ids "$DMS_SECURITY_GROUP" \
  --replication-subnet-group-identifier "$DMS_SUBNET_GROUP"
```

Instance Class와 Storage는 Source Data 크기만으로 정하지 않는다. Full Load 병렬성, LOB, CDC 변경량, 긴 Transaction과 Target Apply 속도를 부하 시험해 정한다. Freeable Memory, Swap Usage, CPU, Disk Queue와 CDC Latency를 함께 본다.

Endpoint 설정 파일에는 Secret ARN만 둔다.

```json
{
  "DatabaseName": "ORCL",
  "SecretsManagerAccessRoleArn": "arn:aws:iam::123456789012:role/dms-secret-access",
  "SecretsManagerSecretId": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:dms/oracle-source",
  "AddSupplementalLogging": true,
  "FailTasksOnLobTruncation": true
}
```

```json
{
  "DatabaseName": "booking_db",
  "SecretsManagerAccessRoleArn": "arn:aws:iam::123456789012:role/dms-secret-access",
  "SecretsManagerSecretId": "arn:aws:secretsmanager:ap-northeast-2:123456789012:secret:dms/aurora-target",
  "ExecuteTimeout": 120
}
```

각각 `oracle-endpoint.json`, `postgres-endpoint.json`으로 저장했다고 가정한다.

```bash
aws dms create-endpoint \
  --region "$AWS_REGION" \
  --endpoint-identifier booking-oracle-source \
  --endpoint-type source \
  --engine-name oracle \
  --ssl-mode require \
  --oracle-settings file://oracle-endpoint.json

aws dms create-endpoint \
  --region "$AWS_REGION" \
  --endpoint-identifier booking-aurora-target \
  --endpoint-type target \
  --engine-name aurora-postgresql \
  --ssl-mode require \
  --postgre-sql-settings file://postgres-endpoint.json
```

생성 응답의 Replication Instance ARN과 Endpoint ARN을 저장한 뒤 연결을 Test한다.

```bash
aws dms test-connection \
  --region "$AWS_REGION" \
  --replication-instance-arn "$DMS_INSTANCE_ARN" \
  --endpoint-arn "$SOURCE_ENDPOINT_ARN"

aws dms test-connection \
  --region "$AWS_REGION" \
  --replication-instance-arn "$DMS_INSTANCE_ARN" \
  --endpoint-arn "$TARGET_ENDPOINT_ARN"

aws dms describe-connections \
  --region "$AWS_REGION" \
  --filters Name=replication-instance-arn,Values="$DMS_INSTANCE_ARN"
```

## 7단계: Table Mapping을 명시적으로 작성한다

운영 Task에서 `%`로 Schema 전체를 무심코 포함하면 임시 Table과 감사 Table까지 이관할 수 있다. 업무 Table을 열거하고 변경 승인 절차로 추가한다.

```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "100",
      "rule-name": "include-reservation",
      "object-locator": {
        "schema-name": "BOOKING",
        "table-name": "RESERVATION"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "selection",
      "rule-id": "110",
      "rule-name": "include-payment",
      "object-locator": {
        "schema-name": "BOOKING",
        "table-name": "PAYMENT"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "selection",
      "rule-id": "120",
      "rule-name": "include-migration-sentinel",
      "object-locator": {
        "schema-name": "BOOKING",
        "table-name": "MIGRATION_SENTINEL"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "transformation",
      "rule-id": "200",
      "rule-name": "rename-booking-schema",
      "rule-target": "schema",
      "object-locator": {
        "schema-name": "BOOKING"
      },
      "rule-action": "rename",
      "value": "booking"
    }
  ]
}
```

## 8단계: 손실을 숨기지 않는 Task 설정을 사용한다

다음 `task-settings.json`은 SCT가 만든 Target을 보존하고, LOB가 64 MiB를 넘거나 변환·충돌 오류가 발생하면 조용히 건너뛰지 않고 Task를 멈춘다. 실제 LOB 최대 크기가 64 MiB보다 크면 Full LOB Mode와 성능을 별도로 시험한다.

```json
{
  "TargetMetadata": {
    "TargetSchema": "booking",
    "SupportLobs": true,
    "FullLobMode": false,
    "LimitedSizeLobMode": true,
    "LobMaxSize": 64,
    "LobChunkSize": 64,
    "BatchApplyEnabled": false,
    "TaskRecoveryTableEnabled": true
  },
  "FullLoadSettings": {
    "TargetTablePrepMode": "DO_NOTHING",
    "CreatePkAfterFullLoad": false,
    "MaxFullLoadSubTasks": 8,
    "TransactionConsistencyTimeout": 600,
    "CommitRate": 10000
  },
  "Logging": {
    "EnableLogging": true
  },
  "ControlTablesSettings": {
    "ControlSchema": "dms_control",
    "HistoryTimeslotInMinutes": 5,
    "HistoryTableEnabled": true,
    "StatusTableEnabled": true,
    "SuspendedTablesTableEnabled": true
  },
  "ChangeProcessingTuning": {
    "BatchApplyPreserveTransaction": true,
    "CommitTimeout": 1,
    "MemoryLimitTotal": 1024,
    "MemoryKeepTime": 60,
    "StatementCacheSize": 50
  },
  "ChangeProcessingDdlHandlingPolicy": {
    "HandleSourceTableDropped": false,
    "HandleSourceTableTruncated": false,
    "HandleSourceTableAltered": false
  },
  "ErrorBehavior": {
    "DataErrorPolicy": "STOP_TASK",
    "DataTruncationErrorPolicy": "STOP_TASK",
    "TableErrorPolicy": "STOP_TASK",
    "ApplyErrorDeletePolicy": "STOP_TASK",
    "ApplyErrorInsertPolicy": "STOP_TASK",
    "ApplyErrorUpdatePolicy": "STOP_TASK",
    "FullLoadIgnoreConflicts": false
  },
  "ValidationSettings": {
    "EnableValidation": true,
    "ValidationMode": "ROW_LEVEL",
    "ThreadCount": 5,
    "PartitionSize": 10000,
    "FailureMaxCount": 1000,
    "ValidationOnly": false,
    "SkipLobColumns": false
  }
}
```

`BatchApplyEnabled=false`는 Source Transaction의 적용 경계를 이해하기 쉬운 보수적 출발점이다. 처리량 때문에 Batch Apply를 켜려면 PK·Unique Key, LOB 제한과 Error Policy의 상호작용을 별도 시험한다. 설정값을 복사한 뒤 바로 운영에 적용하지 말고 Production과 같은 Engine Version의 Rehearsal Task에서 유효성과 처리량을 확인한다.

## 9단계: Task 생성 전 사전 평가를 통과시킨다

```bash
aws dms create-replication-task \
  --region "$AWS_REGION" \
  --replication-task-identifier booking-full-load-cdc \
  --source-endpoint-arn "$SOURCE_ENDPOINT_ARN" \
  --target-endpoint-arn "$TARGET_ENDPOINT_ARN" \
  --replication-instance-arn "$DMS_INSTANCE_ARN" \
  --migration-type full-load-and-cdc \
  --table-mappings file://table-mappings.json \
  --replication-task-settings file://task-settings.json
```

Task를 시작하기 전에 Premigration Assessment를 실행한다. Assessment 결과용 S3 Bucket과 DMS가 쓸 IAM Role이 필요하다.

```bash
aws dms start-replication-task-assessment-run \
  --region "$AWS_REGION" \
  --replication-task-arn "$DMS_TASK_ARN" \
  --service-access-role-arn "$ASSESSMENT_ROLE_ARN" \
  --result-location-bucket "$ASSESSMENT_BUCKET" \
  --result-location-folder booking-migration \
  --assessment-run-name booking-precheck-20260715 \
  --include-only file://assessment-list.json
```

`assessment-list.json`은 현재 DMS Version이 제공하는 Assessment 이름을 `describe-applicable-individual-assessments`로 조회해 만든다. 결과의 Error를 0으로 만들고 Warning은 수용 근거와 대응 방법을 남긴다.

## 10단계: Full Load와 CDC를 시작한다

```bash
aws dms start-replication-task \
  --region "$AWS_REGION" \
  --replication-task-arn "$DMS_TASK_ARN" \
  --start-replication-task-type start-replication
```

동작 순서는 다음과 같다.

1. DMS가 Source 변경 Capture를 준비한다.
2. 각 Table의 기존 Row를 Target으로 Full Load한다.
3. Full Load 중 쌓인 변경을 적용한다.
4. 이후 Redo Log를 계속 읽어 CDC를 유지한다.

Full Load의 Table 순서는 업무 FK 순서가 아니다. FK와 Trigger를 늦게 적용해야 하는 이유다. 대형 Table은 Table Statistics의 `FullLoadRows`, `FullLoadThroughputRowsTarget`과 남은 시간을 보고 병렬성을 조정한다. Source CPU가 오르거나 CDC가 밀리면 무조건 병렬성을 높이지 않는다.

## 11단계: “Task가 Running”이 아니라 정합성을 관측한다

### DMS 상태와 Table Statistics

```bash
aws dms describe-replication-tasks \
  --region "$AWS_REGION" \
  --filters Name=replication-task-arn,Values="$DMS_TASK_ARN" \
  --without-settings

aws dms describe-table-statistics \
  --region "$AWS_REGION" \
  --replication-task-arn "$DMS_TASK_ARN"
```

CloudWatch Alarm은 최소한 다음 지표를 포함한다.

- `CDCLatencySource`: Source에서 변경을 읽어오는 지연
- `CDCLatencyTarget`: 읽은 변경을 Target에 적용하는 지연
- `CDCThroughputRowsTarget`: Target 반영 처리량
- `FreeableMemory`, `SwapUsage`, `CPUUtilization`: Replication Instance 자원
- Task Error와 Table Suspended Event

`CDCLatencySource`가 커지면 Oracle Redo 접근, 긴 Transaction과 Source 부하를 본다. Source Latency는 낮고 `CDCLatencyTarget`만 커지면 Target Lock, Index, Trigger, I/O와 Apply 처리량을 본다.

### Row 수만으로 검증하지 않는다

```sql
-- Source Oracle
SELECT COUNT(*) AS row_count,
       SUM(TOTAL_AMOUNT) AS amount_sum,
       MIN(CREATED_AT) AS first_created_at,
       MAX(UPDATED_AT) AS last_updated_at
FROM BOOKING.RESERVATION
WHERE TENANT_ID = 1001;
```

```sql
-- Target PostgreSQL
SELECT COUNT(*) AS row_count,
       SUM(total_amount) AS amount_sum,
       MIN(created_at) AS first_created_at,
       MAX(updated_at) AS last_updated_at
FROM booking.reservation
WHERE tenant_id = 1001;
```

다음 계층을 함께 검증한다.

1. DMS Row-level Validation의 실패 건수가 0인지 확인한다.
2. Table별 Row 수와 금액 합계를 비교한다.
3. Tenant·날짜 구간별 집계를 비교해 일부 Partition 누락을 찾는다.
4. 예약 상태별 결제 합계와 같은 업무 불변식을 비교한다.
5. 가장 큰 LOB, 다국어 문자열, DST 경계, `NULL`과 빈 문자열 Sample을 비교한다.
6. 신규 예약 생성·변경·취소를 Source에서 실행하고 Target 반영을 확인한다.

Validation Query는 Full Scan으로 운영 Source를 압박할 수 있다. Read Replica 또는 낮은 부하 시간대를 사용하고 PK 범위로 나눠 실행한다.

## 12단계: Cutover 전에 Sequence와 Post-load Object를 준비한다

DMS CDC는 PostgreSQL Sequence의 현재값을 맞춰 주지 않는다. Target에서 Application 쓰기를 열기 전에 Source Sequence보다 큰 값으로 맞춰야 한다.

```sql
-- Oracle에서 마지막 값의 안전한 상한을 확인한다.
SELECT BOOKING.RESERVATION_SEQ.NEXTVAL FROM dual;
```

Oracle에서 확인한 값이 `1842301`이라면 Target에서는 그보다 큰 값으로 설정한다.

```sql
SELECT setval('booking.reservation_seq', 1842301, true);
```

Identity를 사용한다면 실제 Sequence 이름을 조회한다.

```sql
SELECT setval(
    pg_get_serial_sequence('booking.reservation', 'reservation_id'),
    GREATEST((SELECT MAX(reservation_id) FROM booking.reservation), 1842301),
    true
);
```

Secondary Index는 Full Load 이후 CDC 구간에 생성하고, FK는 `NOT VALID`로 추가한 뒤 미리 검증하면 Cutover 시간을 줄일 수 있다.

```sql
CREATE INDEX CONCURRENTLY idx_reservation_tenant_created
    ON booking.reservation (tenant_id, created_at);

ALTER TABLE booking.payment
    ADD CONSTRAINT fk_payment_reservation
    FOREIGN KEY (reservation_id)
    REFERENCES booking.reservation (reservation_id)
    NOT VALID;

ALTER TABLE booking.payment
    VALIDATE CONSTRAINT fk_payment_reservation;
```

업무 Trigger는 DMS가 완전히 멈춘 뒤 활성화한다. CDC 적용 중 Target Trigger가 외부 호출이나 추가 Row 생성을 수행하면 Source에 없던 Side Effect가 생긴다.

## 13단계: 실제 Cutover Runbook

Cutover는 즉흥 명령 모음이 아니라 담당자, 기대 결과, 중단 조건과 되돌리기 명령이 있는 Runbook으로 실행한다.

### T-7일: Rehearsal

- Production Snapshot 복제본으로 Full Load와 CDC를 끝까지 수행한다.
- 예상 Full Load 시간, Peak CDC Lag와 Oracle Redo 증가량을 기록한다.
- Schema 변환 Test, Application 회귀 Test와 성능 Test를 통과한다.
- Cutover와 Rollback을 실제 순서로 한 번 수행한다.
- DDL Freeze를 시작하고 새 Table·Column은 Mapping과 Target DDL에 동시에 반영한다.

### T-30분: 전환 조건 확인

- 모든 Table의 Full Load 상태가 완료다.
- Validation Failed와 Suspended Table이 0이다.
- `CDCLatencySource`, `CDCLatencyTarget`이 합의한 임계값 이하다.
- Target의 Index·FK 검증이 완료됐다.
- Source와 Target Backup 복구 지점이 있다.
- Rollback 결정권자와 관측 Dashboard가 준비됐다.

### T0: Write fence

1. 예약 생성·수정 Command를 Maintenance 상태로 바꾼다.
2. Load Balancer에서 기존 요청이 Drain될 때까지 기다린다.
3. Batch, Consumer, Scheduler와 운영 Script의 Source 쓰기를 중지한다.
4. Oracle의 마지막 확인 Row 또는 업무 Sentinel Transaction을 기록한다.

```sql
UPDATE BOOKING.MIGRATION_SENTINEL
SET LAST_MARKER = 'CUTOVER-20260715-220000',
    UPDATED_AT = SYSTIMESTAMP
WHERE ID = 1;

COMMIT;
```

### T+수십 초: 마지막 CDC 확인

1. 두 CDC Latency가 0 또는 합의한 최소값이 될 때까지 기다린다.
2. Target에서 Sentinel Marker를 확인한다.
3. Table Statistics의 Pending·Error와 Validation을 확인한다.
4. Sequence를 최종값으로 맞춘다.
5. DMS Task를 중지한다.

```bash
aws dms stop-replication-task \
  --region "$AWS_REGION" \
  --replication-task-arn "$DMS_TASK_ARN"
```

### T+1분: Target Writer 개방

1. Target에서 업무 Trigger와 필요한 Post-load Object를 활성화한다.
2. Application Secret 또는 배포 설정을 Aurora Writer Endpoint로 바꾼다.
3. Connection Pool을 재생성하고 새 Connection의 Database Identity를 확인한다.
4. 내부 Synthetic 요청으로 생성·조회·변경·취소를 검증한다.
5. 새 Row가 Oracle이 아니라 Aurora에만 기록되는지 확인한다.
6. 오류율, P95/P99 Latency, Lock, Connection과 Database CPU가 정상이면 write fence를 연다.

Application Instance가 Source와 Target을 동시에 쓰는 시간을 만들지 않는 것이 핵심이다. 설정 변경만 하고 오래된 Pod가 남도록 두지 말고, Readiness와 Connection 검증으로 모든 Writer의 목적지를 증명한다.

## 14단계: 요청 접수까지 멈추지 않으려면 Queue를 쓴다

동기식 Command를 잠시 거절할 수 없다면 Cutover 동안 Command를 SQS FIFO 같은 Durable Queue에 적재하고 접수 ID를 반환할 수 있다.

```text
Normal     API -> Source Database
Cutover    API -> Durable Queue -> 202 Accepted
After      Consumer -> Target Database -> Result Event
```

이 방식에는 Idempotency Key, 순서 보장 범위, 중복 처리, 처리 결과 조회 API와 Queue 적체 Alarm이 필요하다. 기존 동기 API를 단지 Queue로 바꾸면 응답 의미가 달라지므로 Consumer 계약까지 포함한 별도 설계다. 수십 초의 read-only가 허용된다면 단순한 write fence가 더 안전하다.

## 15단계: Rollback은 Target 쓰기 전후가 다르다

### Target 쓰기를 열기 전

아직 Aurora에 신규 업무 Data가 없다. Application을 계속 Oracle에 둔 채 DMS Task와 Target을 고치고 다시 Catch-up하면 된다. 가장 안전한 Rollback 구간이다.

### Target 쓰기를 연 뒤

Aurora에만 존재하는 Transaction이 생겼으므로 접속 주소만 Oracle로 되돌리면 Data를 잃는다. 선택지는 두 가지다.

- **Forward fix**: Aurora를 System of Record로 유지하고 Application 또는 Schema 문제를 수정한다.
- **Reverse replication**: 사전에 PostgreSQL → Oracle DMS CDC 경로를 구축하고 Rehearsal한 경우에만 역방향 Catch-up 후 되돌린다.

Reverse Task를 Cutover 당일 처음 만들면 Rollback Plan이 아니다. Type 역변환, Sequence, Trigger, 충돌 정책과 Supplemental Logging을 미리 검증해야 한다. 대부분의 팀은 Target Writer 개방을 Point of No Return으로 정하고, 그 이후에는 Forward Fix를 기본 정책으로 둔다.

# 추가 실전 사례: 원격 PostgreSQL을 다른 구조의 Aurora PostgreSQL로 이관하기

이번에는 Engine 변환이 없는 다음 사례를 가정한다.

```text
Source : IDC의 Self-managed PostgreSQL
Target : Amazon Aurora PostgreSQL-Compatible
Network: Direct Connect 또는 Site-to-Site VPN
Before : legacy.booking_flat 한 Table에 예약·고객 정보가 함께 존재
After  : customer.customer와 booking.booking으로 정규화
Goal   : 원격지 이전 + Schema 재설계 + Full Load + CDC
```

Engine이 같으므로 AWS SCT는 필수가 아니다. 그러나 Data 구조가 달라지므로 단순한 PostgreSQL Dump·Restore만으로는 목표 Schema를 만들 수 없다. 이 사례에서는 Target DDL을 신규 Version Migration으로 먼저 만들고, DMS는 Data 이동과 CDC에 집중시킨다.

## 같은 Engine Migration에서 먼저 선택할 것

AWS DMS에는 같은 Engine을 위한 Homogeneous Data Migration도 있다. Native Database 도구를 사용해 전체 Database를 같은 구조로 옮기는 경우에는 좋은 선택이다. 하지만 Table 분할·병합처럼 Row 구조가 달라지는 사례에는 변환 단계를 별도로 설계해야 한다.

| 변경 범위 | 권장 방식 |
|---|---|
| 위치만 변경하고 Schema가 동일 | DMS Homogeneous Data Migration 또는 PostgreSQL Native 도구 |
| Schema·Table·Column 이름 변경 | 일반 DMS Replication Task + Table Mapping Transformation |
| Column 추가·삭제과 단순 표현식 | DMS Transformation을 Rehearsal에서 검증 후 사용 |
| 한 Table을 여러 Table로 분리 | Landing Schema + 멱등 Projection |
| 여러 Table을 한 Aggregate로 병합 | Landing Schema 또는 Kinesis CDC + Transactional Consumer |

DMS Transformation은 기본적으로 Table에서 Table, Column에서 Column으로 복제한다. 두 Source Table을 하나의 Target Table에 겹쳐 쓰는 기능은 지원하지 않는다. 한 Row를 여러 Table로 분리하는 업무 규칙도 DMS Mapping JSON에 억지로 넣지 않는다.

## 단순한 구조 변경은 Table Mapping으로 끝낼 수 있다

Source의 `legacy.orders`를 Target의 `booking.reservation`으로 이름만 바꾸고 `memo` Column을 제외하는 정도라면 다음처럼 처리할 수 있다.

```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "100",
      "rule-name": "include-orders",
      "object-locator": {
        "schema-name": "legacy",
        "table-name": "orders"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "transformation",
      "rule-id": "200",
      "rule-name": "rename-schema",
      "rule-target": "schema",
      "object-locator": {
        "schema-name": "legacy"
      },
      "rule-action": "rename",
      "value": "booking"
    },
    {
      "rule-type": "transformation",
      "rule-id": "210",
      "rule-name": "rename-orders",
      "rule-target": "table",
      "object-locator": {
        "schema-name": "legacy",
        "table-name": "orders"
      },
      "rule-action": "rename",
      "value": "reservation"
    },
    {
      "rule-type": "transformation",
      "rule-id": "220",
      "rule-name": "remove-memo",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "legacy",
        "table-name": "orders",
        "column-name": "memo"
      },
      "rule-action": "remove-column"
    }
  ]
}
```

하나의 Object에는 일반적으로 하나의 Transformation Action만 적용할 수 있고 Object 이름은 대소문자를 구분한다. Mapping이 복잡해질수록 실제 Target DDL과 Mapping 결과를 별도 Database에서 먼저 비교한다.

## 복잡한 구조 변경은 Landing Schema를 둔다

Source의 기존 구조는 다음과 같다. 고객 정보가 예약 Row마다 복제되어 있지만, `customer_version`과 `booking_version`이 있어 늦게 도착한 변경으로 최신값을 덮어쓰지 않을 수 있다.

```sql
CREATE SCHEMA IF NOT EXISTS legacy;

CREATE TABLE legacy.booking_flat (
    booking_id       BIGINT PRIMARY KEY,
    tenant_id        BIGINT NOT NULL,
    customer_id      BIGINT NOT NULL,
    customer_name    VARCHAR(100) NOT NULL,
    customer_phone   VARCHAR(30) NOT NULL,
    customer_version BIGINT NOT NULL,
    booking_status   VARCHAR(30) NOT NULL,
    total_amount     NUMERIC(19, 2) NOT NULL,
    booking_version  BIGINT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL
);
```

실제 Source에 안정적인 `customer_id`나 단조 증가 Version이 없다면 Migration 중 임의로 만들어서는 안 된다. 먼저 Expand-Contract로 Column을 추가하고 기존 Row를 Backfill한 뒤, Source Application이 모든 갱신에서 Version을 증가시키도록 배포한다. 동일 고객의 중복 Row가 서로 다른 값을 가지는데 어느 값이 최신인지 판정할 기준도 없다면 자동 정규화 전에 업무 기준으로 Data를 정제해야 한다.

Target에는 세 종류의 Table을 신규 Migration으로 만든다.

1. `migration_raw.booking_flat`: DMS가 Source 구조 그대로 쓰는 Landing Table
2. `customer.customer`: 고객의 최신 상태
3. `booking.booking`: 고객을 참조하는 예약

이미 실행한 Migration을 수정하지 않는다. 다음 DDL을 새 Version Migration으로 추가하고, Main Branch에 존재하던 Migration 뒤에 실행되도록 등록한다.

```sql
CREATE SCHEMA IF NOT EXISTS migration_raw;
CREATE SCHEMA IF NOT EXISTS customer;
CREATE SCHEMA IF NOT EXISTS booking;

CREATE TABLE migration_raw.booking_flat (
    booking_id       BIGINT PRIMARY KEY,
    tenant_id        BIGINT NOT NULL,
    customer_id      BIGINT NOT NULL,
    customer_name    VARCHAR(100) NOT NULL,
    customer_phone   VARCHAR(30) NOT NULL,
    customer_version BIGINT NOT NULL,
    booking_status   VARCHAR(30) NOT NULL,
    total_amount     NUMERIC(19, 2) NOT NULL,
    booking_version  BIGINT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL
);

CREATE TABLE customer.customer (
    tenant_id      BIGINT NOT NULL,
    customer_id    BIGINT NOT NULL,
    name           VARCHAR(100) NOT NULL,
    phone          VARCHAR(30) NOT NULL,
    source_version BIGINT NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, customer_id)
);

CREATE TABLE booking.booking (
    booking_id    BIGINT PRIMARY KEY,
    tenant_id     BIGINT NOT NULL,
    customer_id   BIGINT NOT NULL,
    status        VARCHAR(30) NOT NULL,
    total_amount  NUMERIC(19, 2) NOT NULL,
    source_version BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_booking_customer
        FOREIGN KEY (tenant_id, customer_id)
        REFERENCES customer.customer (tenant_id, customer_id),
    CONSTRAINT ck_booking_status
        CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED'))
);
```

최종 Schema는 구조화된 값을 관계형 Column과 FK로 표현한다. Migration 편의를 이유로 고객이나 예약 전체를 JSONB 한 Column에 저장하지 않는다.

## PostgreSQL Source에서 CDC를 활성화한다

Self-managed PostgreSQL은 Logical Replication을 사용한다. `postgresql.conf`를 다음처럼 설정하고 재시작이 필요한 Parameter를 반영한다.

```properties
wal_level=logical
max_replication_slots=10
max_wal_senders=10
wal_sender_timeout=60000
```

Task 수, 다른 Logical Replication Consumer와 장애 복구 여유를 반영해 Slot과 Sender 수를 정한다. Replication Slot의 Consumer가 멈추면 WAL이 계속 쌓일 수 있으므로 Source Disk 사용량과 `pg_replication_slots`의 LSN 지연에 Alarm을 둔다.

```sql
CREATE ROLE dms_source
    WITH LOGIN REPLICATION PASSWORD 'USE_A_SECRET_VALUE';

GRANT CONNECT ON DATABASE legacy_booking TO dms_source;
GRANT USAGE ON SCHEMA legacy TO dms_source;
GRANT SELECT ON legacy.booking_flat TO dms_source;
```

`pg_hba.conf`에는 DMS Replication Instance의 실제 CIDR만 허용한다.

```text
host  legacy_booking  dms_source  10.40.16.0/24  scram-sha-256
host  replication     dms_source  10.40.16.0/24  scram-sha-256
```

VPN을 통해 Source에 도달하는 경우 DMS Subnet Route Table, IDC 방화벽의 Return Route, DNS, TCP 5432와 MTU를 함께 확인한다. 단순 TCP 연결뿐 아니라 장시간 유지되는 Replication Connection이 Network 장비의 Idle Timeout으로 끊기지 않는지 시험한다.

## DMS는 Source 구조를 Landing Table로만 옮긴다

Target Table을 미리 만들었으므로 `TargetTablePrepMode=DO_NOTHING`을 사용한다. Mapping은 Source Schema 이름만 `migration_raw`로 바꾼다.

```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "100",
      "rule-name": "include-booking-flat",
      "object-locator": {
        "schema-name": "legacy",
        "table-name": "booking_flat"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "transformation",
      "rule-id": "200",
      "rule-name": "route-to-landing-schema",
      "rule-target": "schema",
      "object-locator": {
        "schema-name": "legacy"
      },
      "rule-action": "rename",
      "value": "migration_raw"
    }
  ]
}
```

DMS Validation은 Source와 `migration_raw` 사이의 복제 정확성을 확인한다. `customer.customer`와 `booking.booking`은 구조가 다르므로 별도의 업무 검증이 필요하다.

## Landing Row를 최종 Schema로 투영한다

중간 정도의 변경량이고 Transformation 규칙이 단순한 경우 Aurora Trigger로 Projection을 구성할 수 있다. DMS가 어떤 `session_replication_role`을 사용하더라도 실행되도록 Trigger를 `ENABLE ALWAYS`로 설정한다.

```sql
CREATE OR REPLACE FUNCTION migration_raw.project_booking_flat()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM booking.booking
        WHERE booking_id = OLD.booking_id
          AND source_version <= OLD.booking_version;

        RETURN OLD;
    END IF;

    INSERT INTO customer.customer (
        tenant_id,
        customer_id,
        name,
        phone,
        source_version,
        updated_at
    ) VALUES (
        NEW.tenant_id,
        NEW.customer_id,
        NEW.customer_name,
        NEW.customer_phone,
        NEW.customer_version,
        NEW.updated_at
    )
    ON CONFLICT (tenant_id, customer_id)
    DO UPDATE SET
        name = EXCLUDED.name,
        phone = EXCLUDED.phone,
        source_version = EXCLUDED.source_version,
        updated_at = EXCLUDED.updated_at
    WHERE customer.customer.source_version < EXCLUDED.source_version;

    INSERT INTO booking.booking (
        booking_id,
        tenant_id,
        customer_id,
        status,
        total_amount,
        source_version,
        created_at,
        updated_at
    ) VALUES (
        NEW.booking_id,
        NEW.tenant_id,
        NEW.customer_id,
        NEW.booking_status,
        NEW.total_amount,
        NEW.booking_version,
        NEW.created_at,
        NEW.updated_at
    )
    ON CONFLICT (booking_id)
    DO UPDATE SET
        tenant_id = EXCLUDED.tenant_id,
        customer_id = EXCLUDED.customer_id,
        status = EXCLUDED.status,
        total_amount = EXCLUDED.total_amount,
        source_version = EXCLUDED.source_version,
        updated_at = EXCLUDED.updated_at
    WHERE booking.booking.source_version < EXCLUDED.source_version;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_project_booking_flat
AFTER INSERT OR UPDATE OR DELETE
ON migration_raw.booking_flat
FOR EACH ROW
EXECUTE FUNCTION migration_raw.project_booking_flat();

ALTER TABLE migration_raw.booking_flat
    ENABLE ALWAYS TRIGGER trg_project_booking_flat;

GRANT USAGE ON SCHEMA migration_raw, customer, booking TO dms_target;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON migration_raw.booking_flat,
       customer.customer,
       booking.booking
    TO dms_target;
```

이 Projection은 다음 성질을 가진다.

- 고객 Upsert와 예약 Upsert가 하나의 Aurora Transaction에서 실행된다.
- 같은 Event가 다시 적용돼도 PK와 Version 조건 때문에 결과가 바뀌지 않는다.
- 늦게 도착한 과거 Version이 최신 고객·예약을 덮어쓰지 않는다.
- 예약 삭제는 고객을 자동 삭제하지 않는다. 다른 예약이 참조할 수 있기 때문이다.

Source Application이 `customer_version`과 `booking_version`을 변경할 때마다 단조 증가시키는 것이 전제다. Version 없이 Timestamp만 비교하면 Clock 정밀도와 동시 갱신 때문에 순서를 잘못 판단할 수 있다.

Trigger 방식은 구현이 단순하지만 Full Load의 모든 Row마다 최종 Table Write와 Index 갱신이 추가된다. Rehearsal에서 Source 변경량보다 Projection 처리량이 충분히 큰지 확인한다. Trigger가 CDC Lag의 병목이면 다음 구조로 분리한다.

```text
PostgreSQL WAL
  -> AWS DMS
  -> Kinesis Data Streams
  -> Idempotent Transformer Consumer
  -> Aurora PostgreSQL Transaction
```

Kinesis Target은 `load`, `insert`, `update`, `delete` Operation과 Source Schema·Table 정보를 제공한다. Consumer는 Source PK를 Partition Key로 사용하고, Aurora Transaction 안에서 고객과 예약을 함께 Upsert한다. Kinesis는 중복 제거를 제공하지 않으므로 위와 동일한 Source Version 조건과 처리 Checkpoint가 필요하다. LOB는 1 MiB 제한과 Full LOB Mode 미지원 제약을 먼저 확인한다.

## Projection 결과를 별도로 검증한다

Landing과 최종 Schema는 Row 수가 다를 수 있으므로 단순 COUNT 비교만으로 충분하지 않다.

```sql
-- 모든 Landing 예약이 최종 예약에 최신 Version으로 존재해야 한다.
SELECT raw.booking_id,
       raw.booking_version,
       final.source_version
FROM migration_raw.booking_flat raw
LEFT JOIN booking.booking final
       ON final.booking_id = raw.booking_id
WHERE final.booking_id IS NULL
   OR final.source_version <> raw.booking_version;
```

```sql
-- 고객별로 가장 높은 Source Version이 최종 고객과 같아야 한다.
WITH latest_customer AS (
    SELECT DISTINCT ON (tenant_id, customer_id)
           tenant_id,
           customer_id,
           customer_name,
           customer_phone,
           customer_version
    FROM migration_raw.booking_flat
    ORDER BY tenant_id, customer_id, customer_version DESC
)
SELECT source.tenant_id,
       source.customer_id
FROM latest_customer source
LEFT JOIN customer.customer target
       ON target.tenant_id = source.tenant_id
      AND target.customer_id = source.customer_id
WHERE target.customer_id IS NULL
   OR target.source_version <> source.customer_version
   OR target.name <> source.customer_name
   OR target.phone <> source.customer_phone;
```

```sql
-- FK가 깨진 예약은 없어야 한다.
SELECT booking.booking_id
FROM booking.booking booking
LEFT JOIN customer.customer customer
       ON customer.tenant_id = booking.tenant_id
      AND customer.customer_id = booking.customer_id
WHERE customer.customer_id IS NULL;
```

세 Query가 모두 0 Row인지 확인하고 Tenant·날짜별 예약 금액 합계도 비교한다. Full Scan은 Source가 아닌 Aurora Landing에서 수행할 수 있어 원격 운영 Database 부하를 줄일 수 있다.

## 같은 Engine·다른 Schema Cutover 순서

1. Source DDL을 Freeze한다. PostgreSQL Homogeneous Migration은 PostgreSQL의 지속 복제 중 새 Schema Object를 모두 자동 반영해 주지 않는다.
2. DMS Full Load 완료와 Source → Landing Validation 성공을 확인한다.
3. Landing → Final Projection 불일치가 0인지 확인한다.
4. Source 쓰기를 Fence하고 실행 중인 Transaction과 Batch를 Drain한다.
5. DMS CDC Latency가 0이고 마지막 Sentinel Version이 Final Schema까지 도달했는지 확인한다.
6. DMS를 중지하고 Target Application을 `customer`와 `booking` Schema에 연결한다.
7. 생성·수정·취소 Synthetic Test와 FK·Version 불변식을 확인한 뒤 쓰기를 연다.

Application은 `migration_raw`를 조회하거나 쓰지 않는다. Landing Schema는 DMS와 검증 도구만 접근하도록 권한을 제한한다.

```sql
REVOKE ALL ON SCHEMA migration_raw FROM application_user;
GRANT USAGE ON SCHEMA customer, booking TO application_user;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA customer, booking
    TO application_user;
```

Rollback 경계는 이기종 사례와 같다. Target 쓰기를 열기 전에는 Source를 계속 사용할 수 있다. Target에 새 구조로 쓰기 시작한 뒤에는 `customer`와 `booking`을 기존 `booking_flat`으로 다시 합치는 역방향 Projection이 필요하다. 이를 사전에 구현·시험하지 않았다면 Target Writer 개방 이후의 기본 전략은 Forward Fix다.

안정화 기간이 끝나도 실행했던 Migration을 수정해 Landing Schema를 지우지 않는다. 별도의 신규 Contract Migration으로 Trigger, Function과 `migration_raw` Table을 제거한다.

## 자주 실패하는 지점

### Full Load는 끝났는데 CDC Lag가 줄지 않는다

Source 변경량보다 Target Apply 처리량이 낮은 상태다. 불필요한 Target Index와 Trigger, 작은 Replication Instance, Target Lock, LOB와 긴 Transaction을 확인한다. 병렬성만 높이면 Source와 Target 모두 더 느려질 수 있다.

### UPDATE 또는 DELETE가 누락된다

PK가 없거나 Supplemental Logging이 부족할 수 있다. DMS Log의 key 식별 오류와 Oracle Log Group을 확인한다. 오류 정책을 `IGNORE_RECORD`로 두고 운영하면 Task는 Running인데 Data가 틀린 상태가 된다.

### Full Load 중 FK 오류가 발생한다

DMS는 Table 적재 순서를 FK 관계에 맞춰 보장하지 않는다. FK와 업무 Trigger를 Full Load 이후로 미루거나 DMS Session에 한정해 비활성화한다.

### LOB가 잘리거나 너무 느리다

사전에 CLOB·BLOB 크기 분포를 구한다. Limited LOB Mode의 최대값보다 큰 Row를 중단시키고, 필요한 Table만 Full LOB Mode Task로 분리하는 방법을 고려한다.

### Application은 연결되지만 결과가 다르다

Oracle 빈 문자열, `DATE`, Time Zone, `NUMBER`, 정렬 규칙과 대소문자 식별자를 의심한다. 연결 성공과 SQL 문법 성공은 업무 의미가 같다는 증거가 아니다.

### DDL 변경 이후 CDC가 깨진다

이기종 CDC에서 모든 DDL 전파를 기대하지 않는다. Migration 기간에는 DDL Freeze를 적용하고, 불가피한 변경은 Oracle DDL, SCT 변환 SQL, Target DDL과 DMS Mapping을 한 변경 묶음으로 관리한다.

## 운영 완료 조건과 정리

다음 조건을 모두 만족한 뒤 Migration을 완료 처리한다.

- 합의한 관측 기간 동안 Target 오류율과 Latency가 정상이다.
- Data Validation과 업무 불변식 비교가 통과했다.
- 모든 Writer와 Batch가 Aurora를 사용한다.
- Oracle로 향하는 Connection이 0이다.
- Backup, PITR, Alarm, Dashboard와 운영 권한이 Target 기준으로 준비됐다.
- Rollback 종료가 승인됐다.

즉시 DMS Resource와 Oracle을 삭제하지 않는다. 감사와 장애 분석에 필요한 Log·Assessment 결과를 보존하고 합의한 안정화 기간 이후 다음 순서로 정리한다.

```text
DMS Task 중지 확인
 -> Endpoint와 Replication Instance 삭제
 -> Secret 접근 Role 폐기
 -> Source Database Read-only 전환 및 연결 0 확인
 -> 최종 Snapshot·보존 정책 확인
 -> 승인 후 Source 폐기
```

## 핵심 정리

AWS SCT, DMS Full Load와 CDC를 결합하면 이기종 Database Migration의 긴 Data 복사 시간을 서비스 운영 시간 밖으로 밀어낼 수 있다. 같은 Engine을 원격지로 옮기면서 Schema가 달라지는 경우에도 DMS가 Landing Schema까지의 전달을 맡고 멱등 Projection이 최종 관계형 구조를 만들도록 책임을 나눌 수 있다. 그러나 도구가 Cutover의 정합성을 대신 결정해 주지는 않는다.

성공의 핵심은 Schema와 Data를 서로 다른 단계로 다루고, Oracle Redo와 Key를 CDC 가능하게 준비하며, 오류를 무시하지 않는 Task 설정을 사용하는 것이다. 마지막에는 write fence, Sentinel, Sequence 보정, Target 검증과 Rollback 경계를 순서대로 실행해야 한다. “Task가 Running”이 아니라 RPO 0과 업무 불변식을 증명했을 때 비로소 무중단 전환에 가까워진다.

# Reference

- [AWS SCT Database Migration Assessment Report](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)
- [AWS SCT로 Database Schema 변환](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Converting.Convert.html)
- [Oracle을 PostgreSQL로 변환하는 AWS SCT 절차](https://docs.aws.amazon.com/dms/latest/sbs/chap-oracle-postgresql.migration-process.database-schema-conversion.html)
- [Oracle을 AWS DMS Source로 사용하기](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.Oracle.html)
- [PostgreSQL을 AWS DMS Target으로 사용하기](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.PostgreSQL.html)
- [AWS DMS CDC Task](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html)
- [AWS DMS Task 설정](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.html)
- [AWS DMS Error Handling 설정](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.ErrorHandling.html)
- [AWS DMS Data Validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html)
- [AWS DMS Premigration Assessment](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.PremigrationAssessmentRuns.html)
- [AWS DMS Secrets Manager Endpoint 인증](https://docs.aws.amazon.com/dms/latest/userguide/security_iam_secretsmanager.html)
- [AWS DMS Monitoring](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Monitoring.html)
- [PostgreSQL을 AWS DMS Source로 사용하기](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html)
- [AWS DMS Transformation Rule과 제약](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Transformations.html)
- [AWS DMS Homogeneous Data Migration](https://docs.aws.amazon.com/dms/latest/userguide/data-migrations.html)
- [Kinesis Data Streams를 AWS DMS Target으로 사용하기](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.Kinesis.html)
