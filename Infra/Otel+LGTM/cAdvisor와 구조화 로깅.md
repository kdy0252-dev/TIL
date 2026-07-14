---
id: cAdvisor와 구조화 로깅
started: 2026-06-19
tags:
  - ✅DONE
  - Infra
  - Observability
  - Logging
group:
  - "[[Infra]]"
---
# cAdvisor와 구조화 로깅

## 1. 개요 (Overview)
애플리케이션 Metric만으로는 Container CPU Throttling, Memory Limit, Network와 Filesystem 사용량을 알기 어렵습니다. **cAdvisor**는 Container Runtime 지표를 수집하고, **구조화 로깅**은 Log를 JSON Field로 기록하여 검색과 상관관계를 가능하게 합니다.

---

## 2. cAdvisor
cAdvisor는 Container별 CPU, Memory, Network, Filesystem 지표를 Prometheus 형식으로 제공합니다.

```text
Container Runtime
  -> cAdvisor
  -> Prometheus
  -> Grafana
```

주요 지표는 CPU Usage·Throttling, Working Set Memory, OOM, Network Bytes와 Filesystem 사용량입니다. Local Docker Compose 부하 테스트에서 애플리케이션 처리량과 Container 자원 사용량을 함께 비교할 수 있습니다.

Kubernetes 운영 환경에서는 kubelet/cAdvisor 지표를 kube-prometheus-stack이 수집하므로 별도 cAdvisor Daemon 배치가 항상 필요한 것은 아닙니다.

---

## 3. 구조화 로깅

```json
{
  "timestamp": "2026-07-14T10:00:00Z",
  "level": "INFO",
  "service": "core-app",
  "trace_id": "...",
  "request_id": "...",
  "event": "booking.dispatched",
  "booking_id": 100
}
```

Message 문자열을 Parser로 다시 해석하는 대신 Field로 저장하면 조건 검색과 집계가 안정적입니다.

---

## 4. Cardinality와 개인정보
- Trace ID, Request ID는 Log에는 적합하지만 Metric Label에는 부적합합니다.
- 전화번호, Token, Credential, 전체 Request Body를 기록하지 않습니다.
- 업무 ID도 접근 권한과 Retention 정책을 고려합니다.
- 오류 Stack Trace는 보관하되 동일 오류의 폭주를 Rate Limit합니다.

---

## 5. 실무 사례 적용 관점
이 사례의 Local Observability Stack은 cAdvisor와 Prometheus로 Container Resource를 수집합니다. 애플리케이션은 Logstash 호환 JSON 형식으로 Console Log를 출력하고 Correlation ID를 Gateway부터 Backend까지 전파합니다.

Kubernetes에서는 Grafana Alloy가 Pod Log와 Telemetry를 수집하고 Loki·Tempo·Prometheus 계열 Backend로 전달합니다.

---

## 6. Container Metric 해석

### CPU Usage와 Throttling
CPU Usage가 낮아도 CFS Throttling이 높으면 짧은 Burst가 CPU Limit에 막히고 있을 수 있습니다. 요청 지연과 다음 지표를 함께 봅니다.

```text
rate(container_cpu_usage_seconds_total[5m])
rate(container_cpu_cfs_throttled_seconds_total[5m])
```

CPU Request는 Scheduling 기준이고 CPU Limit은 실행 상한입니다. Java Server는 높은 Burst가 발생할 수 있으므로 Limit을 무조건 Request와 같게 두지 않습니다.

### Memory Usage
`container_memory_usage_bytes`에는 Page Cache가 포함되어 실제 압박을 과대평가할 수 있습니다. Working Set, RSS, JVM Heap·Non-heap과 OOM Event를 함께 확인합니다.

```text
Container Memory
  = JVM Heap
  + Metaspace
  + Thread Stack
  + Direct Buffer
  + Native Library
  + Page Cache 일부
```

Heap Max를 Container Limit에 가깝게 잡으면 Native Memory를 위한 여유가 없어 OOMKill이 발생합니다.

### Network와 Filesystem
Network Byte 증가만으로 병목을 판단하지 않고 Packet Drop, Error, Retransmission과 Application Throughput을 함께 봅니다. Filesystem Usage는 Log 폭주나 Temporary File 누수를 발견하는 데 유용합니다.

