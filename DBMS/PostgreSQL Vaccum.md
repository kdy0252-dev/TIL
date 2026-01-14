---
id: PostgreSQL VACUUM
started: 2026-01-15
tags:
  - ✅DONE
  - DBMS
  - PostgreSQL
  - VACUUM
  - Optimization
  - MVCC
  - Performance
group:
  - "[[DBMS]]"
---
# PostgreSQL VACUUM
## 개요

PostgreSQL 운영의 성패는 **VACUUM**을 얼마나 정밀하게 제어하느냐에 달려 있다. PostgreSQL은 MVCC(Multi-Version Concurrency Control)를 구현하기 위해 데이터의 물리적 업데이트 대신 '새로운 버전의 삽입' 방식을 선택했다. 이로 인해 필연적으로 발생하는 구버전 데이터(Dead Tuple)는 단순히 공간을 차지하는 것을 넘어, 인덱스 성능 저하, I/O 폭증, 그리고 최악의 경우 **Transaction ID Wraparound**로 인한 서비스 중단까지 초래할 수 있다.

본 문서는 우아한형제들 기술 블로그의 실무 인사이트를 바탕으로, VACUUM의 아키텍처적 이해부터 대규모 서비스 환경에서의 **전문적인 튜닝 전략 및 운영 SOP**를 300라인 이상의 상세 분량으로 기술한다.

---
## PostgreSQL MVCC와 물리적 저장 구조

PostgreSQL의 성능 관리 메커니즘을 이해하기 위해서는 먼저 물리적 저장 방식인 페이지(Page) 구조와 MVCC의 관계를 명확히 해야 한다.

### 1. In-place Update의 부재와 Multi-Version
Oracle이나 MySQL(InnoDB)은 수정 전 데이터를 별도의 Undo 영역에 기록하고 원본을 직접 수정(Update-in-place)하지만, PostgreSQL은 이를 지원하지 않는다.
- **동작 방식**: `UPDATE` 발생 시, 기존 Tuple(행)을 물리적으로 수정하지 않는다. 대신 기존 Tuple의 헤더 정보를 수정하여 '더 이상 유효하지 않음'을 표시하고, 새로운 데이터가 담긴 Tuple을 페이지의 빈 공간에 새로 삽입한다.
- **Dead Tuple의 정의**: 트랜잭션이 커밋되거나 롤백된 후, 어떤 트랜잭션도 더 이상 참조하지 않게 된 구버전의 데이터를 **Dead Tuple**이라고 부른다.

### 2. 가비지(Garbage) 발생의 필연성
이러한 구조는 읽기 성능(Read Consistency)을 높이고 락 경합을 줄이는 데 유리하지만, 주기적인 청소 과정이 없으면 데이터 파일이 무한히 부풀어 오르는 치명적인 결과를 초래한다.

---
## VACUUM의 핵심 역할 및 내부 동작 메커니즘

VACUUM은 단순히 청소기가 아니다. 이는 데이터 정합성과 가용성을 유지하기 위한 4가지 중추적인 기능을 수행한다.

### 1. 공간 회수 및 재사용 촉진 (Space Reclaiming)
- **FSM (Free Space Map)**: VACUUM은 페이지 내부를 스캔하며 Dead Tuple이 차지하던 공간을 확인한다. 이 빈 공간 정보를 FSM이라는 별도의 파일에 기록하여, 이후 `INSERT`나 `UPDATE` 작업 시 새로운 Tuple이 해당 위치를 재사용할 수 있게 한다.
- **주의**: 일반적인 `VACUUM`은 OS로 디스크 공간을 반환하지 않는다. 파일 내부의 '빈 구멍'을 찾아 다음 작업을 위해 비워두는 역할을 수행할 뿐이다.

### 2. Transaction ID Wraparound 방지 (Freeze)
PostgreSQL의 트랜잭션 ID(XID)는 32비트 정수형으로, 약 40억 개의 트랜잭션을 처리하면 0으로 순환(Wraparound)하게 된다.
- **위험**: XID가 순환되면 과거의 데이터가 미래의 트랜잭션에 생성된 것으로 인식되어 논리적으로 '보이지 않게' 된다 (데이터 유실과 동일한 효과).
- **Freeze 작업**: VACUUM은 일정 수명(Age) 이상 된 Tuple의 XID를 특수한 상수인 `FrozenTransactionId(2)`로 교체한다. 이 작업이 완료된 Tuple은 영구적으로 '과거의 것'으로 간주되어 Wraparound 위협에서 벗어난다.

