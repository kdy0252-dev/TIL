---
id: Grafana Alloy와 LGTM 수집 파이프라인
started: 2026-06-15
tags:
  - ✅DONE
  - Observability
  - Grafana
  - Alloy
group:
  - "[[Infra Otel+LGTM]]"
---
# Grafana Alloy와 LGTM 수집 파이프라인

## 1. 개요 (Overview)

Grafana Alloy는 Kubernetes에서 Metric, Log, Trace를 발견하고 가공해 각각의 Backend로 전달하는 OpenTelemetry Collector 계열의 수집기입니다. 이 배포 사례에서는 Alloy가 Node와 Pod 가까이에서 Telemetry를 모으고 Prometheus, Loki, Tempo로 전달하는 관측 데이터 평면을 구성합니다.

```text
Application / Node / Kubernetes API
        -> Grafana Alloy
        -> Prometheus : Metric
        -> Loki       : Log
        -> Tempo      : Trace
        -> Grafana    : Query와 상관 분석
```

Alloy의 핵심 역할은 Dashboard를 그리는 것이 아니라 **발견, 수집, 변환, 필터링, 전송**입니다.

---

## 2. 왜 통합 Collector를 사용하는가

Promtail, OpenTelemetry Collector, Prometheus Agent를 각각 운영할 수도 있습니다. 그러나 Collector가 늘어나면 동일한 Kubernetes Discovery와 Label 규칙이 중복되고 Resource 사용량과 Upgrade 지점도 증가합니다.

Alloy로 통합하면 다음 이점이 있습니다.

- Component 간 연결이 명시적인 Pipeline으로 표현됩니다.
- OpenTelemetry와 Prometheus 생태계를 함께 사용할 수 있습니다.
- 공통 Kubernetes Metadata를 Signal마다 일관되게 붙일 수 있습니다.
- Edge에서 불필요한 데이터와 민감 정보를 제거할 수 있습니다.

통합이 모든 문제를 해결하는 것은 아닙니다. 하나의 Alloy 장애가 여러 Signal에 영향을 줄 수 있으므로 Pipeline별 Queue, Retry, Resource와 Alert를 구분해야 합니다.

---

## 3. 배치 형태

### DaemonSet

각 Node에 하나씩 실행해 Container Log, Node Metric, Host 경로에 접근합니다. Log File Tail과 Node-local 수집에 적합합니다.

### Deployment

Kubernetes API Discovery, Cluster Event, Remote Endpoint 수집처럼 Node에 종속되지 않은 작업을 수행합니다. Replica를 늘릴 때 동일 데이터를 중복 수집하지 않도록 Sharding이나 Leader Election 여부를 확인합니다.

### Gateway

Application이 OTLP를 중앙 Endpoint로 전송할 때 사용합니다. 인증, Sampling, Batch, Backend Routing을 중앙화할 수 있지만 Network Hop과 병목 지점이 추가됩니다.

이 사례처럼 여러 Signal을 다루는 환경에서는 DaemonSet과 Deployment 역할을 분리하는 편이 장애 범위를 명확히 합니다.

---

## 4. Component Graph

Alloy Configuration은 Source에서 Receiver, Processor, Exporter로 흐르는 Graph입니다.

```text
discovery.kubernetes
  -> discovery.relabel
  -> loki.source.kubernetes
  -> loki.process
  -> loki.write
```

Metric은 보통 다음과 같이 흐릅니다.

```text
prometheus.scrape
  -> prometheus.relabel
  -> prometheus.remote_write
```

Trace는 OTLP Receiver에서 받아 Batch와 Filter를 거쳐 Tempo로 보냅니다.

Graph가 명시적이면 어느 단계에서 Label이 사라지거나 Sample이 버려졌는지 추적하기 쉽습니다. 반대로 한 Configuration에 너무 많은 조건을 넣으면 변경 영향이 넓어지므로 Signal과 책임별 File 또는 Module로 나눕니다.

