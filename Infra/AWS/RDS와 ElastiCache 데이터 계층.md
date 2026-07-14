---
id: RDS와 ElastiCache 데이터 계층
started: 2026-06-26
tags:
  - ✅DONE
  - AWS
  - RDS
  - ElastiCache
group:
  - "[[Infra AWS]]"
---
# RDS와 ElastiCache 데이터 계층

## 1. 개요 (Overview)

사례 배포 구조는 관계형 영속 데이터에 Amazon RDS PostgreSQL을, 짧은 지연의 Cache·분산 상태에 Amazon ElastiCache Redis를 사용합니다. 두 서비스는 모두 관리형이지만 데이터 의미와 장애 시 복구 방식은 다릅니다.

```text
Application
  -> RDS PostgreSQL : System of Record, Transaction
  -> ElastiCache    : Cache, Lock, 짧은 수명의 공유 상태
```

Redis의 값을 잃어도 RDS 또는 외부 원본에서 재구성할 수 있는지 여부가 가장 중요한 경계입니다.

---

## 2. Network와 접근 제어

RDS와 ElastiCache는 Private Subnet Group에 배치하고 Public Access를 열지 않습니다. Application Security Group에서 데이터 계층 Security Group의 해당 Port만 허용합니다.

운영자 접근은 Client VPN이나 SSM Bastion을 거치고 개인 IP를 DB Security Group에 직접 추가하지 않습니다. 접근 가능 경로와 DB Account 권한은 별도 계층이므로 둘 다 최소화합니다.

TLS 연결과 Server Certificate 검증을 활성화합니다. 암호화만 하고 Server Identity를 확인하지 않으면 중간자 공격을 막지 못합니다.

---

## 3. RDS Multi-AZ와 Read Replica

Multi-AZ는 Primary 장애 시 Standby로 Failover해 가용성을 높입니다. 일반적으로 Standby는 읽기 확장 용도가 아닙니다. Read Replica는 읽기 부하 분산에 사용하지만 비동기 복제로 인한 지연이 있습니다.

```text
Multi-AZ      -> 가용성, 관리형 Standby
Read Replica  -> 읽기 확장, 비동기 복제 지연
```

Read-after-write 일관성이 필요한 Query를 Replica로 보내면 방금 저장한 데이터가 보이지 않을 수 있습니다. 업무별 허용 가능한 Staleness를 정의합니다.

Failover 후 Endpoint DNS가 새 Instance를 가리키므로 Application Connection Pool이 오래된 Connection을 버리고 재연결할 수 있어야 합니다.

---

## 4. Connection Budget

Kubernetes Replica와 Worker 동시성이 증가하면 DB Connection이 빠르게 늘어납니다.

```text
최대 연결 = Pod Replica × Pod당 Pool Size
          + Migration·Batch·운영 도구 연결
```

이 값은 RDS `max_connections`보다 충분히 낮아야 합니다. Rolling Update와 Blue-Green 중에는 이전·새 Pod가 동시에 살아 있어 평상시보다 Connection이 많습니다.

Pool 크기를 크게 하면 항상 처리량이 늘지는 않습니다. DB CPU Core와 Lock 경합을 넘는 동시 Query는 Latency만 증가시킵니다. Connection Timeout, Query Timeout, Idle Lifetime과 Leak Detection을 함께 설정합니다.

---

## 5. Backup과 복구

RDS Automated Backup과 Point-in-Time Recovery는 운영 실수와 장애 복구의 핵심입니다. Snapshot이 존재하는 것과 실제 복구 가능한 것은 다릅니다.

정기 복구 훈련에서 새 Instance Restore 시간, 데이터 손실 범위, DNS·Secret·Application 전환, Migration Version 호환성, 복구 후 무결성을 측정합니다.

삭제 방지와 Final Snapshot 정책을 환경 중요도에 맞게 설정합니다. Cross-region DR이 필요하다면 Snapshot Copy, Replica, KMS Key와 Secret 복구까지 포함합니다.

