---
id: Kubernetes Policy as Code
started: 2026-07-09
tags:
  - ✅DONE
  - K8S
  - Policy-as-Code
  - Security
group:
  - "[[Infra K8S]]"
---
# Kubernetes Policy-as-Code

## 1. 개요

Policy-as-Code는 보안·신뢰성·비용 규칙을 사람이 기억하는 Checklist가 아니라 Version 관리되고 자동 Test되는 정책으로 표현합니다.

```text
Manifest 작성
  -> CI 정적 Policy Test
  -> Kubernetes Admission
  -> Audit / Warn / Deny
  -> 위반 Metric과 예외 관리
```

PDB, Resource Request, Image Digest, Security Context 같은 규칙을 모든 Helm Chart Reviewer가 매번 발견하리라 기대하지 않습니다.

---

## 2. Admission Control

Admission Controller는 인증·인가 후 Resource가 etcd에 저장되기 전에 요청을 검사합니다.

- Mutating: Default를 추가하거나 Resource를 변경합니다.
- Validating: 요청을 허용하거나 거부합니다.
- Built-in Policy: ResourceQuota, LimitRange, Pod Security 등
- Dynamic Policy: Webhook, Kyverno, OPA Gatekeeper
- In-process Policy: ValidatingAdmissionPolicy와 CEL

정책 엔진 장애가 Kubernetes API 쓰기를 막을 수 있으므로 가용성과 Failure Policy가 중요합니다.

---

## 3. ValidatingAdmissionPolicy

Kubernetes의 ValidatingAdmissionPolicy는 외부 Webhook 호출 없이 API Server 내부에서 CEL 규칙을 평가합니다. 단순 검증에 적합합니다.

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-resource-requests.example.com
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: >-
        object.spec.template.spec.containers.all(container,
          has(container.resources.requests.cpu) &&
          has(container.resources.requests.memory))
      message: CPU and memory requests are required
```

Binding이 Namespace 범위와 `Deny`, `Warn`, `Audit` 행동을 결정합니다.

---

## 4. Kyverno와 Gatekeeper

### Kyverno

Kubernetes Resource 형식으로 Validate, Mutate, Generate와 Image 검증을 표현합니다. YAML 중심이라 Platform 팀과 Application 팀이 읽기 쉽습니다.

### OPA Gatekeeper

Rego 기반의 범용 Policy Engine입니다. ConstraintTemplate과 Constraint로 규칙과 Parameter를 분리합니다.

### 선택 기준

- 단순 CEL 검증: ValidatingAdmissionPolicy
- Kubernetes 중심 Mutation·Generation·Image 정책: Kyverno
- 조직 전체의 복잡한 범용 Policy: OPA/Gatekeeper

도구 수를 늘리기 전에 내장 Policy와 CEL로 해결 가능한지 봅니다.

---

## 5. 우선 적용 정책

### 보안

- Privileged, Host Network·PID·Path 금지
- Root 실행과 Privilege Escalation 금지
- Read-only Root Filesystem 권장
- 허용 Registry와 서명된 Image만 사용
- Secret을 Environment 값으로 직접 작성하지 않음

### 신뢰성

- CPU·Memory Request 필수
- Liveness·Readiness·Startup Probe 기준
- Production Replica와 PDB
- Image `latest` Tag 금지, Digest 권장
- 필수 Owner·Service·Environment Label

### 비용과 운영

- Resource 상한
- Load Balancer와 Public Service 승인
- StorageClass와 PVC 크기 제한
- TTL 없는 임시 Job 방지

---

## 6. Audit에서 Deny로 전환

기존 Cluster에 바로 Deny를 적용하면 현재 Workload가 대량으로 실패할 수 있습니다.

```text
Inventory
  -> Audit
  -> Warn
  -> 신규 Resource만 Deny
  -> 기존 위반 제거
  -> 전체 Deny
