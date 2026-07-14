---
id: Pod Security Standards와 Security Context
started: 2026-07-11
tags:
  - ✅DONE
  - K8S
  - Security
  - Pod-Security
group:
  - "[[Infra K8S]]"
---
# Pod Security Standards와 Security Context

## 1. Container는 보안 경계가 아니다

Container Process도 Node의 Linux Kernel을 공유한다. Root 실행, 특권 Mode, Host Path와 위험 Capability가 허용되면 Application 침해가 Node 침해로 확대될 수 있다.

Pod Security Standards는 Pod가 지켜야 할 보안 수준을 Privileged, Baseline, Restricted 세 Profile로 정의한다. Pod Security Admission은 Namespace Label을 기준으로 이 표준을 검사한다.

## 2. 세 가지 Profile

| Profile | 의미 | 주 사용처 |
|---|---|---|
| Privileged | 거의 제한 없음 | 신뢰된 System Workload의 예외 |
| Baseline | 알려진 권한 상승을 막는 최소선 | 일반 Workload 전환 단계 |
| Restricted | 현재 Hardening 모범 사례 | Application 기본 목표 |

Restricted는 Non-root 실행, Privilege Escalation 금지, Seccomp, Capability 제거 등을 요구한다. 모든 System Daemon이 Restricted를 만족하는 것은 아니므로 인프라 Namespace와 Application Namespace를 구분한다.

## 3. Namespace Label로 적용하기

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: application
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

`enforce`는 위반 Pod를 거부하고 `audit`는 Audit Annotation, `warn`은 사용자 경고를 남긴다. 기존 Cluster에는 Audit와 Warn으로 영향 범위를 본 뒤 Enforce로 전환하는 편이 안전하다.

`latest`는 Upgrade 때 기준이 바뀔 수 있다. 예측 가능성이 중요하면 Cluster Version에 맞춰 Profile Version을 고정하고 Upgrade 과정에서 갱신한다.

## 4. Security Context

```yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

`runAsNonRoot`는 Image의 User 설정과 일치해야 한다. `readOnlyRootFilesystem`를 켜면 `/tmp`, Log, Cache처럼 쓰기가 필요한 경로는 `emptyDir` 등으로 명시한다. 보안 옵션은 Application의 File System 가정을 드러내기도 한다.

## 5. Linux Capability

Root 권한을 하나의 Boolean으로 생각하면 과도한 권한을 주기 쉽다. Linux Capability는 Network 설정, 소유권 변경 같은 권한을 나눈다. 기본 Capability도 모두 제거하고 정말 필요한 항목만 추가하는 방식이 좋다.

1024 미만 Port를 열기 위해 Root로 실행하기보다 높은 Container Port를 사용하거나 필요한 경우 `NET_BIND_SERVICE`만 검토한다.

## 6. ServiceAccount Token과 Host 접근

AWS API나 Kubernetes API를 사용하지 않는 Pod는 `automountServiceAccountToken: false`로 Token 자동 Mount를 막는다. `hostNetwork`, `hostPID`, `hostIPC`, `hostPath`는 Node 경계를 약화하므로 일반 Application에서 금지한다.

DaemonSet처럼 예외가 필요한 Workload는 별도 Namespace, 전용 ServiceAccount와 제한된 Node에 배치한다. 예외를 전체 Cluster Profile 완화로 해결하지 않는다.

## 7. PodSecurityPolicy와 혼동하지 않기

PodSecurityPolicy는 Kubernetes 1.25에서 제거되었다. 새로운 설계는 Pod Security Admission과 필요시 Kyverno·Gatekeeper 같은 Admission Policy를 사용한다. PSS는 표준 Profile이고, Image Registry나 필수 Label처럼 조직 고유 규칙은 별도 Policy Engine이 담당한다.

## 8. 실무에서 빠지기 쉬운 설계

Security Context 일부만 Helm Values에 있고 Namespace의 Enforce가 없다면 새 Chart나 임시 Pod가 제한 없이 배포될 수 있다. 반대로 Restricted를 갑자기 적용하면 Monitoring Agent와 CSI Driver까지 거부되어 Cluster 운영이 멈출 수 있다.

Application Namespace는 Restricted를 기본으로 하고, System Namespace의 예외는 Workload별 이유와 범위를 기록한다. CI에서 Rendered Manifest를 검사하고 Staging의 Warn·Audit 결과를 본 뒤 Admission에서 최종 거부하는 흐름이 안전하다.

## 9. 기억할 점

Security Context는 YAML 장식이 아니라 Process가 Kernel과 Node에 행사할 수 있는 권한을 줄이는 장치다. 안전한 기본값을 Namespace 수준에서 강제하고 예외를 좁게 격리할 때 새 Workload에도 보안 수준이 자동 적용된다.

# Reference
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [Configure a Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
