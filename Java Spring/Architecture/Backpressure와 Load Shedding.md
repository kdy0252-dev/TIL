---
id: Backpressure와 Load Shedding
started: 2026-05-22
tags:
  - ✅DONE
  - Architecture
  - Resilience
  - Performance
group:
  - "[[Java Spring Architecture]]"
---
# Backpressure와 Load Shedding

## 1. 개요 (Overview)
시스템이 처리 능력보다 많은 요청을 계속 수락하면 Queue와 대기 시간이 증가하고 결국 Timeout·Retry가 전체 장애를 만듭니다. **Backpressure**는 생산자에게 속도를 낮추라는 신호를 보내고, **Load Shedding**은 처리할 수 없는 요청을 조기에 거부하여 이미 진행 중인 작업과 하위 시스템을 보호합니다.

---

## 2. 보호 계층

```text
Client
  -> Rate Limit
  -> Gateway Timeout
  -> Readiness Traffic Gate
  -> Bulkhead / Concurrency Limit
  -> Connection Pool
  -> Database
```

한 계층만으로 모든 과부하를 해결하지 않습니다. 가장 비싼 자원에 도달하기 전에 여러 경계에서 부하를 제한합니다.

---

## 3. Backpressure 신호
- HTTP `429 Too Many Requests`: 호출 주체별 제한
- HTTP `503 Service Unavailable`: 현재 처리 용량 부족
- `Retry-After`: 재시도 가능 시점
- Queue Remaining Capacity
- Kubernetes Readiness 실패: 신규 트래픽 차단

오류를 늦게 반환하는 것보다 빠르게 거부하면 Client와 Server 자원을 모두 절약할 수 있습니다.

---

## 4. Resilience 패턴 결합

| 패턴 | 보호 대상 |
|---|---|
| Rate Limiter | 호출량 |
| Bulkhead | 동시 실행 수·Thread·Semaphore |
| Circuit Breaker | 실패 중인 하위 서비스 호출 |
| Timeout | 자원 점유 시간 |
| In-flight Deduplication | 동일 Key의 중복 실행 |
| Cache·Stale Read | 원본 조회 부하 |

Retry는 부하를 늘리는 패턴이므로 Backoff, Jitter와 전체 Retry Budget이 필요합니다.

---

## 5. 사례의 DB Backpressure
이 사례는 DB 관련 오류와 처리 용량을 감지하는 Filter·Health Indicator를 두고, 트래픽 수용이 어려운 상태를 Readiness에 반영합니다.

```text
DB Saturation 감지
  -> Traffic Capacity 상태 변경
  -> Actuator Readiness DOWN
  -> Kubernetes Endpoint에서 Pod 제외
  -> 진행 중 요청 처리와 회복
```

Liveness를 실패시키지 않기 때문에 Pod가 동시에 재시작되는 악순환을 피할 수 있습니다.

---

## 6. 용량 제한
- DB Pool 크기보다 훨씬 많은 동시 Query를 허용하지 않습니다.
- Batch와 Online Traffic의 Pool·Semaphore를 분리합니다.
- Hot Key는 In-flight Deduplication과 Cache로 보호합니다.
- 외부 Map API는 Circuit Breaker와 Bulkhead를 적용합니다.
- Queue가 가득 찼을 때 무제한 대기 대신 명시적으로 거부합니다.

---

## 7. 관측 지표
- Connection Pool Active·Pending·Timeout
- Executor Active Thread·Queue Size·Rejected Count
- HTTP 429·503과 Readiness 변경
- Circuit Breaker Open 비율
- Bulkhead Rejection
- 요청 지연과 Retry 횟수

---

## 8. Queueing 관점
처리량 한계를 넘으면 Queue 길이와 대기 시간이 비선형적으로 증가합니다. 평균 사용률을 100%에 가깝게 운영하면 작은 Traffic 변동에도 Tail Latency가 급증합니다.

```text
Arrival Rate λ >= Service Rate μ
  -> Queue 지속 증가
  -> Timeout
  -> Retry
  -> 더 높은 Arrival Rate
```

의도적인 여유 Capacity와 명확한 Queue 상한이 필요합니다.

