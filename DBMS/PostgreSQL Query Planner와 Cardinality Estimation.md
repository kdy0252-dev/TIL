---
id: PostgreSQL Query Planner와 Cardinality Estimation
started: 2026-05-18
tags:
  - ✅DONE
  - PostgreSQL
  - Query-Planner
group:
  - "[[DBMS]]"
---
# PostgreSQL Query Planner와 Cardinality Estimation

## 1. 개요

Planner는 가능한 실행 계획의 비용을 추정해 하나를 선택합니다. 느린 Query는 SQL 문법보다 Row 수 추정이 틀려 잘못된 Join·Scan을 선택한 결과인 경우가 많습니다.

```text
SQL -> Parse -> Rewrite -> Plan 후보 생성 -> Cost 비교 -> Execute
```

---

## 2. Cardinality

Cardinality Estimation은 각 단계에서 몇 Row가 나올지 예상하는 일입니다. 예상 10 Row가 실제 100만 Row라면 Nested Loop와 작은 Memory 계획이 선택될 수 있습니다.

`EXPLAIN ANALYZE`의 estimated rows와 actual rows 비율을 먼저 봅니다.

---

## 3. Statistics

`ANALYZE`는 다음 통계를 수집합니다.

- Null 비율
- Distinct 추정
- Most Common Values와 빈도
- Histogram
- Column Correlation

통계가 오래됐거나 Sampling이 부족하면 분포를 잘못 이해합니다. 무조건 Statistics Target을 높이면 Analyze와 Catalog 비용이 증가합니다.

---

## 4. 상관관계

Planner는 기본적으로 조건 Column을 독립적으로 추정할 수 있습니다. `country`와 `city`, `tenant_id`와 업무 상태처럼 강하게 연관된 Column은 오차가 큽니다.

Extended Statistics의 Dependencies, N-distinct, MCV를 사용해 다중 Column 분포를 알려줄 수 있습니다.

---

## 5. Cost Model

`seq_page_cost`, `random_page_cost`, CPU Cost, Parallel Cost는 절대 시간이 아니라 상대 비용입니다. SSD라는 이유만으로 값을 복사하지 말고 실제 Cache와 Storage를 Benchmark합니다.

`effective_cache_size`는 Memory를 할당하지 않고 Planner에게 사용 가능한 Cache 규모를 알려줍니다.

---

## 6. Join 선택

- Nested Loop: 외부 Row가 적고 내부 Index가 있을 때
- Hash Join: 큰 Equality Join, Hash가 Memory에 맞을 때
- Merge Join: 정렬된 입력과 Range 조건에 유리

Join Algorithm을 강제로 끄는 것은 진단 실험일 뿐 영구 해결책이 아닙니다. 통계·Index·Query 구조를 고칩니다.

---

## 7. EXPLAIN 읽기

```sql
EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS, FORMAT JSON)
SELECT ...;
```

- 실제 실행하므로 쓰기 Query는 Transaction에서 주의합니다.
- Node별 estimated/actual rows와 loops를 봅니다.
- Shared Hit/Read와 Temp Read/Write를 구분합니다.
- 한 Node의 시간이 자식 시간을 포함할 수 있음을 유의합니다.

---

## 8. Parameter와 Generic Plan

Prepared Statement는 Custom Plan과 Generic Plan을 선택할 수 있습니다. Tenant별 데이터 편차가 크면 평균적인 Generic Plan이 특정 대형 Tenant에서 매우 느릴 수 있습니다.

같은 SQL의 Parameter별 Plan과 `plan_cache_mode` 실험으로 확인하되 전역 강제 전에 원인을 검증합니다.

---

## 9. 사례 적용

Multi-tenant Query는 `tenant_id`와 상태·날짜 조건의 분포가 Tenant마다 다릅니다. RSQL 같은 동적 조건은 조합 수가 많아 하나의 Index로 해결되지 않습니다.

- 대표 소형·대형 Tenant 데이터로 Test합니다.
- P95 조건 조합의 Plan을 Snapshot합니다.
- Pagination Count Query를 별도로 측정합니다.
- 통계 갱신 뒤 Plan 변경을 감시합니다.

---

## 10. 완료 기준

- [ ] Estimated와 Actual Row 오차를 먼저 확인합니다.
- [ ] 단일·다중 Column Statistics의 차이를 설명합니다.
- [ ] Buffer, Temp I/O와 WAL을 Plan에서 해석합니다.
- [ ] Parameter별 Plan 편차를 검증합니다.
- [ ] 주요 Query Plan과 P95 회귀를 자동 비교합니다.

# Reference

- [PostgreSQL Planner Statistics](https://www.postgresql.org/docs/current/planner-stats.html)
- [Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [[RSQL과 QueryDSL 동적 검색]]