---

## 6. Schema Migration

Blue-Green과 Rolling Update에서는 이전 Version과 새 Version이 동시에 같은 Schema를 사용합니다.

1. 새 Column·Table을 호환 가능하게 추가합니다.
2. 이전·새 Application이 모두 동작하도록 배포합니다.
3. Backfill을 작은 Batch로 수행합니다.
4. 새 경로가 안정된 뒤 이전 Column 사용을 제거합니다.
5. 관찰 기간 후 파괴적 변경을 수행합니다.

Column Rename이나 Type 변경을 한 번에 수행하면 Rollback이 어렵습니다. Expand-Migrate-Contract를 적용합니다. 긴 DDL은 Traffic을 막을 수 있으므로 예상 Lock, Table Size, Timeout을 사전 검증합니다.

---

## 7. Parameter와 관측성

RDS는 CPU, Freeable Memory, Free Storage, Connection, Read·Write Latency, IOPS, Replica Lag를 감시합니다. Performance Insights와 Slow Query Log로 내부 병목을 분석합니다.

높은 CPU만으로 Instance 확대를 결정하지 않습니다. Index 누락, N+1 Query, Lock Wait, 긴 Transaction, Connection Storm, Autovacuum 지연, 실제 Traffic 증가를 구분합니다.

Parameter Group 변경 중 Reboot가 필요한 항목과 즉시 적용되는 항목을 구분합니다. Terraform Plan뿐 아니라 적용 시점과 Restart 영향을 확인합니다.

---

## 8. ElastiCache Replication Group

Redis Replication Group은 Primary와 Replica를 구성하고 Automatic Failover를 제공할 수 있습니다. Failover 시 짧은 연결 끊김과 DNS 변경이 발생할 수 있습니다.

Client는 제한된 Exponential Backoff로 재연결하고 무한 재시도로 Thread를 점유하지 않습니다. Cluster Mode에서는 Key Space가 Shard에 분산되며 Multi-key Operation은 같은 Hash Slot 제약을 받을 수 있습니다.

단일 Shard에서 시작하더라도 Memory와 Throughput이 언제 Sharding 기준에 도달하는지 Metric을 정합니다.

---

## 9. Cache 패턴

Cache-aside는 Cache Miss 때 DB를 조회해 저장합니다. 가장 단순하지만 Hot Key 만료 순간에 동시 DB 조회가 몰리는 Cache Stampede가 발생할 수 있습니다. TTL Jitter, In-flight Deduplication, 사전 갱신으로 완화합니다.

DB Commit 이후 Cache를 Invalidate해야 합니다. Commit 전에 삭제하면 다른 요청이 이전 DB 값을 다시 Cache할 수 있습니다. Event 기반 Invalidate는 전달 지연과 중복을 고려합니다.

Cache 데이터는 Stale할 수 있다는 전제에서 사용하고, 금액·권한처럼 강한 일관성이 필요한 판단의 유일한 근거로 두지 않습니다.

---

## 10. TTL, Eviction과 Memory

TTL은 데이터 신선도와 Memory 회수 정책입니다. 데이터 변화 빈도와 Staleness 허용 범위에 맞춥니다.

Memory가 한도에 도달하면 `maxmemory-policy`에 따라 Key가 Evict되거나 Write가 실패합니다. Cache, Lock, Queue, Idempotency Key를 같은 Instance에 두면 Eviction의 의미가 서로 다릅니다.

```text
Cache Key        -> Eviction 허용 가능
분산 Lock Key    -> 임의 Eviction 위험
Idempotency Key  -> 조기 삭제 시 중복 처리 위험
Queue            -> 유실 허용 여부 별도 결정
```

Big Key와 Hot Key는 Latency와 Failover 시간을 악화시킵니다. Key Size, Command Latency, Eviction, Hit Ratio, Memory Fragmentation을 감시합니다.

