---
id: Argo Rollouts Blue-Green 배포
started: 2026-06-29
tags:
  - ✅DONE
  - K8S
  - Argo-Rollouts
  - Deployment
group:
  - "[[Infra K8S]]"
---
# Argo Rollouts Blue-Green 배포

## 1. 개요 (Overview)
**Argo Rollouts**는 Kubernetes Deployment를 확장하여 Blue-Green과 Canary 같은 Progressive Delivery를 제공합니다. 이 사례는 Active Service와 Preview Service를 분리하는 Blue-Green 전략을 사용합니다.

---

## 2. 구조

```text
Active Service  -> Stable ReplicaSet
Preview Service -> New ReplicaSet

검증 성공
  -> Active Service Selector를 New ReplicaSet으로 전환
  -> 이전 ReplicaSet 지연 종료
```

Service Selector 전환은 빠르지만 기존 연결과 ALB Target Deregistration 시간을 고려해야 합니다.

---

## 3. Rollout 정의

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    blueGreen:
      activeService: app
      previewService: app-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 120
```

`autoPromotionEnabled`를 끄면 Preview 환경의 Smoke Test와 Metric 확인 후 명시적으로 승격할 수 있습니다.

---

## 4. 실무 사례 적용 관점
사례의 Helm Chart는 서비스별 Rollout, Active Service, Preview Service를 생성합니다. `minReadySeconds`, `progressDeadlineSeconds`, Probe와 종료 유예 시간을 함께 설정합니다.

현재 자동 승격을 사용하더라도 Preview Service가 있으므로 향후 Analysis Template이나 수동 승인으로 발전시킬 수 있습니다.

---

## 5. 안전한 전환 조건
- Startup·Readiness Probe가 실제 트래픽 준비 상태를 반영합니다.
- 새 Version의 DB Migration이 이전 Version과 호환됩니다.
- In-flight 요청을 위한 `preStop`과 Graceful Shutdown을 둡니다.
- ALB Deregistration Delay와 `terminationGracePeriodSeconds`를 맞춥니다.
- Error Rate, P95 Latency, Saturation을 승격 조건으로 사용합니다.

---

## 6. Blue-Green과 Canary

| 전략 | 장점 | 단점 |
|---|---|---|
| Blue-Green | 전환·Rollback이 빠르고 단순 | 새 Version에 전체 트래픽이 한 번에 이동 |
| Canary | 소량 트래픽으로 위험 제한 | Traffic Routing과 분석이 복잡 |

DB Schema나 외부 Side Effect는 Pod Version Rollback만으로 되돌릴 수 없으므로 별도의 호환성 전략이 필요합니다.

---

## 7. Blue-Green 상태 전이

```text
Stable ReplicaSet Running
  -> New ReplicaSet 생성
  -> Preview Service 연결
  -> Readiness + minReadySeconds
  -> Promotion
  -> Active Service Selector 전환
  -> scaleDownDelay
  -> Old ReplicaSet 축소
```

`minReadySeconds`는 일시적으로 Ready가 된 Pod를 즉시 안정 상태로 판단하지 않게 합니다. `progressDeadlineSeconds`는 배포가 무한 대기하지 않도록 전체 상한을 둡니다.

## 8. Preview 검증
Preview Service는 실제 Production Traffic을 받기 전 새 Version을 검증하는 경로입니다.

- Actuator Health와 주요 Dependency 연결
- OpenAPI와 간단한 Read API
- DB Schema 호환성
- 핵심 Business Smoke Test
- Metric·Log·Trace 수집
- ConfigMap과 Secret Version

Preview Test가 실제 외부 Side Effect를 만들지 않도록 Test Account·Dry-run·읽기 전용 Scenario를 사용합니다.

## 9. Analysis Template
Argo Rollouts는 Prometheus Query로 승격 조건을 자동 평가할 수 있습니다.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
spec:
  metrics:
    - name: success-rate
      successCondition: result[0] >= 0.99
      provider:
        prometheus:
          query: |
            sum(rate(http_server_requests_seconds_count{status!~"5.."}[5m]))
            /
            sum(rate(http_server_requests_seconds_count[5m]))
```

Traffic이 없는 Preview에서는 Production Success Rate를 계산할 수 없습니다. Synthetic Request를 보내거나 Promotion 후 짧은 검증 창을 별도로 설계합니다.

## 10. Database 호환성
Blue-Green에서는 Old와 New Version이 동시에 같은 DB를 사용합니다. Migration은 다음 순서의 Expand-and-Contract를 따릅니다.

1. 새 Column·Table을 이전 Version과 호환되게 추가합니다.
2. Old·New 모두 동작 가능한 상태에서 New Version을 배포합니다.
3. Data Backfill과 사용 전환을 완료합니다.
4. 다음 Release에서 Old Schema를 제거합니다.

한 Release에서 Column Rename·삭제와 코드 전환을 동시에 하면 Rollback이 불가능해집니다.

## 11. 종료와 연결 Drain
Active Service 전환 직후에도 ALB, Client Keep-alive와 In-flight 요청이 Old Pod로 갈 수 있습니다.

```text
scaleDownDelaySeconds
  >= Endpoint/ALB 전파 시간 + 최대 정상 요청 시간
```

`scaleDownDelaySeconds: 0`은 빠르지만 실제 Traffic 환경에서는 연결 실패 위험이 있습니다. ALB Deregistration Delay와 Application Graceful Shutdown을 측정해 설정합니다.

## 12. Abort와 Rollback
- Promotion 전 Abort: Preview ReplicaSet을 중단하고 Active는 유지
- Promotion 후 Abort: Active Service를 Stable ReplicaSet으로 되돌림
- Git Rollback: Desired Image Tag 자체를 이전 Version으로 복구

외부 Event 발행, DB 변경, Cache Format은 Traffic 전환만으로 되돌아가지 않습니다. Forward Recovery 전략이 필요합니다.

## 13. 운영 명령과 확인 항목

```sh
kubectl argo rollouts get rollout core-app -n production --watch
kubectl argo rollouts promote core-app -n production
kubectl argo rollouts abort core-app -n production
```

승격 전 Image Digest, Replica Health, Preview Test, Error Rate, Saturation과 Migration 상태를 확인합니다.

---

## 14. 배포 사례 적용 진단과 개선 과제

Active·Preview Service와 Blue-Green Rollout은 적용돼 있지만 자동 Promotion이 Application Health만 보고 진행되면 기능 회귀와 DB 비호환을 놓칠 수 있습니다. Preview가 추가로 소비하는 Node·DB Connection도 평상시 Capacity 산정에서 빠질 수 있습니다.

Pre-promotion Analysis에 Synthetic, 핵심 API, Error Rate·P99, Migration 호환 검사를 넣고 Manual Approval 조건을 Prod에 명시합니다. Scale-down Delay는 ALB Deregistration과 긴 요청 시간을 합산해 정하며 Abort 절차를 Game Day로 검증합니다.

완료 기준은 실패 Analysis가 Traffic 전환을 막고 전환 후 SLO 악화가 자동 Abort되며, 이전 Replica가 종료되기 전 Connection Drain이 끝나고 검증된 이전 Digest로 Rollback 가능한 상태입니다.

---

# Reference
- [[k6 부하 테스트와 성능 검증]]
- [Argo Rollouts BlueGreen](https://argo-rollouts.readthedocs.io/en/stable/features/bluegreen/)
- [[Argo CD와 GitOps]]
- [[Helm Application Chart 설계]]
