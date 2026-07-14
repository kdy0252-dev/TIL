---
id: Spring Boot Actuator와 Micrometer Observation
started: 2026-06-06
tags:
  - ✅DONE
  - Java-Spring
  - Observability
group:
  - "[[Java Spring]]"
---
# Spring Boot Actuator와 Micrometer Observation

## 1. 개요 (Overview)
**Spring Boot Actuator**는 Health, Metrics, Environment 등 운영 Endpoint를 제공하고, **Micrometer**는 Metric과 Observation을 Vendor-neutral API로 기록합니다. 애플리케이션이 단순히 실행 중인지가 아니라 실제로 트래픽을 받을 수 있는지를 표현해야 Kubernetes와 운영자가 올바르게 판단할 수 있습니다.

---

## 2. Health 상태 구분

| Probe | 질문 | 실패 시 동작 |
|---|---|---|
| Startup | 초기화가 끝났는가? | 다른 Probe 시작 지연 |
| Liveness | Process를 재시작해야 하는가? | Container 재시작 |
| Readiness | 지금 트래픽을 받을 수 있는가? | Service Endpoint에서 제외 |

DB가 잠시 느리다는 이유로 Liveness를 실패시키면 모든 Pod가 동시에 재시작해 장애를 키울 수 있습니다. 외부 의존성·Backpressure 상태는 주로 Readiness에 반영합니다.

---

## 3. Actuator 설정

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  endpoint:
    health:
      probes:
        enabled: true
```

`env`, `configprops`, `beans` 같은 Endpoint는 민감 정보를 노출할 수 있으므로 기본 비공개를 유지합니다.

---

## 4. Micrometer Observation
Observation은 하나의 업무 작업에서 Timer, Trace, Log Correlation을 함께 생성할 수 있는 API입니다.

```java
return Observation.createNotStarted("booking.dispatch", observationRegistry)
        .lowCardinalityKeyValue("result", "success")
        .observe(() -> dispatchService.dispatch(command));
```

- **Low Cardinality**: 상태, 결과 유형처럼 값의 종류가 제한됨
- **High Cardinality**: Booking ID, 사용자 ID처럼 값이 계속 증가함

High-cardinality 값을 Metric Label로 사용하면 시계열 수가 폭증합니다. Trace Tag나 Log Field로 제한합니다.

---

## 5. 실무 사례 적용 관점
이 사례는 Health·Prometheus Endpoint, OTLP Trace·Metric Export, Request Correlation과 업무 Metric을 사용합니다. `TrafficCapacityHealthIndicator`는 DB Backpressure 상태를 Readiness Group에 포함하여 과부하 Pod가 신규 트래픽을 받지 않게 합니다.

```text
Application
  -> Actuator /prometheus
  -> ServiceMonitor
  -> Prometheus
  -> Grafana

Application Observation
  -> OTLP
  -> Trace Backend
```

---

## 6. 운영 지표
- HTTP 요청 수, 오류율, P95·P99 지연
- JVM Heap, GC Pause, Thread와 Connection Pool
- DB Query와 Transaction 시간
- Outbox 대기·재시도·실패 수
- Active In-flight 작업과 Queue 포화도
- Readiness 상태 변경 횟수

---

## 7. Health Contributor

```java
@Component
public class TrafficCapacityHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        return capacityAvailable()
                ? Health.up().build()
                : Health.outOfService().withDetail("reason", "db-saturated").build();
    }
}
```

Detail에 Credential, Host 내부 정보나 개인 데이터를 넣지 않습니다. Health Check 자체가 느린 외부 호출을 매번 수행하지 않게 Cache·Timeout을 둡니다.

## 8. Health Group
Liveness와 Readiness에 포함할 Indicator를 명시적으로 분리합니다. 기본 전체 Health를 그대로 Probe에 연결하지 않습니다.

```yaml
management.endpoint.health.group:
  liveness.include: livenessState
  readiness.include: readinessState,trafficCapacity
```

## 9. Counter, Gauge, Timer
- Counter: 단조 증가 Event 수
- Gauge: 현재 Queue Size·Active 작업
- Timer: 처리 시간과 횟수
- DistributionSummary: Byte·Batch 크기

Gauge Supplier가 무거운 Query를 실행하지 않게 하고, Timer는 성공·실패 Tag를 제한된 값으로 기록합니다.

## 10. Observation Lifecycle

```text
start
  -> scope open
  -> low/high-cardinality key 추가
  -> event/error
stop
```

Scope를 닫지 않으면 Context가 다음 작업으로 누출될 수 있습니다. `observe()`나 `try-with-resources`를 사용합니다.

## 11. Context Propagation
HTTP, Executor, Virtual Thread와 Reactive 경계에서 Trace·Observation Context가 전파되어야 합니다. 무조건 ThreadLocal을 복사하지 않고 Spring·Micrometer의 Context Propagation 지원을 사용합니다.

## 12. Custom Metric Naming
이름은 단위와 Event를 명확히 합니다.

```text
fms.outbox.pending
fms.outbox.delivery.duration
fms.booking.dispatch.count
```

환경·서비스는 Resource Attribute로 두고 Metric 이름에 포함하지 않습니다.

## 13. SLO 연결
Metric 수집 목적을 SLI와 연결합니다.

- Availability: 성공 요청 비율
- Latency: 임계 시간 내 요청 비율
- Freshness: 가장 오래된 Outbox 대기 시간
- Correctness: Reconciliation 불일치 비율

Alert는 Error Budget 소진 속도나 지속적인 사용자 영향을 중심으로 설계합니다.

## 14. Endpoint 보안
- Health Summary만 외부 Load Balancer에 공개
- Prometheus Endpoint는 Cluster 내부 수집기만 접근
- Env·Heap Dump·Thread Dump는 강한 인증과 감사 필요
- CORS와 Management Port 분리를 검토

## 15. 테스트와 운영 검증
- Health Indicator의 Up·Down·회복을 단위 테스트합니다.
- DB 포화 시 Readiness만 Down되는지 확인합니다.
- Metric Tag Cardinality를 Test Traffic으로 점검합니다.
- Trace와 Log의 Correlation ID를 확인합니다.
- Prometheus Scrape 장애가 업무 요청을 방해하지 않는지 확인합니다.

---

## 16. 실무 사례 적용 진단과 개선 과제

이 사례는 Prometheus Endpoint, Custom Readiness, `ObservationRegistry`와 `@ObservedSpan`을 핵심 조회·배차 흐름에 사용합니다. 다만 Instrumentation이 업무 영역별로 고르게 적용되지 않고 Metric/Span 이름·Low Cardinality Tag의 중앙 규약이 부족합니다.

먼저 핵심 User Journey별 SLI와 Span Map을 정하고 공통 Naming Convention을 Test합니다. Outbox Age, 외부 Provider Latency, DB Pool Saturation, Load Shedding을 동일 Dashboard에서 연결하며 Actuator 상세 정보 노출은 최소화합니다.

완료 기준은 요청 하나를 Gateway부터 DB·외부 API·비동기 후속 처리까지 Trace로 따라갈 수 있고, 모든 호출 Alert가 SLO와 Runbook에 연결되며 고 Cardinality Tag가 Registry Filter에서 차단되는 상태입니다.

---

# Reference
- [Spring Boot Actuator](https://docs.spring.io/spring-boot/reference/actuator/)
- [Micrometer Observation](https://docs.micrometer.io/micrometer/reference/observation.html)
- [[Terraform을 이용한 Otel + LGTM IaC 구성]]
- [[Backpressure와 Load Shedding]]
