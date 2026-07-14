---
id: Alertmanager와 Synthetic Monitoring
started: 2026-06-15
tags:
  - ✅DONE
  - Observability
  - Alertmanager
  - Synthetic-Monitoring
group:
  - "[[Infra Otel+LGTM]]"
---
# Alertmanager와 Synthetic Monitoring

## 1. 개요 (Overview)

Alertmanager는 Prometheus Alert를 수신해 중복 제거, 그룹화, 억제, Routing한 뒤 운영 채널로 전달합니다. Synthetic Monitoring은 시스템 외부에서 실제 사용 경로를 주기적으로 호출해 내부 Metric만으로 알 수 없는 DNS, TLS, CDN, Load Balancer 장애를 감지합니다.

이 배포 사례은 두 경로를 결합합니다.

```text
PrometheusRule -> Prometheus -> Alertmanager
                                  -> API Gateway
                                  -> Lambda Relay
                                  -> Teams

EventBridge -> Lambda HTTPS Check -> CloudWatch Metric/Alarm
                                      -> Alert 경로
```

내부 White-box Metric과 외부 Black-box Check를 함께 사용해야 “Pod는 정상인데 사용자는 접속할 수 없는” 상황을 발견할 수 있습니다.

---

## 2. Alert Lifecycle

Prometheus Rule의 조건이 `for` 시간 동안 유지되면 Alert가 Firing 상태가 됩니다. Alertmanager는 동일 Label 집합을 가진 Alert를 Group으로 묶고 Receiver에 보냅니다.

```text
Inactive -> Pending -> Firing -> Resolved
```

`for`가 너무 짧으면 순간 Spike에 알림이 쏟아지고, 너무 길면 실제 장애 감지가 늦습니다. Signal의 변동성과 허용 탐지 시간에 맞춥니다.

Alert가 Resolved됐다는 것은 원인이 해결됐다는 뜻이 아니라 Rule 조건이 더 이상 참이 아니라는 뜻입니다. Metric 수집 자체가 끊겨도 표현식에 따라 Resolved처럼 보일 수 있으므로 `absent()` 또는 수집 실패 Alert를 별도로 둡니다.

---

## 3. Label과 Annotation 계약

Alert Label은 Routing과 중복 제거에 쓰이므로 안정적이어야 합니다.

권장 Label은 `alertname`, `severity`, `service`, `environment`, `namespace`, `team`입니다. Annotation에는 사람이 대응할 `summary`, `description`, `runbook_url`, `dashboard_url`을 둡니다.

Pod UID나 Error Message 전체처럼 매번 달라지는 값을 Label에 넣으면 Alert Group이 분리됩니다. 이런 값은 Annotation에 둡니다.

---

## 4. Grouping, Inhibition, Silence

하나의 Node 장애로 수십 Pod Alert가 발생할 때 개별 알림을 모두 보내면 근본 원인을 찾기 어렵습니다. `group_by`로 Environment·Service·Alertname 단위로 묶고 `group_wait`, `group_interval`, `repeat_interval`을 조정합니다.

Inhibition은 상위 원인 Alert가 있을 때 하위 증상 Alert를 억제합니다. 예를 들어 Cluster Network 장애가 Firing이면 개별 Service Endpoint Alert를 억제할 수 있습니다.

Silence는 계획 작업 중 알림 전달을 잠시 중단합니다. 종료 시간, 작성자, 변경 Ticket을 기록하고 넓은 정규식 대신 정확한 Label Matcher를 사용합니다. Silence 중에도 Alert와 Metric 자체는 보존하며, Silence를 장애 해결 수단으로 사용하지 않습니다.

---

## 5. Receiver Routing

Severity만으로 Receiver를 나누기보다 서비스 소유권과 환경을 함께 사용합니다.

```text
Prod + Critical -> On-call 즉시 호출
Prod + Warning  -> Team 운영 채널
Non-prod        -> 개발 채널 또는 업무 시간 요약
Platform        -> Platform 팀
```

같은 Alert가 여러 Route에 중복 전송되는지 `continue` 설정을 확인합니다. Receiver 장애 시 Alertmanager Log와 Notification Failure Metric을 감시해야 합니다. Alert 생성이 정상이어도 전달 경로가 실패할 수 있습니다.

---

## 6. Teams Relay 구조

Alertmanager Webhook Payload와 Teams Card 형식 사이에는 변환 계층이 필요합니다. 이 사례의 구조에서는 API Gateway가 Webhook을 받고 Lambda가 Message Card로 변환해 Teams로 전달합니다.

```text
Alertmanager
  -> Tokenized API Gateway Path
  -> Lambda Payload 검증·변환
  -> Teams Webhook
```

Relay는 Firing·Resolved 상태, 여러 Alert Group, Severity·Service·Environment, Runbook Link, Teams Rate Limit과 Payload 크기를 처리해야 합니다.

Webhook Token이 URL Path에 있더라도 Secret처럼 관리합니다. Log에 전체 URL을 남기지 않고 API Gateway Rate Limit과 Lambda 최소 권한을 적용합니다. Relay 실패가 Alertmanager의 무한 재시도를 유발하지 않도록 Timeout과 실패 정책을 명확히 합니다.

---

## 7. Synthetic Monitoring의 관점

Synthetic Check는 실제 사용자가 거치는 외부 경로에서 실행해야 의미가 있습니다.

```text
DNS Resolution
  -> TCP Connect
  -> TLS Handshake
  -> CloudFront / ALB
  -> Application Response
```