## 7. 구조화 Log Schema
서비스마다 Field 이름이 다르면 통합 검색이 어렵습니다. 공통 Envelope를 정합니다.

| 필드 | 의미 | 예시 |
|---|---|---|
| `timestamp` | UTC Event 시각 | ISO-8601 |
| `level` | 심각도 | INFO, WARN, ERROR |
| `service` | 논리적 서비스명 | production-app |
| `trace_id` | 분산 Trace 연결 | 32자리 Hex |
| `request_id` | 요청 상관관계 | Gateway 생성 ID |
| `event` | 안정적인 Event 이름 | `outbox.delivery.failed` |
| `tenant_id` | Tenant 경계 | 필요 시 비식별 값 |
| `error.type` | 오류 분류 | TimeoutException |

Human-readable Message와 Machine-readable Field를 함께 두되, Message Parsing을 검색 계약으로 사용하지 않습니다.

## 8. Log Level과 Sampling
- ERROR는 운영 조치가 필요한 실패에 사용합니다.
- 예상 가능한 Validation 오류를 ERROR Stack Trace로 남기지 않습니다.
- 반복되는 동일 오류는 Rate Limit이나 Sampling을 적용합니다.
- 정상 고빈도 Event는 Metric으로 집계하고 Log는 표본만 남깁니다.
- Debug Log는 운영에서 동적으로 켤 때 자동 만료되게 합니다.

## 9. Metric·Log·Trace 연결

```text
Metric Alert
  -> 영향 시간대·Service 확인
  -> Trace에서 느린 Span 확인
  -> trace_id로 Log 검색
  -> Container Metric으로 CPU/Memory 압박 확인
```

세 신호의 `service.name`, 환경, Namespace Label을 동일하게 유지해야 이동이 자연스럽습니다.

## 10. 장애 사례

### 지연은 증가하지만 CPU는 낮음
DB Connection 대기, 외부 API, Lock, Thread Pinning을 확인합니다. Container CPU만 보고 증설하면 원인이 해결되지 않습니다.

### Loki 저장량 급증
새 배포에서 Debug Log나 요청 Body가 출력되는지 확인합니다. Retention보다 먼저 발생 Source를 줄입니다.

### 특정 Container만 Metric이 없음
cAdvisor Target, Container Label, Prometheus Relabeling, Runtime Socket 접근 권한을 확인합니다.

## 11. 검증 체크리스트
- 부하 테스트 중 CPU Usage·Throttling·Memory Working Set을 함께 기록합니다.
- 의도적인 오류를 발생시켜 Trace ID로 Log를 찾을 수 있는지 확인합니다.
- 개인정보와 Credential이 Log에 없는지 정규식과 Sample Review로 검사합니다.
- Log Backend 장애가 애플리케이션 요청을 Block하지 않는지 확인합니다.
- Retention과 예상 일일 수집량으로 저장 비용을 계산합니다.

---

## 13. 실무 사례 적용 진단과 개선 과제

Container Metric과 JSON Log 기반은 있으나 Application마다 Field 이름과 민감 정보 제거 수준이 다르면 Loki Query와 Incident 상관 분석이 깨집니다. Debug Log와 Stack Trace 폭증은 비용과 Collector Backpressure를 동시에 만들 수 있습니다.

`timestamp/level/service/environment/trace_id/message/error.type` Schema를 공통 Log Encoder로 고정하고 Authorization·Cookie·개인정보를 금지합니다. Namespace·Service별 Log Rate/Byte Budget, Sampling과 Retention을 정의하고 Dropped Log를 경보합니다.

완료 기준은 임의 Trace ID로 Gateway부터 Worker Log까지 조회되고 PII Scanner가 CI/Stage에서 통과하며, Error Storm에도 Alloy·Loki Queue와 비용이 한도 안에 머무는 상태입니다.

---

# Reference
- [cAdvisor](https://github.com/google/cadvisor)
- [Spring Boot Structured Logging](https://docs.spring.io/spring-boot/reference/features/logging.html#features.logging.structured)
- [Grafana Alloy](https://grafana.com/docs/alloy/latest/)
- [[Terraform을 이용한 Otel + LGTM IaC 구성]]