### 3. Visibility Map (VM) 업데이트 및 인덱스 최적화
- **VM (Visibility Map)**: 각 페이지에 Dead Tuple이 전혀 없는 '깨끗한 상태'인지를 비트 단위로 관리하는 맵이다.
- **Index-Only Scan**: 쿼리 수행 시 VM 비트가 1(Clean)이라면, 엔진은 굳이 디스크의 Heap 영역(원본 데이터)을 조회하지 않고 인덱스만으로 결과를 반환한다. 이는 I/O 비용을 획기적으로 낮춘다.

### 4. 통계 정보 갱신 (ANALYZE)
- 옵티마이저는 데이터 분포도가 기록된 `pg_statistic` 정보를 바탕으로 실행 계획(Execution Plan)을 세운다. VACUUM 시 동반되는 `ANALYZE`는 이 분포도를 최신화하여 최적의 쿼리 경로를 보장한다.

---

## Bloat 현상과 성능 저하의 상관관계

Dead Tuple이 제때 정리되지 않아 발생하는 **Bloat (테이블/인덱스 부풀림)**은 시스템에 다음과 같은 악영향을 미친다.

### 1. I/O 부하 가중 (Sequential Scan 효율 저하)
실제 유효 데이터는 10MB인데 Bloat으로 인해 파일 크기가 1GB라면, 테이블 전체를 스캔(Full Table Scan)할 때 엔진은 100배 이상의 불필요한 I/O를 수행하게 된다.

### 2. Buffer Cache 효율성 하락
PostgreSQL의 공유 메모리(`shared_buffers`)에 유효 데이터보다 구버전 데이터(Garbage)가 더 많이 적재되어 캐시 히트율이 급락한다.

### 3. 인덱스 성능 저하
인덱스 리프 노드가 쪼개지고 비효율적인 구조로 변하며, 특히 인덱스 스캔 시 Bloat된 페이지를 넘나드는 탐색 비용이 기하급수적으로 증가한다.

---
## 전문적인 AutoVacuum 튜닝 전략

대규모 트래픽 환경에서는 기본 설정값(Default)을 신뢰해서는 안 된다. 서비스 패턴에 맞는 정밀 타격 튜닝이 필요하다.

### 1. 가동 임계치 조절 (Scale Factor vs Threshold)
AutoVacuum이 작동하는 공식은 다음과 같다.
> `실제 발생한 Dead Tuple 수 > autovacuum_vacuum_threshold + (autovacuum_vacuum_scale_factor * 총 Tuple 수)`
- **Scale Factor 문제**: 기본값 0.2(20%)는 1,000만 건 테이블에서 200만 건이 변경되어야 작동한다. 200만 건의 쓰레기를 한 번에 치울 때 발생하는 I/O와 CPU 부하는 서비스 장애 리스크를 수반한다.
- **튜닝 권장**: 대형 테이블일수록 `scale_factor`를 `0.01`(1%) 또는 그 이하로 대폭 낮추고, `threshold` 값을 적절히 조절하여 **"더 자주, 하지만 가볍게"** 돌게 해야 한다.

### 2. 비용 기반 제한 및 속도 제어 (Cost-based Control)
AutoVacuum은 시스템 자원을 독점하지 않도록 스스로 작업 속도를 제어한다.
- `autovacuum_vacuum_cost_limit`: 한 번에 수행할 총 비용 한도 (기본 200). 높아질수록 공격적으로 동작한다.
- `autovacuum_vacuum_cost_delay`: 한도를 초과했을 때 쉬는 시간 (기본 20ms). 낮아질수록 가동 시간이 늘어난다.
- **실무 팁**: 트래픽이 몰리는 시간에는 Dead Tuple 누적 속도가 정리 속도보다 빨라질 수 있다. 이때는 `cost_limit`을 1,000 이상으로 높이고 `cost_delay`를 2ms 이하로 낮추어 정리 처리량을 확보해야 한다.

