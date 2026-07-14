---
id: Helm Application Chart 설계
started: 2026-07-03
tags:
  - ✅DONE
  - K8S
  - Helm
  - Deployment
group:
  - "[[Infra K8S]]"
---
# Helm Application Chart 설계

## 1. 개요 (Overview)
**Helm Chart**는 Kubernetes Resource Template과 환경별 값을 분리합니다. Application Chart는 Resource를 생성하는 도구를 넘어 Image, Probe, Resource, Scheduling, Observability와 배포 전략의 계약입니다.

---

## 2. 사례 Chart 구성

```text
app/
  Chart.yaml
  values.yaml
  config/
  templates/
    rollout.yaml
    service.yaml
    service-preview.yaml
    ingress.yaml
    configmap.yaml
    serviceaccount.yaml
    servicemonitor.yaml
```

Deployment 대신 Argo Rollout을 사용하고 Active·Preview Service를 분리합니다.

---

## 3. Values 계약

| 값 | 목적 |
|---|---|
| `image.repository/tag` | 배포 Artifact 선택 |
| `resources` | Scheduling과 Resource Isolation |
| `startup/liveness/readinessProbe` | Lifecycle 판단 |
| `nodeSelector/affinity/tolerations` | 환경·Node Placement |
| `serviceMonitor` | Prometheus 수집 |
| `rollout.blueGreen` | Progressive Delivery 정책 |
| `env/configMap` | Runtime Configuration |

환경별 차이는 Values로 표현하고 Template 자체의 복제를 최소화하는 것이 이상적입니다. 환경별 Chart를 복제한다면 변경 동기화 검증이 필요합니다.

---

## 4. ConfigMap Rollout

```yaml
metadata:
  annotations:
    checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

ConfigMap 내용이 바뀌면 Pod Template Annotation도 바뀌어 새 ReplicaSet이 생성됩니다. Secret 값은 ConfigMap이나 Git에 저장하지 않습니다.

---

## 5. Template 검증

```sh
helm lint ./chart
helm template app ./chart -f values.yaml
```

CI에서 Render 결과, Kubernetes Schema, 금지된 Security Context와 필수 Label을 검사합니다. 실제 Cluster에서는 Helm Test와 Smoke Test로 Service 연결을 확인합니다.

---

## 6. 설계 원칙
- `latest`가 아닌 불변 Image Tag를 사용합니다.
- Resource Request를 반드시 설정합니다.
- Probe의 목적과 Endpoint를 구분합니다.
- `automountServiceAccountToken`은 Kubernetes API가 필요 없으면 끕니다.
- Secret과 환경별 자격증명을 Values에 Commit하지 않습니다.
- Template Helper 이름과 Label을 일관되게 유지합니다.

---

## 7. Template 함수와 Scope
Helm은 Go Template을 사용합니다. `.` Scope가 `range`, `with` 안에서 바뀌므로 Root는 `$`로 접근합니다.

```yaml
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
```

Whitespace 제어가 잘못되면 유효하지 않은 YAML이 생성될 수 있으므로 Render 결과를 기준으로 Review합니다.

## 8. Helper와 Label
`_helpers.tpl`에 이름·Selector·공통 Label을 정의합니다. Selector Label은 배포 후 변경하면 기존 Workload와 연결이 깨질 수 있으므로 안정적으로 유지합니다.

권장 Label은 `app.kubernetes.io/name`, `instance`, `version`, `component`, `managed-by`입니다.

## 9. Values Schema
`values.schema.json`으로 필수 값, Type, Enum과 Pattern을 검증할 수 있습니다. Image Repository 누락이나 잘못된 Resource 형식을 Install 전에 발견합니다.

Environment Values가 많아질수록 문서 대신 Schema와 Default를 계약으로 관리하는 것이 효과적입니다.

## 10. Secret 분리
ConfigMap에는 비민감 설정만 둡니다. Secret은 External Secret, SOPS, Sealed Secret 또는 사전 Provisioning을 사용합니다.

Checksum Annotation에 Secret 내용을 직접 Render하면 Manifest Diff나 Annotation에 Hash만 남더라도 Secret Source 접근 경계를 점검해야 합니다.

## 11. Library Chart와 중복
app, gateway, metrics Chart가 동일 Template을 복사하면 수정 누락이 생깁니다. Library Chart로 공통 Template을 추출할 수 있지만 지나친 범용화는 Values 계약을 복잡하게 합니다.

먼저 공통 불변 요소와 서비스별 변형점을 식별한 뒤 추출합니다.

## 12. Upgrade와 Rollback
Helm Revision Rollback과 GitOps Rollback은 다릅니다. Argo CD 환경에서는 Git Desired State가 우선이므로 CLI Rollback 후 Git도 일치시켜야 합니다.

CRD는 Helm Rollback만으로 안전하게 이전 Version으로 돌아가지 않을 수 있습니다.

## 13. Test Matrix
- 모든 환경 Values Render
- Optional 기능 On·Off
- Empty List와 Null
- 긴 이름의 63자 제한
- Helm Upgrade Diff
- Kubernetes Version별 Schema
- ServiceMonitor·Ingress Selector 연결

## 14. Chart Review 체크리스트
- Namespace가 Template과 Argo Destination에서 일치하는가?
- Active·Preview Service Selector가 올바른가?
- Config 변경이 Rollout을 유발하는가?
- Probe Port Name이 Container Port와 일치하는가?
- Resource와 Security Context 기본값이 안전한가?
- Secret이 Render 결과에 포함되지 않는가?

---

## 15. 배포 사례 적용 진단과 개선 과제

환경·서비스별 Chart가 유사한 Rollout·Service·Monitor Template을 반복합니다. 이 구조는 한 환경에만 Probe, Label, Security Context 수정이 빠지는 Configuration Drift를 만들기 쉽습니다. Values에 Application Secret을 넣는 방식도 제거해야 합니다.

공통 Helper와 JSON Schema로 필수 Label, Resource, Probe, Image Digest, Secret Reference를 검증하고 중복이 큰 부분은 Versioned Library Chart로 승격합니다. `helm lint/template`, kubeconform, Policy Test를 Dev·QA·Prod Matrix로 실행합니다.

완료 기준은 같은 기능 변경이 환경마다 복사되지 않고, 잘못된 Values와 평문 Secret이 CI에서 실패하며, Rendered Manifest Diff로 실제 변경 Resource를 Review할 수 있는 상태입니다.

---

# Reference
- [Helm Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [[3. Helm Chart 설치]]
- [[Argo Rollouts Blue-Green 배포]]