---

## 11. Redis Lock의 한계

Redis `SET NX PX`는 간단한 Lock에 사용할 수 있지만 Process Pause나 Network Partition 뒤 만료된 Lock 소유자가 계속 작업할 수 있습니다. 중요한 쓰기에는 Fencing Token 또는 DB의 조건부 갱신이 필요합니다.

Lock 해제 시 값이 자신의 Token과 일치할 때만 삭제하는 Atomic Script를 사용합니다. 단순 `DEL`은 이미 다른 소유자가 획득한 Lock을 지울 수 있습니다.

DB Unique Constraint, Optimistic Lock, Idempotency Key로 문제를 더 단순하게 해결할 수 있는지 먼저 검토합니다.

---

## 12. Secret과 Credential Rotation

DB Password와 Redis Auth Token을 Terraform State나 Plaintext Values에 노출하지 않습니다. Secret Manager 등 외부 보관소에서 Runtime에 전달하고 Log와 Plan Output에 Masking합니다.

Rotation은 새 Credential 발급, Application 전환, 기존 Credential 폐기 순으로 수행합니다. Connection Pool은 기존 Connection을 유지할 수 있으므로 Rotation 후 재연결 시점을 계획합니다.

Application Role은 Schema Owner와 분리하고 필요한 Table·Operation만 허용합니다. Migration Role은 배포 시점에만 사용합니다.

---

## 13. 장애 시나리오와 검증

| 시나리오 | 기대 동작 |
|---|---|
| RDS Failover | Pool이 오래된 연결을 버리고 제한 시간 안에 재연결 |
| DB Connection 고갈 | 빠른 실패와 Backpressure, 무한 대기 방지 |
| Redis Failover | 짧은 오류 후 재연결, 업무 데이터 불일치 없음 |
| Cache 전체 삭제 | DB에서 재구성, Stampede 제어 |
| Migration 실패 | 호환 가능한 이전 Application 유지 |
| Secret Rotation | 새 연결부터 새 Credential 사용, 무중단 전환 |

- [ ] 데이터 서비스가 Private Subnet과 최소 Security Group을 사용하는가
- [ ] Blue-Green 시점의 최대 DB Connection을 계산했는가
- [ ] Backup Restore를 실제로 수행하고 RTO·RPO를 측정했는가
- [ ] Schema 변경이 이전·새 Version과 호환되는가
- [ ] Redis Key가 유실돼도 재구성 가능한지 분류했는가
- [ ] Cache Stampede와 Hot Key를 감시하는가
- [ ] Failover·Credential Rotation을 정기 검증하는가

---

## 14. 배포 사례 적용 진단과 개선 과제

운영 Data Stack은 삭제 방지와 암호화를 사용하지만 조사 시점에 RDS `multi_az = false`로 설정되어 있습니다. 이는 Instance·AZ 장애 시 수동 복구와 더 긴 중단을 감수하는 명시적 가용성 공백입니다. Application Replica 증가와 Blue-Green 중 Connection Budget도 별도 검증이 필요합니다.

P1로 Prod Multi-AZ 전환 전 Storage·Parameter·Backup과 Failover 영향 Test를 수행합니다. Pod 수 × Pool Size를 배포 중 최대치로 계산하고 RDS Connection Budget을 고정합니다. ElastiCache는 데이터 유형별 유실 허용성을 분류하고 Failover·Eviction Test를 추가합니다.

완료 기준은 RDS 강제 Failover와 Redis Primary 교체에서 애플리케이션이 제한 시간 안에 재연결하고, PITR Restore로 RTO/RPO를 증명하며, Schema Migration이 이전·새 Image 동시 실행과 호환되는 상태입니다.

---

# Reference

- [Amazon RDS for PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/Welcome.html)
- [Amazon RDS High Availability](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html)
- [Amazon ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html)
- [[In-flight Deduplication]]
- [[멱등성과 Reconciliation]]
