---
id: Prometheus Operator와 ServiceMonitor
started: 2026-06-16
tags:
  - ✅DONE
  - Prometheus
  - K8S
  - Observability
group:
  - "[[Infra]]"
---
# Prometheus Operator와 ServiceMonitor

## 1. 개요 (Overview)
**Prometheus Operator**는 Prometheus, Alertmanager와 Scrape 설정을 Kubernetes Custom Resource로 관리합니다. **ServiceMonitor**는 어떤 Service의 어떤 Endpoint를 수집할지 선언합니다.

```text
Application /actuator/prometheus
  <- Kubernetes Service
  <- ServiceMonitor
  <- Prometheus Operator
  <- Prometheus
```

---

## 2. ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  labels:
    release: kube-prometheus-stack
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: core-app
  endpoints:
    - port: http
      path: /actuator/prometheus
      interval: 30s
```

ServiceMonitor는 Pod가 아니라 Service Label을 선택합니다. Chart의 Service와 ServiceMonitor Selector가 일치하는지 확인해야 합니다.

---

## 3. Namespace와 Label 선택
Prometheus는 모든 Namespace의 ServiceMonitor를 자동으로 보지 않을 수 있습니다. `serviceMonitorSelector`, `serviceMonitorNamespaceSelector`와 Helm Release Label 정책을 함께 확인합니다.

Resource는 생성됐지만 Target이 보이지 않는 경우 가장 먼저 Selector와 Namespace를 확인합니다.

---

## 4. 실무 사례 적용 관점
사례의 Application Helm Chart는 Core Application, Gateway, BFF, Metrics별 ServiceMonitor를 생성하고 `/actuator/prometheus`를 수집합니다. Shared `kube-prometheus-stack`이 Cluster·Application Metric과 Alert Rule을 관리합니다.

Metric Endpoint는 Cluster 내부에만 노출하고, 외부 공개가 필요하면 인증과 Network 경계를 둡니다.

---

## 5. Cardinality와 비용
- 사용자 ID, 차량 ID, 요청 URL 원문을 Label로 사용하지 않습니다.
- Histogram Bucket 수와 Scrape Interval을 목적에 맞게 조정합니다.
- 사용하지 않는 Metric은 Drop Rule을 검토합니다.
- Recording Rule로 반복되는 고비용 Query를 사전 계산합니다.
- Alert는 증상과 사용자 영향 중심으로 구성합니다.

---

## 6. Prometheus Operator Resource 관계

```text
Prometheus CR
  ├─ serviceMonitorSelector
  ├─ podMonitorSelector
  ├─ ruleSelector
  └─ retention / storage

ServiceMonitor
  -> Service 선택
  -> Endpoint Port 이름 선택
  -> Pod Target 발견
```

Operator는 ServiceMonitor 자체를 Scrape하지 않습니다. ServiceMonitor를 읽어 Prometheus Configuration을 생성합니다. 따라서 CRD, Operator, Prometheus Instance가 모두 정상이어야 합니다.

## 7. ServiceMonitor 상세 설정

```yaml
spec:
  namespaceSelector:
    matchNames: [production]
  selector:
    matchLabels:
      app.kubernetes.io/name: core-app
  endpoints:
    - port: http
      path: /actuator/prometheus
      interval: 30s
      scrapeTimeout: 10s
      honorLabels: false
```

`port`는 Service의 숫자 Port가 아니라 **Port Name**을 가리킵니다. 이 불일치는 Resource는 정상인데 Target이 생성되지 않는 대표 원인입니다.

## 8. Label 설계와 Relabeling
Target Label은 조회·Alert Routing의 기준입니다. `cluster`, `namespace`, `service`, `environment`처럼 안정적인 Label을 통일합니다.

`relabelings`는 Scrape 전 Target Label을 변경하고, `metricRelabelings`는 Scrape한 Sample을 저장하기 전에 필터링합니다. Metric Drop은 비용을 줄이지만 이후 복구할 수 없으므로 실제 사용 여부를 확인합니다.

## 9. Recording Rule과 Alert Rule

```yaml
groups:
  - name: core-api
    rules:
      - record: fms:http_request_error_ratio:5m
        expr: |
          sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
          /
          sum(rate(http_server_requests_seconds_count[5m]))
```

Dashboard와 Alert에서 긴 Query를 반복하지 않고 Recording Rule을 사용합니다. Alert는 단순 CPU 상승보다 오류율, 지연, 가용성과 같은 사용자 영향에 연결합니다.

## 10. 흔한 장애와 진단 순서

### ServiceMonitor가 발견되지 않음
1. CRD가 존재하는지 확인합니다.
2. Prometheus의 ServiceMonitor Selector와 Release Label을 확인합니다.
3. Namespace Selector를 확인합니다.

### Target이 Down
1. Service Endpoint와 Port Name을 확인합니다.
2. Prometheus Pod에서 Metric URL에 접근 가능한지 확인합니다.
3. NetworkPolicy, Mesh mTLS, 인증 설정을 확인합니다.

### Scrape는 되지만 시계열 폭증
최근 추가된 Label과 URI Template 처리를 확인합니다. Path Variable이 실제 ID로 기록되지 않게 합니다.

## 11. 용량 계획
대략적인 Sample 수는 다음 요소에 비례합니다.

```text
Series 수 × (Retention / Scrape Interval)
```

Replica 증가, Histogram Bucket, 상태 코드·URI·Exception Label 조합이 Series 수를 크게 늘립니다. Retention과 Persistent Volume 크기를 변경 전에 계산합니다.

## 12. 검증 체크리스트
- Helm Render 결과에서 Service와 ServiceMonitor Label을 대조합니다.
- Prometheus Targets 화면에서 실제 Scrape URL과 오류를 확인합니다.
- 재배포 후 old Replica Label이 불필요하게 남지 않는지 확인합니다.
- Alert Rule을 `promtool`로 검사합니다.
- 장애를 주입해 Alert 발생·해제·Notification을 End-to-end로 확인합니다.

---

## 13. 배포 사례 적용 진단과 개선 과제

ServiceMonitor가 각 Workload Chart에 있지만 Label Selector가 맞지 않으면 조용히 Target이 사라질 수 있습니다. Recording/Alert Rule의 소유권, Retention·Storage 용량, 고 Cardinality 제한도 서비스 증가에 따라 운영 부채가 됩니다.

CI에서 Rendered ServiceMonitor와 Service Label Match를 검사하고 Prometheus Target Down·Rule Evaluation Failure를 경보합니다. Series 증가율과 TSDB Head/Retention을 용량 계획에 포함하고 업무 Label Allowlist를 둡니다.

완료 기준은 신규 서비스 배포 후 Target·기본 SLI·Alert가 자동 확인되고, Label 변경이 CI에서 실패하며, 보존 기간 동안 예상 Disk와 Query P95를 유지하는 상태입니다.

---

# Reference
- [Prometheus Operator](https://prometheus-operator.dev/)
- [ServiceMonitor API](https://prometheus-operator.dev/docs/api-reference/api/)
- [[Spring Boot Actuator와 Micrometer Observation]]
- [[Terraform을 이용한 Otel + LGTM IaC 구성]]
