---
id: Istio Ambient Mesh와 Kiali
started: 2026-06-02
tags:
  - ✅DONE
  - Infra
  - Istio
  - Service-Mesh
group:
  - "[[Architecture]]"
---
# Istio Ambient Mesh와 Kiali

## 1. 개요 (Overview)
**Istio Ambient Mesh**는 각 Pod에 Sidecar Proxy를 주입하지 않고 Node 단위 `ztunnel`과 선택적 Waypoint Proxy로 Service Mesh 기능을 제공합니다. **Kiali**는 Istio Traffic, Topology, Configuration과 Telemetry를 시각화합니다.

---

## 2. Ambient Data Plane

```text
Pod A
  -> ztunnel (L4 mTLS)
  -> Network
  -> ztunnel
  -> Pod B

Optional L7 Policy
  -> Waypoint Proxy
```

- **ztunnel**: L4 mTLS, Identity, 기본 Telemetry
- **Waypoint**: HTTP Routing, L7 Authorization, 확장 정책
- **istiod**: Control Plane과 인증서·설정 배포

---

## 3. Sidecar와 차이

| 항목 | Sidecar Mode | Ambient Mode |
|---|---|---|
| Proxy 위치 | Pod마다 Envoy | Node ztunnel + 선택적 Waypoint |
| Resource 비용 | Pod 수에 비례 | Node와 Waypoint 수에 비례 |
| 주입 | Pod 재시작 필요 | Namespace Label로 참여 |
| L7 기능 | Sidecar에 기본 포함 | Waypoint 필요 |

Ambient가 모든 Sidecar 기능을 자동으로 대체한다고 가정하지 않고 필요한 L7 정책과 지원 범위를 확인합니다.

---

## 4. 실무 사례 적용 관점
이 사례의 환경 Namespace는 `istio.io/dataplane-mode=ambient` Label을 사용합니다. Terraform이 Istio Base, CNI, ztunnel, istiod와 Ingress Gateway를 설치합니다. 외부 RDS·Redis 같은 Endpoint는 ServiceEntry로 Mesh Routing에 연결합니다.

Kiali는 Prometheus Telemetry를 사용하여 Service Graph와 오류율을 보여줍니다. Kiali 화면은 원인 그 자체가 아니라 Trace·Metric·Log로 들어가는 탐색 도구입니다.

---

## 5. 운영 주의사항
- mTLS 모드를 점진적으로 전환하고 비참여 Workload 통신을 검증합니다.
- Namespace Label 변경 전 Network 경로와 DNS를 확인합니다.
- Egress와 외부 ServiceEntry의 소유권을 명확히 합니다.
- Kiali 접근은 Internal ALB와 인증으로 제한합니다.
- Istio Version Upgrade 시 CRD, Control Plane, Data Plane 순서를 따릅니다.

---

## 6. Identity와 mTLS 동작
Istio는 Kubernetes Service Account를 Workload Identity의 기반으로 사용합니다. istiod가 Workload에 짧은 수명의 인증서를 발급하고, ztunnel은 이 인증서를 사용하여 HBONE 기반 Tunnel을 구성합니다.

```text
ServiceAccount A
  -> SPIFFE Identity A
  -> ztunnel A
  == mTLS Tunnel ==
  -> ztunnel B
  -> SPIFFE Identity B 검증
  -> ServiceAccount B
```

Network 위치나 Pod IP가 아니라 Identity를 기준으로 통신을 인증할 수 있습니다. 단, mTLS는 상대가 누구인지 확인할 뿐 "누가 누구를 호출할 수 있는가"를 자동으로 결정하지는 않습니다. `AuthorizationPolicy`로 허용 관계를 정의해야 합니다.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-gateway
spec:
  selector:
    matchLabels:
      app: core-app
  rules:
    - from:
        - source:
            principals:
              - cluster.local/ns/production/sa/core-gateway