Cluster 내부에서만 Health Endpoint를 호출하면 Public DNS, Certificate, WAF, CDN 장애를 놓칩니다. 반대로 외부 Check만으로는 내부 원인을 알 수 없으므로 Application Metric과 Trace로 Drill-down합니다.

---

## 8. Lambda 기반 HTTPS Check

EventBridge Schedule이 Lambda를 호출하고 Lambda는 대상 URL의 Status, Latency와 응답 조건을 확인한 뒤 CloudWatch Custom Metric을 기록할 수 있습니다.

Check는 단순 200뿐 아니라 예상 Host와 TLS Certificate, Redirect와 최종 URL, 응답 시간 상한, Content Marker, DNS·Connect·TLS·Read Timeout을 구분해 검증합니다.

전체 응답 Body나 Credential을 Log에 남기지 않습니다. 인증이 필요한 Check는 최소 권한 전용 계정과 Secret을 사용하고 상태를 변경하지 않는 Endpoint를 호출합니다.

Lambda가 VPC 내부에서 실행되면 NAT나 DNS 경로가 실제 외부 사용자와 달라질 수 있습니다. Check 위치가 무엇을 검증하는지 문서화합니다.

---

## 9. False Positive 방지

한 번의 Timeout으로 즉시 호출하면 Internet Jitter가 장애로 과대 평가됩니다. 연속 실패 횟수, 관측 Window와 다중 위치를 조합합니다.

```text
Failure Ratio = Failed Checks / Total Checks in Window
```

너무 긴 Window는 탐지를 늦춥니다. 핵심 API는 짧은 Interval과 2~3회 연속 실패, 정적 페이지는 조금 완화된 조건처럼 중요도별로 다르게 설정합니다.

Check 자체의 장애와 대상 장애를 구분해야 합니다. Lambda Error, EventBridge Invocation 실패, CloudWatch Metric 미발행을 별도 Alert로 둡니다.

---

## 10. SLO 기반 Alert

CPU 80% 같은 원인 후보보다 사용자 영향에 가까운 SLI를 먼저 호출하는 것이 좋습니다.

- Availability: 성공 요청 비율
- Latency: 기준 시간 안에 완료된 요청 비율
- Correctness: 기대 내용이나 업무 결과 일치

Error Budget Burn Rate Alert는 빠른 대규모 장애와 느린 지속 열화를 다른 Window로 감지합니다. Synthetic Check는 Traffic이 없는 시간에도 Availability를 측정하지만 실제 사용자 요청을 대표하지 못할 수 있으므로 서버 측 Request SLI와 함께 봅니다.

---

## 11. Runbook 구성

Alert마다 다음 순서를 제공합니다.

1. 사용자 영향과 영향을 받는 환경을 확인합니다.
2. Synthetic 단계 중 DNS, TLS, HTTP 어디서 실패했는지 봅니다.
3. 최근 배포·인프라 변경을 확인합니다.
4. 내부 Metric, Log, Trace로 원인을 좁힙니다.
5. Traffic 차단, Rollback, Scale-out 등 안전한 완화를 수행합니다.
6. 복구 후 Synthetic과 실제 SLI가 모두 정상인지 확인합니다.

Runbook Link가 오래되면 Alert의 가치가 떨어집니다. Game Day나 장애 회고에서 실제로 실행해 갱신합니다.

---

## 12. 검증과 운영 점검표

Alert는 생성만 확인하지 말고 전달 전체를 시험합니다. Test Alert를 Firing하고 Alertmanager Route, API Gateway·Lambda Relay, Teams Card, Resolved Notification까지 확인합니다. Synthetic 대상에 의도적 실패를 만들어 탐지 시간도 측정합니다.

- [ ] 모든 호출 Alert에 Owner와 Runbook이 있는가
- [ ] 고 Cardinality 값이 Alert Label에 없는가
- [ ] Notification 실패 자체를 감시하는가
- [ ] Silence에 만료 시간과 사유가 있는가
- [ ] 외부 Check가 DNS·TLS·CDN 경로를 포함하는가
- [ ] Check 미실행과 대상 실패를 구분하는가
- [ ] 실제 SLO와 Synthetic 결과를 함께 보는가
- [ ] 전달 End-to-End Test를 정기 수행하는가

---

## 13. 배포 사례 적용 진단과 개선 과제

Teams Relay와 CloudFront Synthetic Lambda가 구성되어 있지만 Alert 전달 경로 자체의 실패, Check 미실행, Tokenized Webhook URL 노출을 별도로 감시해야 합니다. 개별 Resource Alert가 SLO·Owner·Runbook과 모두 연결됐는지도 지속 검증 대상입니다.

Relay Lambda Error와 Notification Failure, EventBridge Missed Invocation, Synthetic Metric Absence를 독립 Alert로 만듭니다. Webhook Token을 Secret으로 취급해 Log·Output에서 가리고 정기 회전합니다. Alert Rule에는 Owner와 Runbook Label을 Policy로 강제합니다.

완료 기준은 Test Firing부터 Teams의 Resolved Card까지 정기 Probe가 성공하고, Relay를 고장 내도 독립 경로로 감지하며, 외부 DNS·TLS·CDN 장애의 탐지 시간이 SLO 안에 드는 상태입니다.

---

# Reference

- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Amazon EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [[Prometheus Operator와 ServiceMonitor]]
- [[CloudFront S3 정적 프론트엔드]]