---

## 5. Kubernetes Discovery와 Label 설계

Kubernetes Discovery는 Pod, Service, Endpoint의 Meta Label을 제공합니다. 그대로 저장하면 내부 UID, Annotation, 임시 Label이 Cardinality를 폭증시킵니다. 필요한 값만 안정된 이름으로 변환합니다.

권장 공통 Label은 다음과 같습니다.

- `cluster`
- `environment`
- `namespace`
- `service_name`
- `pod`
- `container`
- `version`

Request ID, User ID, URL 전체, Exception Message는 Metric Label로 사용하지 않습니다. 이런 값은 Log Field나 Trace Attribute로 보관하고 필요할 때 검색합니다.

Label 이름은 Signal 간 연결 키입니다. Metric의 `service`, Log의 `app`, Trace의 `service.name`이 제각각이면 Grafana에서 자동 상관 분석이 어렵습니다.

---

## 6. Log Pipeline

Container Runtime Log는 Timestamp, Stream, Payload를 담습니다. Alloy는 이를 읽어 JSON을 Parsing하고 필요한 Field를 Label 또는 Structured Metadata로 승격합니다.

```text
Container Log File
  -> CRI Parsing
  -> JSON Parsing
  -> Timestamp 정규화
  -> 민감 정보 제거
  -> Label 정규화
  -> Loki Batch 전송
```

Parsing 실패 Log를 조용히 버리면 장애 시 증거가 사라집니다. 원문을 유지하거나 Parsing Error Counter를 경보해야 합니다. Stack Trace가 여러 줄이면 Multiline 규칙이 필요하지만, 시작 패턴이 부정확하면 서로 다른 요청의 Log가 하나로 합쳐질 수 있습니다.

Password, Token, Cookie, Authorization Header는 애플리케이션에서 기록하지 않는 것이 우선입니다. Collector의 Masking은 방어선이지 비밀 관리의 주 수단이 아닙니다.

---

## 7. Metric Pipeline

Alloy는 Prometheus 형식 Endpoint를 Scrape하거나 Metric을 Remote Write할 수 있습니다. Scrape 주기와 Timeout은 Target 수와 수집 비용을 결정합니다.

```text
초당 Sample 수 ≈ Target 수 × Target당 Series 수 ÷ Scrape Interval
```

불필요한 Histogram Bucket, JVM 내부 Metric, 고유 ID Label은 Edge에서 Drop할 수 있습니다. 다만 Drop 규칙은 되돌릴 수 없으므로 실제 Query와 Alert가 사용하지 않는다는 근거가 필요합니다.

Remote Write Queue가 차면 Memory가 증가하고 오래된 Sample이 폐기될 수 있습니다. Queue Length, Retry, Dropped Sample, Backend Latency를 Collector 자체 Metric으로 감시합니다.

---

## 8. Trace Pipeline

Application은 OTLP/gRPC 또는 OTLP/HTTP로 Span을 보냅니다. Collector는 Batch 처리 후 Tempo로 전달합니다.

Sampling 위치에 따라 의미가 달라집니다.

- Head Sampling: 요청 시작 시 결정하므로 저렴하지만 실패 요청을 놓칠 수 있습니다.
- Tail Sampling: Trace 완료 후 결과를 보고 선택하므로 오류·지연 Trace를 보존하기 좋지만 Buffer 비용이 큽니다.

Trace Attribute에 개인정보나 전체 Query를 넣지 않습니다. `service.name`, `deployment.environment`, `http.route`, `error.type`처럼 집계 가능한 속성을 우선합니다.

Context Propagation이 끊기면 Service별 Span은 존재해도 하나의 Trace로 연결되지 않습니다. HTTP, Kafka, 비동기 Executor 경계를 별도로 검증해야 합니다.

---

## 9. Backpressure와 장애 시 동작

Backend가 느려지면 Alloy는 Queue와 Retry로 일시 장애를 흡수합니다. 그러나 Buffer는 무한하지 않습니다.

