---
id: Tail Sampling과 Metric Exemplar
started: 2026-06-18
tags:
  - ✅DONE
  - OpenTelemetry
  - Tail-Sampling
group:
  - "[[Infra Otel+LGTM]]"
---
# Tail Sampling과 Metric Exemplar

## 1. Sampling의 목적

모든 Trace를 저장하면 비용과 Cardinality가 커집니다. Sampling은 진단 가치가 높은 Trace를 제한된 예산 안에서 보존합니다.

---

## 2. Head Sampling

요청 시작 시 Trace ID 기반으로 결정합니다. 비용이 낮고 단순하지만 결과를 모르므로 희귀 오류와 느린 요청을 놓칠 수 있습니다. Parent 결정 전파가 중요합니다.

---

## 3. Tail Sampling

Trace가 끝난 뒤 Status, Duration, Attribute와 Span을 보고 결정합니다.

- Error Trace 100%
- P99 이상 Latency
- 핵심 업무 Route
- 특정 Release·Tenant의 제한된 Debug Sample
- 나머지는 확률 Sample

결정 전 Trace를 Buffer해야 하므로 Memory와 지연 비용이 있습니다.

---

## 4. Collector 구조

같은 Trace의 Span이 같은 Tail Sampler에 도착하도록 Trace ID 기반 Load Balancing이 필요합니다. 단순 Round-robin은 Span을 여러 Collector에 흩어 불완전한 판단을 만듭니다.

Decision Wait, Expected Trace 수, Memory Limiter와 Overflow 정책을 설정합니다.

---

## 5. Late Span과 Partial Trace

결정 뒤 늦게 도착한 Span은 유실되거나 별도 처리될 수 있습니다. Async 작업과 Queue가 긴 시스템은 Decision Wait를 늘려야 하지만 Buffer 비용이 커집니다.

Partial Trace 비율과 Dropped Span을 Metric으로 봅니다.

---

## 6. Exemplar

Exemplar는 Histogram Sample에 대표 Trace ID를 연결합니다.

```text
P99 Latency Bucket
  -> Exemplar Trace ID
  -> Tempo의 실제 느린 Trace
```

Metric은 현상을, Trace는 한 요청의 원인을 보여줍니다.

---

## 7. Context와 Cardinality

Trace ID를 일반 Metric Label로 넣으면 Series가 폭증합니다. Exemplar 전용 저장을 사용합니다. `http.route`는 Template을 쓰고 실제 URL·User ID를 Metric Label로 넣지 않습니다.

---

## 8. Sampling Bias

오류만 저장하면 정상 Traffic의 Baseline을 잃습니다. Service·Route·Environment별 최소 확률 Sample을 유지합니다. Sampling 정책 변경은 분석 결과의 시계열 비교에도 영향을 줍니다.

---

## 9. 사례 적용

Gateway→업무 API→DB·외부 지도 호출은 Trace로 연결하고, 예약·배차 실패와 느린 통계 요청을 Tail Policy로 보존합니다. Outbox 비동기 처리는 Span Link로 원 요청과 연결합니다.

---

## 10. 실패 양상과 진단

| 증상 | 확인할 항목 |
|---|---|
| Trace가 중간부터 보임 | Span Routing, Context 전파, Decision Wait |
| Collector Memory 급증 | Trace 유입률, Expected Trace, Policy 복잡도 |
| 오류 Trace가 누락됨 | Status 설정, Policy 순서, Late Span |
| Trace는 있으나 Metric 연결 불가 | Exemplar 저장, Trace ID, Datasource Link |
| 특정 서비스만 과도하게 저장 | Attribute 조건과 기본 확률 Policy |

Collector 재시작과 Backend 지연 중 Buffer가 어떻게 손실되는지도 별도 Test합니다.

---

## 11. 적용 단계

1. 현재 Trace 유입량과 Storage 비용을 측정합니다.
2. Head Sampling을 유지한 채 오류·지연 Route를 정의합니다.
3. Stage에서 Trace ID 기반 Routing과 Tail Sampler를 배치합니다.
4. Partial Trace·Drop·Decision Latency를 관찰합니다.
5. Histogram Exemplar에서 대표 Trace로 이동하도록 Grafana를 연결합니다.
6. Sampling 정책 변경 이력을 Version 관리합니다.

---

## 12. 완료 기준

- [ ] Head·Tail Sampling 비용과 정보 차이를 설명합니다.
- [ ] Trace ID 기반 Collector Routing이 적용됩니다.
- [ ] Error·Latency·업무 우선순위 Policy가 있습니다.
- [ ] Partial Trace와 Buffer Drop을 감시합니다.
- [ ] Grafana Histogram Exemplar에서 Tempo Trace로 이동할 수 있습니다.

# Reference

- [OpenTelemetry Tail Sampling Processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/tailsamplingprocessor)
- [Prometheus Exemplars](https://prometheus.io/docs/concepts/exemplar/)
- [[Grafana Alloy와 LGTM 수집 파이프라인]]