## 9. Admission Control
요청을 받은 뒤 비싼 작업을 시작하기 전에 처리 가능성을 판단합니다.

- Global 동시성 제한
- Tenant별 Quota
- Endpoint별 비용 Weight
- Queue Capacity
- DB Pool 가용 Connection

단순 요청 수가 아니라 예상 비용이 다른 작업을 분리합니다.

## 10. Load Shedding 우선순위
모든 요청을 동일하게 거부하지 않습니다.

1. Health·운영 제어 Traffic 보호
2. 핵심 쓰기·운행 Traffic 보호
3. 재시도 가능한 조회 제한
4. 무거운 Export·통계·Batch 중단

Priority Queue는 낮은 우선순위가 영구적으로 굶지 않도록 정책이 필요합니다.

## 11. Retry Budget
전체 요청 중 Retry가 차지할 수 있는 비율을 제한합니다. 각 Client가 3회 Retry하면 장애 시 Traffic이 최대 4배가 될 수 있습니다.

Server가 `Retry-After`를 제공하고 Client는 Deadline 안에서만 Jitter Retry를 수행합니다.

## 12. Adaptive Concurrency
고정 Semaphore 외에 지연과 오류를 관측해 동시성 Limit을 조정할 수 있습니다. 하지만 제어 Loop가 불안정하면 진동이 생기므로 충분한 관측과 보수적인 조정이 필요합니다.

## 13. Readiness를 이용한 Load Shedding
Readiness Down은 Pod 전체를 Load Balancer에서 제외하는 큰 단위 제어입니다. 특정 Endpoint만 과부하라면 Filter·Bulkhead로 해당 요청만 거부하는 것이 낫습니다.

모든 Pod가 동시에 Readiness Down이 되면 전체 서비스가 사라질 수 있으므로 Threshold와 회복 Hysteresis를 둡니다.

## 14. Hysteresis

```text
Connection 사용률 > 90%가 30초 지속 -> 제한 시작
Connection 사용률 < 60%가 60초 지속 -> 제한 해제
```

같은 Threshold로 즉시 On·Off하면 상태가 빠르게 흔들립니다.

## 15. 부하 테스트
- Step Load로 포화점 탐색
- Spike에서 Queue·Readiness 변화
- DB 지연 주입
- 외부 API 429·Timeout
- Retry On·Off 비교
- 중요한 Traffic이 낮은 우선순위보다 보호되는지 확인

성공 기준은 최대 처리량이 아니라 과부하에서도 Tail Latency가 제한되고 회복되는 것입니다.

## 16. 운영 Runbook
1. 어떤 자원이 포화됐는지 확인합니다.
2. Retry·Batch·무거운 Endpoint를 줄입니다.
3. Load Shedding이 동작하는지 확인합니다.
4. 단순 Scale-out이 하위 DB 부하를 더 키우지 않는지 판단합니다.
5. 회복 후 제한을 점진적으로 해제합니다.

---

## 17. 실무 사례 적용 진단과 개선 과제

이 사례에는 `DbBackpressureFilter`, Traffic Capacity Readiness와 Map API Rate Limit이 있어 과부하 제어가 실제 구현돼 있습니다. 다만 DB, 외부 API, Async Executor, Outbox Queue의 수용량이 하나의 Capacity Budget으로 연결되지는 않았고 환경별 임계치의 근거도 문서화가 부족합니다.

해결책은 Hikari Pool 대기, HTTP 동시 요청, Executor Queue, Outbox Age를 하나의 Saturation Dashboard로 연결하고 부하 Test로 임계치를 산정하는 것입니다. Readiness는 느린 Scale-out 신호, 429/503 Load Shedding은 빠른 보호 신호로 역할을 분리하며 Hysteresis를 둡니다.

완료 기준은 목표 부하를 넘겼을 때 Memory/Queue가 무한 증가하지 않고 중요 요청의 SLO가 유지되며, 거절률·회복 시간이 자동 Test와 Runbook에 수치로 남는 상태입니다.

---

# Reference
- [[k6 부하 테스트와 성능 검증]]
- [[Circuit Breaker와 Resilience4j]]
- [[In-flight Deduplication]]
- [[Bucket4j-RateLimiter]]
- [[Spring Boot Actuator와 Micrometer Observation]]