```

## 7. Waypoint가 필요한 경우
ztunnel은 TCP 수준의 보안과 Telemetry에 집중합니다. 다음 요구가 있으면 L7 처리를 위한 Waypoint를 검토합니다.

- HTTP Method·Path 기준 Authorization
- Header 기반 Routing
- Request-level Telemetry
- Retry, Timeout, Fault Injection 같은 L7 정책

모든 Namespace에 Waypoint를 배치하면 Sidecar를 줄인 이점이 다시 Resource 비용으로 돌아올 수 있습니다. L7 정책이 필요한 Service 경계에만 선택적으로 둡니다.

## 8. 외부 서비스와 Egress
RDS, ElastiCache, 외부 API처럼 Mesh 밖에 있는 대상은 DNS 이름과 Port를 명시적으로 관리합니다. `ServiceEntry`는 외부 대상을 Service Registry에 추가하지만 그 자체로 Network 연결이나 AWS Security Group을 열어주지는 않습니다.

```text
Application
  -> Istio ServiceEntry/Policy
  -> Kubernetes/VPC Network
  -> Security Group/NACL
  -> External Service
```

장애 분석 시 Mesh 설정, DNS, Security Group, Route를 계층별로 나누어 확인합니다.

## 9. 장애 시나리오와 진단

### ztunnel 장애
Node의 ztunnel Pod 상태와 Log, CNI 구성을 확인합니다. 특정 Node의 Workload만 통신하지 못하면 ztunnel과 Node Network를 우선 의심합니다.

### 인증서·mTLS 오류
Workload Identity, Service Account, istiod 연결과 Clock Skew를 확인합니다. `STRICT` 전환 직후 Legacy Workload가 실패한다면 Mesh 참여 여부를 점검합니다.

### Kiali Graph에 Traffic이 없음
Kiali 자체보다 Prometheus Scrape, Istio Telemetry Label, 조회 시간 범위를 먼저 확인합니다. Graph가 없다고 실제 통신이 없다는 뜻은 아닙니다.

### Upgrade 후 Policy 변화
Control Plane과 Data Plane Version Skew 지원 범위를 확인하고, Dev Namespace에서 먼저 Upgrade합니다. CRD를 제거하거나 Downgrade하기 전에 저장된 Custom Resource 호환성을 확인합니다.

## 10. 검증 체크리스트
- Namespace Label 적용 전후의 Pod 통신을 비교합니다.
- 허용·거부 AuthorizationPolicy Test를 자동화합니다.
- mTLS 상태와 Peer Identity를 확인합니다.
- 외부 RDS·Redis·API 통신을 별도 Smoke Test로 검증합니다.
- ztunnel 한 개를 재시작해 Node Traffic 회복을 확인합니다.
- Kiali, Prometheus, Trace의 Service 이름이 일관되는지 확인합니다.

---

## 13. 배포 사례 적용 진단과 개선 과제

Ambient Mode의 ztunnel·Waypoint·Kiali 기반은 있으나 Mesh 참여만으로 Namespace 간 접근이 제한되지는 않습니다. AuthorizationPolicy와 Egress 정책이 명시적으로 보이지 않으면 mTLS는 암호화만 제공하고 권한 경계는 열려 있을 수 있습니다.

Service Account 기반 Default-deny AuthorizationPolicy를 Namespace별로 적용하고 필요한 Caller→Callee만 허용합니다. 외부 Egress, DNS, Telemetry 예외를 Inventory화하고 ztunnel·Waypoint 장애와 Certificate Rotation을 Test합니다.

완료 기준은 허용되지 않은 Service Identity 호출이 차단되고 mTLS Strict 상태와 Policy Deny가 Dashboard에 보이며, Mesh Component Upgrade 중 핵심 Traffic이 정의된 방식으로 유지되는 상태입니다.

---

# Reference
- [Istio Ambient Mode](https://istio.io/latest/docs/ambient/)
- [Kiali Documentation](https://kiali.io/docs/)
- [[Istio 트래픽 모니터링 및 Sidecar]]