```text
Backend 지연
  -> 전송 Queue 증가
  -> Alloy Memory 증가
  -> Queue 한도 도달
  -> 오래된 Telemetry Drop
```

관측 파이프라인 장애가 업무 Pod를 축출하게 해서는 안 됩니다. Alloy Resource Limit, PriorityClass, Node 배치와 Disk Buffer 여부를 명확히 합니다. Retry는 Exponential Backoff와 최대 시간을 두어 Backend 복구 후 Retry Storm이 발생하지 않게 합니다.

관측 데이터 손실은 업무 실패와 다르지만, Incident 분석 가능성을 훼손합니다. `dropped_entries`, `failed_samples`, `exporter_send_failed_spans` 같은 Signal별 손실 Metric을 경보합니다.

---

## 10. Multi-Tenancy와 보안

환경별 Namespace가 같은 Backend를 사용한다면 Query 격리와 보존 정책을 설계해야 합니다.

- Collector ServiceAccount는 필요한 Namespace와 Resource만 읽습니다.
- OTLP Receiver는 Cluster 외부에 무인증으로 노출하지 않습니다.
- Backend Credential은 Secret으로 주입하고 Configuration 출력에 남기지 않습니다.
- 환경·Cluster Label을 Collector가 신뢰 가능한 값으로 덮어씁니다.
- Tenant가 임의 Label로 다른 환경을 가장하지 못하게 합니다.

TLS는 전송 구간을 보호하지만 잘못 수집한 개인정보를 해결하지 않습니다. 수집 전 Data Classification이 필요합니다.

---

## 11. 운영 점검과 검증

변경 시 Signal별 End-to-End Smoke Test를 수행합니다.

1. 고유 Marker가 포함된 Test Log를 생성하고 Loki에서 조회합니다.
2. Test Counter를 증가시키고 Prometheus에서 Label과 값을 확인합니다.
3. HTTP 요청 하나를 보내 Trace가 여러 Service에 연결되는지 확인합니다.
4. Backend를 일시 차단해 Queue와 Retry, 복구 후 Drain을 관찰합니다.
5. Collector Pod를 재시작해 중복·손실 범위를 확인합니다.

### 점검표

- [ ] Metric, Log, Trace가 같은 Service·Environment 이름을 사용하는가
- [ ] 고 Cardinality Label을 Edge에서 통제하는가
- [ ] 민감 정보 제거 규칙과 Parsing 실패 Metric이 있는가
- [ ] Backend 장애 시 Queue 한도와 Drop 정책을 알고 있는가
- [ ] Alloy 자체 Metric과 Resource 사용량을 감시하는가
- [ ] Configuration 변경을 비운영 환경에서 재생 검증하는가

---

## 13. 배포 사례 적용 진단과 개선 과제

Alloy와 LGTM Stack은 구성돼 있지만 Signal별 Label 규약, Cardinality Budget, Backend 장애 시 Drop 허용량이 명시적으로 연결되어야 합니다. Collector 통합은 Alloy 장애가 Metric·Log·Trace 모두에 영향을 주는 공통 실패 지점도 만듭니다.

Signal마다 Queue·Retry·Drop Metric과 SLO를 정의하고 `cluster/environment/service_name`을 Collector에서 신뢰 가능한 값으로 정규화합니다. 민감 정보 Filter, High-cardinality Drop, Backend 차단 후 Buffer Drain을 Stage 환경에서 재생 Test합니다.

완료 기준은 Test 요청 하나가 세 Signal에서 같은 Service·Trace ID로 연결되고, Backend 장애 중 손실량을 측정할 수 있으며, Collector Resource 포화가 업무 Pod를 축출하지 않는 상태입니다.

---

# Reference

- [Grafana Alloy Documentation](https://grafana.com/docs/alloy/latest/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [[Prometheus Operator와 ServiceMonitor]]
- [[cAdvisor와 구조화 로깅]]
