---
id: Schema Multi-Tenancy 경계 설계
started: 2026-05-23
tags:
  - ✅DONE
  - Architecture
  - Multi-Tenancy
  - PostgreSQL
group:
  - "[[Java Spring Architecture]]"
---
# Schema Multi-Tenancy 경계 설계

## 1. 개요 (Overview)
**Schema-per-tenant**는 하나의 PostgreSQL Instance·Database 안에서 Tenant마다 별도 Schema를 사용하는 방식입니다. Database 운영 비용을 공유하면서 Table과 Index의 Namespace를 분리할 수 있지만, Application이 올바른 Tenant Context를 선택하는 것이 보안 경계가 됩니다.

---

## 2. 구조

```text
Database
  ├─ public / shared schema
  ├─ tenant_a
  │   ├─ booking
  │   └─ driving
  ├─ tenant_b
  │   ├─ booking
  │   └─ driving
  └─ metrics_batch
```

공용 Identity·Tenant Registry와 Tenant 업무 데이터를 어느 Schema가 소유하는지 명확히 해야 합니다.

---

## 3. Tenant Context 흐름

```text
JWT / Request
  -> Tenant ID 검증
  -> Tenant Context
  -> Connection Schema 선택
  -> Query
  -> Context 정리
```

Client가 전달한 Schema 이름을 그대로 사용하지 않습니다. 인증된 Tenant ID를 Server의 Registry에서 검증된 Schema Identifier로 변환합니다.

---

## 4. Connection Pool 주의사항
Connection은 Pool로 반환된 뒤 다른 요청에서 재사용됩니다. `search_path`나 Schema를 변경했다면 반드시 원래 상태로 복구해야 합니다. Transaction 중 Tenant Context가 바뀌지 않도록 하고, 비동기 실행 시 ThreadLocal Context가 자동 전달된다고 가정하지 않습니다.

Virtual Thread에서도 Tenant Context의 생성·정리 Scope를 명시적으로 관리해야 합니다.

---

## 5. Migration
모든 Tenant Schema에 Liquibase ChangeSet을 적용할 때 다음을 고려합니다.

- 신규 Tenant와 기존 Tenant의 동일 Version 보장
- 여러 Instance의 동시 Migration 방지
- Tenant별 실패 격리와 재시도
- Migration 진행 중 Traffic 차단 또는 호환성 유지
- 전체 Tenant Migration 시간과 병렬성 제한

Expand-and-Contract 방식으로 구·신 Application Version이 동시에 동작 가능한 Schema 변경을 설계합니다.

---

## 6. 실무 사례 적용 관점
이 사례의 핵심 업무 애플리케이션은 Hibernate Schema Multi-tenancy를 사용하고, Metrics는 Tenant별 jOOQ·JPA Executor로 업무 Schema와 Metrics Schema를 선택합니다. Startup Tenant Migration은 제한된 병렬성으로 각 Schema의 Liquibase ChangeLog를 적용합니다.

Metrics Batch처럼 모든 Tenant를 순회하는 작업은 한 Tenant 실패가 전체 Job을 멈출지, 실패 Tenant만 기록하고 계속할지 정책을 명확히 해야 합니다.

---

## 7. 격리 검증
- 다른 Tenant ID로 동일 Resource에 접근하는 Security Test
- Connection 재사용 후 Schema 누출 Test
- 비동기·Scheduler에서 Tenant Context 누락 Test
- Migration Version 불일치 Alert
- Query Log의 Tenant 식별자와 민감정보 정책
- Backup·Restore의 Tenant 단위 복구 가능성

---

## 8. Shared Schema와 Tenant Schema
모든 데이터를 Tenant Schema에 넣으면 Tenant Registry나 시스템 관리자 계정처럼 전역 데이터 접근이 어려워집니다. 반대로 공용 Schema가 많아지면 Tenant 격리가 약해집니다.

```text
Public/Shared
  -> tenant registry, global configuration

Tenant Schema
  -> member, booking, driving, payment
```

Table마다 소유 범위와 접근 주체를 문서화합니다.

## 9. Schema 선택 방식
- Hibernate MultiTenantConnectionProvider
- Transaction 시작 시 `SET LOCAL search_path`
- jOOQ Render Mapping 또는 DSLContext
- SQL에 검증된 Schema Identifier 명시

