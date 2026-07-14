---
id: GlitchTip 오류 추적과 Valkey
started: 2026-06-12
tags:
  - ✅DONE
  - Observability
  - GlitchTip
  - Valkey
group:
  - "[[Infra]]"
---
# GlitchTip 오류 추적과 Valkey

## 1. 개요 (Overview)

GlitchTip은 Sentry SDK Protocol을 활용해 Application Error, Stack Trace, Release, 사용자 영향 범위를 수집하는 오류 추적 플랫폼입니다. 이 배포 사례에서는 EKS에 GlitchTip Web·Worker를 배치하고 외부 PostgreSQL과 Chart 내부 Valkey를 연결하며 ALB를 통해 접근합니다.

```text
Application SDK
  -> GlitchTip Web
  -> PostgreSQL : Issue, Event Metadata, Project
  -> Valkey     : Queue, Cache
  -> Worker     : 비동기 처리와 알림
```

Metric이 “오류율이 증가했다”를 알려준다면 오류 추적은 “어떤 Release의 어느 코드 경로에서 누구에게 발생했는가”를 좁히는 데 사용합니다.

---

## 2. Event 수집 흐름

Application SDK는 예외를 Capture하고 DSN Endpoint로 Event를 전송합니다. Event에는 Exception Type, Stack Frame, Release, Environment, Tag와 선택적 사용자 Context가 포함됩니다.

```text
Exception
  -> SDK Event 생성
  -> Local Queue / 비동기 전송
  -> Ingestion 인증과 크기 검사
  -> Issue Grouping
  -> 저장 및 알림
```

오류 추적 전송 실패가 업무 요청 실패로 이어져서는 안 됩니다. SDK는 짧은 Timeout과 제한된 Buffer를 사용하고, 애플리케이션 종료 시 Flush 시간을 과도하게 늘리지 않습니다.

---

## 3. Issue Grouping

GlitchTip은 Exception과 Stack Frame의 Fingerprint를 사용해 유사 Event를 하나의 Issue로 묶습니다. Grouping 품질이 나쁘면 같은 원인이 여러 Issue로 흩어지거나 서로 다른 원인이 하나로 합쳐집니다.

다음 상황에서는 Custom Fingerprint를 검토합니다.

- 동적 Message 값 때문에 같은 오류가 분리되는 경우
- 외부 API Error를 Provider와 Error Code별로 나눠야 하는 경우
- 동일 Exception Type이 업무 의미상 서로 다른 경우

Fingerprint에 Request ID나 User ID를 넣으면 모든 Event가 별도 Issue가 되므로 피합니다.

---

## 4. Release와 Environment

Release 정보가 있어야 오류가 어느 배포에서 시작됐는지 알 수 있습니다. Image Tag 또는 Git Commit SHA를 SDK Release와 일치시키고 Dev·QA·Prod Environment를 분리합니다.

```text
Git Commit SHA
  = Container Image Label
  = Helm values image tag 또는 annotation
  = GlitchTip release
```

배포 Marker와 Issue의 First Seen 시점을 연결하면 회귀 여부를 빠르게 판단할 수 있습니다. Blue-Green 전환에서는 Preview와 Active가 같은 Environment를 쓰더라도 Version Tag로 구분되어야 합니다.

Source Map이나 Debug Symbol을 사용하는 Frontend·Native Application은 Release 이름과 Artifact Upload 이름이 정확히 일치해야 읽을 수 있는 Stack Trace를 얻습니다.

---

## 5. 민감 정보와 개인정보

오류 Event에는 Header, Query Parameter, Form Data, User 정보가 들어갈 수 있습니다. 수집 전 다음을 제한합니다.

- Authorization, Cookie, Token, Password 제거
- 주민번호, 전화번호, 이메일 등 개인정보 Masking
- Request Body 전체 수집 금지 또는 Allowlist 적용
- SQL Parameter와 외부 API Credential 제거
- User Context는 내부 식별자 Hash 등 최소 정보만 사용

Server-side Scrubbing이 있더라도 SDK `beforeSend` 단계에서 먼저 제거하는 것이 안전합니다. 한번 저장된 민감 정보는 Backup과 Replication에도 남을 수 있습니다.

---

## 6. Sampling과 Event Storm

같은 오류가 초당 수천 번 발생하면 Ingestion, Queue, Database, 알림이 함께 포화될 수 있습니다.

제어 수단은 다음과 같습니다.

- SDK Sample Rate
- 반복 오류의 Rate Limit
- Event 크기 제한
- Alert Cooldown과 Grouping
- Project별 Quota

무작위 Sampling만 적용하면 희귀한 치명 오류를 놓칠 수 있습니다. 오류 유형, HTTP Status, Environment에 따라 우선순위를 다르게 두고 Drop 수를 Metric으로 남깁니다.

---

## 7. PostgreSQL 데이터 계층

PostgreSQL에는 Issue, Event Metadata, 사용자·Project 설정이 저장됩니다. 운영 시 다음을 고려합니다.

- Connection Pool과 Worker 동시성의 합
- Event 보존 기간과 Table 증가율
- Migration 실행 순서와 Rollback 가능성
- Multi-AZ, Backup, Point-in-Time Recovery
- Vacuum과 Index Bloat

Pod Replica만 늘리고 DB Connection Budget을 조정하지 않으면 RDS Connection이 먼저 고갈됩니다. Web과 Worker의 Pool 한도를 합산해 최대 연결 수보다 낮게 유지합니다.

대량 Event 정리는 Transaction과 I/O 부하를 만들므로 업무 시간 외 Batch와 작은 Chunk를 사용합니다.

