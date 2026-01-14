---
id: 대규모 트래픽 대응을 위한 PostgreSQL 최적화 전략
started: 2026-01-14
tags:
  - ✅DONE
  - DBMS
  - PostgreSQL
  - Optimization
  - Performance
group:
  - "[[DBMS]]"
---
# 대규모 트래픽 대응을 위한 PostgreSQL 최적화 전략
## 0. 개요 (Executive Summary)

본 문서는 동시 접속자가 급증하고 트랜잭션 밀도가 높은 대규모 서비스 환경에서 **PostgreSQL DBMS의 성능 임계치를 확장하기 위한 최적화 가이드**이다. PostgreSQL은 높은 신뢰성과 표준 준수성을 보장하지만, 기본 대중성을 위한 보수적인 설정은 고부하 환경에서 자원 활용을 저해하고 쿼리 타임아웃을 유발하는 원인이 된다.

본 자산은 **[메모리 레이아웃 최적화 - 쓰기 지연 완화 - 동시성 제어 - 가용성 유지]** 의 관점에서 시스템의 병목을 진단하고 해결하기 위한 정밀 튜닝 방안을 수립하는 것을 목적으로 한다.

---
## 1. 메모리 아키텍처 최적화 (Memory Layout Tuning)

PostgreSQL의 메모리 할당 구조는 공유 메모리 영역(Shared Memory)과 세션별 작업 영역(Local Memory)으로 구분된다. 대규모 트래픽 환경에서는 이 두 영역의 균형 잡힌 배분이 성능의 핵심이다.

### 1.1 Shared Buffers (`shared_buffers`)
- **기술적 정의**: 디스크 I/O를 최소화하기 위해 데이터 페이지를 캐싱하는 가장 중요한 메모리 영역이다.
- **최적화 가이드**: 
  - 일반적으로 시스템 전체 물리 메모리의 **25% ~ 40%**를 권장한다.
  - 리눅스 커널의 HugePages 설정과 병행할 때 TLB 미스를 줄여 극적인 성능 향상을 기대할 수 있다.
- **장애 징후**: 
  - `EXPLAIN ANALYZE` 상의 `Shared Read` 수치 증가 (디스크 읽기 발생).
  - 버퍼 히트율(Buffer Hit Ratio)이 99% 미만으로 하락.

### 1.2 작업 메모리 (`work_mem`)
- **기술적 정의**: `ORDER BY`, `DISTINCT`, `JOIN` 등을 수행할 때 각 프로세스(세션)에 할당되는 로컬 메모리이다.
- **최적화 전략**:
  - 이 설정은 **연결된 세션 수만큼 할당**될 수 있으므로, `max_connections * work_mem`이 전체 메모리 한도를 초과하지 않도록 정밀 계산이 필요하다.
  - 복잡한 분석 쿼리가 많은 경우 `8MB ~ 16MB` 이상으로 시작하되, 특정 트랜잭션에서만 `SET work_mem = '64MB'`와 같이 세션 단위 상향을 권장한다.
- **증상**: 
  - `log_temp_files` 로그 증가 (메모리 부족으로 디스크 임시 파일 사용 시 발생).
  - 정렬 작업이 포함된 쿼리의 성능 급락.

### 1.3 유지보수 작업 메모리 (`maintenance_work_mem`)
- **대상**: `VACUUM`, `CREATE INDEX`, `ALTER TABLE` 등 관리 작업에 할당된다.
- **권장값**: 대용량 인덱스 생성 시 성능 향상을 위해 `1GB ~ 2GB` 이상으로 상향한다.

---
## 2. WAL 및 쓰기 성능 최적화 (Write-Ahead Logging)

PostgreSQL은 모든 변경 사항을 데이터 파일에 직접 쓰기 전에 먼저 WAL(Write-Ahead Log)에 기록한다. 대량의 트래픽이 유입될 때 WAL I/O는 전체 시스템 성능의 병목이 된다.

### 2.1 체크포인트 전략 (`checkpoint_timeout` & `max_wal_size`)
- **배경**: 체크포인트는 메모리의 변경된 데이터(Dirty Pages)를 디스크로 플러시하는 과정이다. 자주 발생하면 I/O 부하가 심해지고, 너무 늦게 발생하면 복구 시간이 길어진다.
- **최적화 설정**:
  - `checkpoint_timeout = 15min ~ 30min`: 잦은 플러시를 억제하여 I/O 급증(Spike)을 완화한다.
  - `max_wal_size = 2GB ~ 10GB`: 로그 공간을 넉넉히 확보하여 공간 부족으로 인한 강제 체크포인트를 방지한다.
  - `checkpoint_completion_target = 0.9`: I/O 작업을 체크포인트 주기 동안 완만하게 분산시킨다.