```

위반 수, Owner, 예외 만료일을 Dashboard로 관리합니다. Policy가 무시되는 Namespace를 영구 예외로 만들지 않습니다.

---

## 7. Policy Test

정책도 코드이므로 Positive·Negative Test가 필요합니다.

- 허용해야 하는 최소 Manifest
- 각 위반을 하나씩 포함한 Manifest
- Namespace·Environment별 예외
- Update와 Delete 동작
- Helm Rendered Manifest 전체
- Kubernetes Version Upgrade 후 API 호환

CI에서 먼저 실행하면 개발자가 Cluster Admission Error를 기다리지 않아도 됩니다.

---

## 8. Failure Policy

`Fail`은 Policy Engine 오류 시 요청을 거부해 안전하지만 Control Plane 작업을 막을 수 있습니다. `Ignore`는 가용성은 높지만 공격이나 잘못된 배포를 통과시킬 수 있습니다.

Critical Security Policy는 Fail-closed를 우선하되 Webhook Replica, PDB, Timeout과 Monitoring을 강화합니다. 위험이 낮은 권고 정책은 Audit·Warn으로 운영할 수 있습니다.

Lease, Node, System Namespace처럼 Control Plane에 민감한 Resource는 Policy 범위를 매우 신중히 정합니다.

---

## 9. GitOps와 Policy 소유권

- Policy 정의는 Platform 저장소가 소유합니다.
- Application 저장소는 CI에서 같은 Policy Bundle을 Test합니다.
- Argo CD Project와 Admission Policy의 책임을 구분합니다.
- Policy 변경도 Pull Request, Review와 Rollback을 거칩니다.
- Cluster의 수동 Policy 변경은 Drift로 탐지합니다.

Policy Version과 Application Deployment 결과를 연결해야 갑작스러운 배포 실패 원인을 찾을 수 있습니다.

---

## 10. 사례의 부족한 점과 해결

현재 Helm Values에 Probe와 Resource가 있지만 PDB·NetworkPolicy·Quota가 일관되게 존재하지 않습니다. 문서와 Review만으로 강제하는 단계에 머뭅니다.

1. 필수 Label·Resource·Image Policy를 Audit합니다.
2. 기존 위반을 Service Owner별로 정리합니다.
3. Production 신규 Resource부터 Deny합니다.
4. PDB와 Security Context를 Library Chart에 기본화합니다.
5. 서명 Image 검증을 Supply-chain 정책과 연결합니다.
6. 예외에 Owner·사유·만료 시간을 요구합니다.

---

## 11. Anti-pattern

- 모든 규칙을 하나의 거대한 Policy로 만듭니다.
- 이유와 해결 방법 없는 Error Message를 반환합니다.
- Platform System Namespace까지 무차별 적용합니다.
- Webhook 장애와 Certificate 만료를 감시하지 않습니다.
- 예외를 영구 Namespace Label 하나로 처리합니다.
- CI Policy Version과 Cluster Version이 다릅니다.

---

## 12. 완료 기준

- [ ] 가장 중요한 보안·신뢰성 규칙이 CI와 Admission에서 동일하게 실행됩니다.
- [ ] Policy마다 Owner, 목적과 해결 가능한 Error Message가 있습니다.
- [ ] Audit→Warn→Deny 전환 계획과 위반 추세가 있습니다.
- [ ] 예외에 사유와 자동 만료가 있습니다.
- [ ] Policy Engine 장애가 Control Plane을 마비시키지 않게 Test했습니다.
- [ ] Kubernetes Upgrade 전에 Policy Compatibility를 검증합니다.
- [ ] 수동 변경과 Policy Drift를 GitOps가 탐지합니다.

---

# Reference

- [Kubernetes Policies](https://kubernetes.io/docs/concepts/policy/)
- [Validating Admission Policy](https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/)
- [Kyverno Documentation](https://kyverno.io/docs/)
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/)
- [[Kubernetes Workload 신뢰성]]
- [[Helm Application Chart 설계]]