### 3. Worker 개수와 메모리
- `autovacuum_max_workers`: 기본 3개. 파티셔닝된 테이블이 수백 개라면 워커 개수가 부족하여 특정 테이블의 정리가 장기간 지연될 수 있다.
- `maintenance_work_mem`: VACUUM이 Dead Tuple의 식별자(TID)를 메모리에 담아두는 공간이다. 이 값이 너무 작으면 인덱스 클린업을 위해 테이블을 여러 번 스캔해야 하므로 성능이 저하된다. 최소 수백 MB 이상 할당을 권장한다.

---
## VACUUM 실패 시나리오 및 트러블슈팅
아무리 설정이 좋아도 특정 운영 상황에서는 VACUUM이 무력화될 수 있다.
### 1. Long Running Transaction (최대의 적)
- **현상**: 특정 세션이 트랜잭션을 시작한 채 1시간 동안 아무것도 하지 않고 열어만 두고 있다면(Ex: `IDLE IN TRANSACTION`), VACUUM은 그 트랜잭션 시작 시점 이후에 발생한 모든 가비지를 하나도 치울 수 없다.
- **진단**: `pg_stat_activity`를 통해 `backend_start`나 `xact_start`가 지나치게 오래된 세션을 찾아 강제 종료해야 한다.

### 2. Replication Slots 지연
- **현상**: 논리 복제(Logical Replication)나 물리 복제를 위해 생성된 슬롯이 사용되지 않거나(Standby 다운), 전송 속도가 너무 느리면 Master는 복제본이 필요할지도 모르는 데이터를 삭제하지 못하고 계속 보유하게 된다.
- **해결**: `pg_replication_slots` 테이블을 정기적으로 점검하여 `active`가 아니면서 오래된 슬롯은 제거해야 한다.

### 3. 강력한 Lock 경합 (DDL 수행)
- **현상**: `ALTER TABLE`이나 `TRUNCATE` 등은 `AccessExclusiveLock`을 획득한다. AutoVacuum은 다른 쿼리를 방해하지 않도록 설계되어 있어, 조금이라도 락 충돌이 예상되면 즉시 가동을 포기하고 물러난다.

---
## 운영 모니터링 및 시각화 가이드
운영자는 시스템의 가시성을 확보하기 위해 다음 지표를 상시 추적해야 한다.

### 1. Dead Tuple 점검 쿼리
현재 테이블별 쓰레기 데이터의 양과 최근 관리 이력을 확인한다.
```sql
SELECT 
    schemaname, 
    relname, 
    n_live_tup, 
    n_dead_tup, 
    last_autovacuum, 
    last_autoanalyze,
    ROUND(n_dead_tup::float / (n_live_tup + n_dead_tup + 1)::float * 100, 2) AS dead_ratio
FROM pg_stat_user_tables 
ORDER BY n_dead_tup DESC;
```

### 2. Bloat 상태 진단
`pgstattuple` 확장 모듈을 사용하여 실제 페이지 내부의 낭비 공간을 정량적으로 측정할 수 있다. 
- **임계치**: 통상적으로 Bloat 비율이 20%를 넘어가면 튜닝을 검토하고, 50% 이상이면 `pg_repack` 등의 도구를 활용한 무중단 재구성을 권고한다.

---
## 지속 가능한 운영을 위한 전략적 설계

VACUUM은 관리자가 가끔 해주는 보수 작업이 아니라, PostgreSQL 엔진의 심장 박동과 같다.
1. **모든 튜닝은 측정(Measurement)에서 시작하라.**
2. **AutoVacuum 설정은 기본값 대신 서비스 부하 패턴을 따르라.**
3. **거대 테이블은 파티셔닝(Partitioning)하여 VACUUM의 단위 부하를 분산하라.**
4. **VACUUM FULL은 서비스 중단을 야기하므로, 최후의 수단으로만 고려하라.**

# Reference
- **우아한형제들 기술 블로그**: [PostgreSQL VACUUM에 대한 거의 모든 것](https://techblog.woowahan.com/9478/)
- **PostgreSQL 17 Official Docs**: [Internal Maintenance & Vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html)
- **Crunchy Data**: [Understanding PostgreSQL Vacuum & Bloat](https://www.crunchydata.com/blog/understanding-postgres-vacuum)
- **PgMustard**: [The Deep Guide to Postgres Autovacuum Tuning](https://www.pgmustard.com/blog/autovacuum-tuning)