### 2.2 동기식 커밋 제어 (`synchronous_commit`)
- **전략**: 데이터 손실이 치명적이지 않은 로그성 데이터나 일부 빠른 처리가 필요한 트랜잭션의 경우 수동 조정을 고려한다.
- **설정**: `off` 설정 시 트랜잭션 처리 속도가 비약적으로 향상되나, 전원 장애 시 약 3 * `wal_writer_delay` 만큼의 데이터 유실 가능성이 있다.

---
## 3. 동시성 및 커넥션 관리 (Connection & Pooling)

PostgreSQL은 세션마다 별도의 프로세스를 생성(Fork)하므로, 너무 많은 직접 연결은 메모리 부족과 컨텍스트 스위칭 오버헤드를 유발한다.

### 3.1 `max_connections` 설정의 한계
- **현상**: 천 단위 이상의 직접 연결은 성능에 역효과를 준다.
- **대응**: `max_connections`는 애플리케이션 요구 수준에 따라 `500 ~ 1000` 정도로 유지하되, 그 이상의 트래픽은 반드시 **PgBouncer**와 같은 외부 커넥션 풀러를 통해 제어해야 한다.

### 3.2 PgBouncer 도입 (Standard Architecture)
- **Pooling Mode**: `Transaction mode` 권장.
- **이점**: 수천 개의 클라이언트 세션을 소수의 실제 DB 프로세스로 집중시켜 CPU 사이클을 보존하고 커넥션 오버헤드를 제거한다.

---
## 4. 고부하 환경의 진공(Vacuum) 전략

PostgreSQL의 MVCC(Multi-Version Concurrency Control) 특성상 UPDATE/DELETE 작업 시 데드 튜플(Dead Tuple)이 누적되며, 이를 제때 정리하지 않으면 테이블 블로트(Bloat)가 발생하여 전체 성능이 저하된다.

### 4.1 Autovacuum 정밀 튜닝
- **`autovacuum_max_workers = 3 ~ 10`**: 시스템의 코어 수에 비례하여 동시 작업 수를 늘린다.
- **`autovacuum_vacuum_scale_factor = 0.05`**: 테이블의 5%만 변경되어도 즉시 청소를 시작하여 블로트 발생을 억제한다.
- **`autovacuum_vacuum_cost_limit = 1000 ~ 2000`**: 백그라운드 작업이 소모할 수 있는 I/O 한도를 상향하여 청소 속도를 높인다.

---
## 5. 실행 계획 및 쿼리 최적화 (Optimizer Tuning)

대량 데이터 조회 시 옵티마이저가 잘못된 통계를 기반으로 판단하지 않도록 유도해야 한다.

- **`random_page_cost = 1.1`**: SSD/NVMe 스토리지 사용 시 Sequential Read와 Random Read의 비용 차이가 거의 없음을 옵티마이저에게 알린다. (기본값 4.0은 HDD 기준)
- **`effective_cache_size`**: 커널의 페이지 캐시와 Postgres의 버퍼를 합쳐 사용 가능한 전체 메모리 양을 기술한다 (보통 물리 메모리의 75%). 옵티마이저가 Index Scan을 더 적극적으로 사용하도록 유도한다.

---
## 6. 모니터링 및 자산 가치 유지를 위한 지표 (Metrics)

| 카테고리 | 핵심 지표 (SQL / Metric) | 모니터링 포인트 |
| :--- | :--- | :--- |
| **Buffer** | `blks_hit / (blks_hit + blks_read)` | 버퍼 히트율 99% 유지 여부 |
| **Connection** | `pg_stat_activity` (waiting status) | Lock 경합 및 대기 세션 수 |
| **Bloat** | `pgstattuple` (Dead tuple ratio) | 20% 초과 시 수동 VACUUM 고려 |
| **I/O** | `pg_stat_bgwriter` (checkpoints) | `max_wal_size`에 의한 체크포인트 빈도 |

---
## 7. 추신
DBMS 최적화는 단발성 작업이 아닌, 데이터 증가분과 쿼리 패턴의 변화에 따른 지속적인 추적 관리가 필요하다. 본 자산에 포함된 가이드를 기준으로 운영 환경에 맞는 **Baseline**을 수립하고, 매 분기 성능 감사를 통해 최적의 임계치를 갱신해야 한다.

---
## Reference
- **Official Docs**: [PostgreSQL 17 Documentation - Server Configuration](https://www.postgresql.org/docs/current/runtime-config.html)
- **Performance Blog**: [PGConfig.org - PostgreSQL Configuration Tool](https://pgconfig.org)
- **Deep Insight**: [TimescaleDB Blog - PostgreSQL Performance Tuning](https://www.timescale.com/blog/postgresql-performance-tuning-guide-shared-buffers-work-mem/)
- **Practical Guide**: [2ndQuadrant - Tuning PostgreSQL for High Performance](https://www.2ndquadrant.com/en/blog/)