---

## 8. Valkey의 역할

Valkey는 Redis Protocol과 호환되는 In-memory Data Store입니다. GlitchTip에서는 비동기 작업 Queue와 Cache에 사용됩니다.

Queue 데이터가 유실되면 아직 처리되지 않은 알림이나 Event 작업이 사라질 수 있습니다. Chart 내부 단일 Valkey는 간단하지만 Node 장애와 Upgrade 시 내구성이 제한됩니다.

환경 중요도에 따라 다음을 결정합니다.

- Persistence 사용 여부
- Replica와 Failover
- Pod Anti-affinity와 PDB
- Memory Limit과 Eviction Policy
- 관리형 ElastiCache 전환 기준

Cache와 Queue를 같은 Instance에 둘 때 Eviction으로 Queue Key가 제거되지 않는지 확인합니다. `maxmemory-policy`는 데이터 의미에 맞게 선택해야 합니다.

---

## 9. Worker와 Backpressure

Worker 처리율이 유입률보다 낮으면 Queue가 증가합니다.

```text
Queue 증가율 = Event 유입률 - Worker 처리율
```

Worker Replica를 늘리기 전에 PostgreSQL과 Valkey가 추가 동시성을 감당할 수 있는지 확인합니다. CPU가 아니라 외부 I/O가 병목이면 Replica 증가가 DB 경합만 키울 수 있습니다.

감시할 항목은 Queue Length, Oldest Job Age, 처리율, 실패·재시도 수, Worker Memory, DB Connection입니다. Queue Length가 낮아도 가장 오래된 작업의 Age가 크면 특정 작업이 정체된 상태일 수 있습니다.

---

## 10. Kubernetes와 ALB 배치

Web과 Worker는 책임이 다르므로 Deployment와 Resource를 분리합니다. Web은 Ingress Traffic과 Latency, Worker는 Queue Throughput을 기준으로 Scale합니다.

ALB Health Check는 단순 Process 생존과 DB·Valkey 의존성 상태를 구분합니다. 일시적인 DB 지연으로 모든 Web Pod가 동시에 Unready가 되면 오히려 복구 경로가 사라질 수 있으므로 Readiness 기준을 신중히 정합니다.

외부 공개 Endpoint라면 WAF, TLS, Request Size, Rate Limit과 Admin 접근 통제를 적용합니다. Ingestion Endpoint와 UI/Admin Endpoint의 노출 정책을 분리할 수 있는지도 검토합니다.

---

## 11. Alert 설계

오류마다 즉시 알림을 보내면 Alert Fatigue가 생깁니다. 다음 조건을 조합합니다.

- Prod에서 새로 발생한 Issue
- 최근 Release 이후 급증한 Issue
- 영향 User 또는 Event 수가 임계치를 넘은 Issue
- 결제·인증 등 핵심 경로 Tag
- 해결 상태였던 Issue의 Regression

GlitchTip 알림 자체가 실패할 수 있으므로 Ingestion과 Worker 상태는 Prometheus·Alertmanager 같은 독립 관측 경로에서도 감시합니다.

---

## 12. 장애 복구와 검증

복구 우선순위는 데이터 수집보다 업무 시스템 보호입니다. Event Storm이 DB를 압박하면 Ingestion Rate를 낮추고 Sample을 강화합니다.

정기적으로 다음을 검증합니다.

1. Test Exception이 올바른 Project·Environment·Release로 들어오는가
2. 민감 정보가 Event에 포함되지 않는가
3. Worker 중단 후 Queue가 쌓이고 재시작 후 처리되는가
4. PostgreSQL Backup에서 Project와 Issue를 복구할 수 있는가
5. Valkey 재시작의 허용 가능한 유실 범위를 알고 있는가
6. 새 Release가 배포 Marker와 연결되는가

### 운영 점검표

- [ ] DSN과 Admin Credential이 Secret으로 관리되는가
- [ ] Release·Environment 이름이 배포 정보와 일치하는가
- [ ] 보존 기간과 Event Quota가 정의되어 있는가
- [ ] Queue Age와 Worker 실패를 감시하는가
- [ ] DB Connection Budget과 Migration 절차가 있는가
- [ ] PII Scrubbing을 Test Event로 검증하는가

---

## 13. 배포 사례 적용 진단과 개선 과제

GlitchTip은 외부 RDS와 Chart 내부 Valkey를 사용합니다. In-cluster Valkey의 내구성과 Failover 수준이 운영 오류 Event·알림 Queue의 중요도에 비해 낮을 수 있고, Event Retention·Quota·PII Scrubbing의 코드화가 필요합니다.

먼저 Valkey 유실 시 영향과 복구 가능성을 분류해 Prod에서 관리형 ElastiCache 또는 복제·Persistence 전환 기준을 정합니다. SDK `beforeSend`와 Server Scrubbing을 Test하고 Release·Environment를 Image Digest와 연결합니다. Queue Age·Worker Failure·DB Connection을 경보합니다.

완료 기준은 Valkey/Worker 재시작 후 허용 범위 내에서 Queue가 회복되고, Test Event에 PII가 없으며, 새 Release 회귀와 GlitchTip 자체 수집 장애를 독립 Alert로 식별하는 상태입니다.

---

# Reference

- [GlitchTip Documentation](https://glitchtip.com/documentation/)
- [Valkey Documentation](https://valkey.io/topics/documentation/)
- [Sentry SDK Usage](https://docs.sentry.io/platforms/)
- [[Spring Boot Actuator와 Micrometer Observation]]
- [[Kubernetes Workload 신뢰성]]
