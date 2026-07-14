---
id: PgBouncer Connection Pooling
started: 2026-05-16
tags:
  - ✅DONE
  - PostgreSQL
  - PgBouncer
group:
  - "[[DBMS]]"
---
# PgBouncer Connection Pooling

## 1. 개요

PostgreSQL은 Connection마다 Backend Process를 사용합니다. Pod와 Virtual Thread를 늘리면 Application 동시성보다 DB Connection이 먼저 한계에 도달할 수 있습니다. PgBouncer는 많은 Client Connection을 적은 Server Connection에 Multiplexing합니다.

---

## 2. 이중 Pool 구조

```text
Application Hikari Pool
  -> PgBouncer Client Connection
  -> PgBouncer Server Pool
  -> PostgreSQL Backend
```

두 Pool을 모두 크게 두면 대기가 사라지는 것이 아니라 위치만 바뀝니다. 전체 Connection Budget과 Queue Timeout을 함께 설계합니다.

---

## 3. Pool Mode

| Mode | Server Connection 반환 시점 | 특징 |
|---|---|---|
| Session | Client 종료 | 호환성 높고 Multiplexing 낮음 |
| Transaction | Transaction 종료 | 일반 Web API에 효율적 |
| Statement | Statement 종료 | Multi-statement Transaction 불가 |

Transaction Mode에서는 Session 상태가 다음 Transaction에 유지된다고 가정하면 안 됩니다.

---

## 4. Transaction Mode 제약

- Session-level `SET`
- Temporary Table
- Session Advisory Lock
- 일부 Prepared Statement 방식
- `LISTEN/NOTIFY`
- Session에 묶인 Cursor

Driver와 PgBouncer Version에 따라 Prepared Statement 지원이 달라질 수 있으므로 실제 조합을 Test합니다.

---

## 5. Sizing

```text
DB Server Connection Budget
  = PgBouncer Pool 합
  + Migration·Admin·Monitoring 여유
```

DB CPU Core보다 훨씬 많은 Active Query는 처리량보다 경합을 늘립니다. Pool Size는 부하 Test에서 Saturation과 P95를 보고 정합니다.

---

## 6. Queue와 Timeout

PgBouncer 대기 시간이 Application HTTP Timeout보다 길면 이미 취소된 요청이 DB에서 뒤늦게 실행될 수 있습니다. Connection 획득, Statement, HTTP Timeout을 End-to-End Budget으로 정렬합니다.

무한 Queue보다 빠른 Load Shedding이 전체 시스템을 보호할 수 있습니다.

---

## 7. Failover

RDS Failover 뒤 DNS가 변경되면 PgBouncer가 기존 Server Connection을 폐기하고 재연결해야 합니다. DNS TTL, Health Check, Connection Lifetime과 재시도 폭주를 Test합니다.

PgBouncer 자체도 Replica, Service와 PDB가 없으면 새로운 단일 실패 지점입니다.

---

## 8. 관측 지표

- Client Active·Waiting
- Server Active·Idle
- Transaction·Query Rate
- 평균 대기 시간
- Pool별 Max Wait
- Connection Error와 DNS Failover
- PostgreSQL Backend 수와 CPU

Hikari Pending과 PgBouncer Waiting을 같은 Dashboard에서 봅니다.

---

## 9. 사례 적용 판단

Pod 수 × Hikari Pool이 RDS Budget을 위협하거나 Connection Churn이 크면 PgBouncer 후보입니다. 현재 직접 Pool만으로 충분하다면 새 운영 계층을 추가할 필요는 없습니다.

도입 전 Transaction Mode 제약, Tenant Schema 전환, Migration Tool과 Batch를 별도 Endpoint로 분리할지 검토합니다.

---

## 10. 완료 기준

- [ ] Pool Mode별 Session 의미를 설명할 수 있습니다.
- [ ] Hikari·PgBouncer·PostgreSQL Budget이 수치화되어 있습니다.
- [ ] Prepared Statement와 Tenant Schema가 통합 Test를 통과합니다.
- [ ] Failover와 PgBouncer 재시작 시 SLO를 검증했습니다.
- [ ] Queue가 한도를 넘으면 빠르게 실패합니다.

# Reference

- [PgBouncer Documentation](https://www.pgbouncer.org/usage.html)
- [[RDS와 ElastiCache 데이터 계층]]
- [[Backpressure와 Load Shedding]]