`SET LOCAL`은 Transaction 종료 시 복구되어 Pool 누출 위험을 줄입니다. Auto-commit Query와 Transaction 없는 실행 경로를 별도로 확인합니다.

## 10. Tenant Context 보안
Tenant ID는 요청 Header만 믿지 않고 JWT Claim과 사용자의 소속 권한을 검증합니다. Super Admin의 Cross-tenant 기능은 일반 요청 흐름과 분리하고 감사 Log를 남깁니다.

Background Job에는 HTTP Context가 없으므로 작업 Payload에 Tenant ID를 명시하고 Registry에서 Schema를 다시 해석합니다.

## 11. Cache 격리
Redis Key와 Local Cache Key에 Tenant를 포함합니다.

```text
fms:{environment}:{tenant}:{resource}:{id}
```

Tenant가 빠진 Cache Key는 DB가 격리되어 있어도 다른 Tenant 데이터를 반환하는 치명적인 문제를 만듭니다.

## 12. Query와 Connection 누출
Connection Pool에서 다음 순서의 Test를 수행합니다.

1. Tenant A Query
2. Connection 반환
3. 같은 Pool에서 Tenant B Query
4. A 데이터가 보이지 않음 확인

Exception·Timeout 경로에서도 Schema Reset이 수행되는지 확인합니다.

## 13. Migration Orchestration

```text
Tenant Registry Page
  -> Version 확인
  -> 제한된 병렬 실행
  -> Tenant별 Lock
  -> Liquibase Update
  -> 성공·실패 기록
```

한 Tenant의 실패가 전체 Startup을 막을지 Traffic을 제한한 채 나머지를 진행할지 정책을 정합니다. Migration 중인 Tenant만 Readiness에서 제외하는 방법도 검토할 수 있습니다.

## 14. Backup과 복구
Schema-per-tenant는 물리적으로 같은 Database를 공유하므로 Instance 장애 격리는 제공하지 않습니다. PITR은 전체 Database 단위이며 특정 Tenant 복구에는 별도 Export·Restore 절차가 필요합니다.

삭제 Tenant의 Retention, Legal Hold와 Backup에서의 데이터 제거 정책도 고려합니다.

## 15. Noisy Neighbor
한 Tenant의 무거운 Query가 공용 DB CPU·I/O·Connection을 사용합니다. Tenant별 Rate Limit, Query Timeout, Batch Quota와 Metric Label을 사용합니다.

## 16. 대안 비교

| 방식 | 격리 | 운영 비용 | 확장 단위 |
|---|---|---|---|
| Row-level tenant_id | 낮음 | 낮음 | DB 전체 |
| Schema-per-tenant | 중간 | 중간 | DB 전체·일부 Schema 운영 |
| Database-per-tenant | 높음 | 높음 | Tenant별 |

규제·규모가 큰 Tenant만 별도 Database로 이동하는 Hybrid도 가능합니다.

---

## 17. 실무 사례 적용 진단과 개선 과제

이 사례는 Tenant Schema Changelog와 Tenant Context를 사용하지만 Context 전달, Connection 반환 전 Schema 초기화, Async/Scheduler 경계의 Tenant 누락을 지속 검증해야 합니다. 특히 Virtual Thread·비동기 실행이 늘면 ThreadLocal 기반 Context 전파 가정이 약해집니다.

해결하려면 모든 Inbound 경계에서 인증된 Tenant를 생성하고 Repository가 이를 명시적으로 요구하게 합니다. Connection Pool 반환 시 기본 Schema 복원, Cache Key의 Tenant Prefix, Scheduler의 Tenant 반복 실행을 통합 Test로 고정하고 Migration 상태를 Tenant별 Ledger로 관리합니다.

완료 기준은 임의 Tenant 교차 접근 Test가 모두 실패하고, Thread 재사용·Async 실행·예외 종료 후에도 Schema 누수가 없으며, Tenant별 Migration 실패를 격리·재개할 수 있는 상태입니다.

---

# Reference
- [[멀티 테넌시]]
- [[Liquibase 설치 및 사용법]]
- [[jOOQ 타입 안전 SQL]]
