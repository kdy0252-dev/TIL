---
id: Kubernetes Gateway API
started: 2026-07-07
tags:
  - ✅DONE
  - K8S
  - Gateway-API
group:
  - "[[Infra K8S]]"
---
# Kubernetes Gateway API

## 1. 개요

Gateway API는 Ingress보다 표현력이 풍부하고 Infrastructure Owner와 Application Owner의 책임을 Resource로 분리합니다.

```text
GatewayClass -> Gateway -> HTTPRoute / GRPCRoute / TCPRoute
```

---

## 2. 역할 분리

- Infrastructure Provider: GatewayClass 구현
- Cluster Operator: Gateway, Listener, TLS와 허용 Namespace
- Application Team: Route, Match, Filter와 Backend

한 팀이 Load Balancer Annotation 전체를 소유하는 문제를 줄입니다.

---

## 3. Listener와 Route Attachment

Gateway Listener는 Port, Protocol, Hostname, TLS와 연결 가능한 Namespace를 정의합니다. Route의 `parentRefs`와 Listener `allowedRoutes`가 모두 맞아야 연결됩니다.

Status Condition에서 Accepted, Programmed, ResolvedRefs를 확인합니다.

---

## 4. HTTPRoute

Host, Path, Header, Method Match와 Weighted Backend, Redirect, Rewrite를 표준 Resource로 표현합니다. 구현체별 지원 Feature를 GatewayClass Status와 Compatibility 문서에서 확인합니다.

---

## 5. ReferenceGrant

다른 Namespace의 Service나 Secret을 참조할 때 대상 Namespace가 `ReferenceGrant`로 명시적으로 허용합니다. Cross-namespace Reference를 기본 거부해 권한 경계를 보호합니다.

---

## 6. Progressive Delivery

Weighted Backend로 Canary Traffic을 분배할 수 있지만 배포 상태와 Analysis·Rollback은 Argo Rollouts 같은 Controller와 조정해야 합니다. 두 Controller가 같은 Traffic Weight를 동시에 소유하지 않게 합니다.

---

## 7. Mesh와 Gateway

Gateway API는 North-South뿐 아니라 구현에 따라 Mesh Route에도 사용할 수 있습니다. Istio Ambient의 Waypoint와 Route 지원 범위를 Version별로 검증합니다.

---

## 8. Ingress Migration

1. 기존 Host·Path·TLS·Annotation Inventory
2. Controller Feature Mapping
3. 별도 Domain으로 Gateway 병행
4. Route Status와 Synthetic Test
5. DNS·Traffic 점진 전환
6. Ingress 제거

Annotation 기능이 표준 Filter로 대응되지 않을 수 있습니다.

---

## 9. Policy와 보안

Gateway 생성 권한과 Route 연결 권한을 RBAC로 분리합니다. Public Gateway에 임의 Namespace가 Route를 붙이지 못하게 `allowedRoutes`와 Policy-as-Code를 적용합니다.

---

## 10. HTTPRoute 예시

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: core-api
spec:
  parentRefs:
    - name: public-gateway
      namespace: platform
  hostnames: ["api.example.com"]
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: core-api
          port: 8080
```

Route가 존재해도 Parent Status가 Accepted인지 확인해야 실제 연결을 보장할 수 있습니다.

---

## 11. 관측성과 장애

- Accepted·Programmed·ResolvedRefs Condition
- Controller Reconcile Error
- Listener TLS Certificate 상태
- Route별 4xx·5xx·Latency
- Backend Health와 ReferenceGrant 거부
- Gateway Data Plane Capacity

Control Plane Resource가 정상이어도 Load Balancer와 Proxy Data Plane이 실패할 수 있어 Synthetic Check를 함께 둡니다.

---

## 12. 적용 판단

현재 Ingress Annotation이 단순하고 한 팀이 모두 관리한다면 Migration 이점이 작을 수 있습니다. 여러 팀이 Listener와 Route를 분리 소유하거나 HTTP·gRPC·TCP 정책을 표준화해야 할 때 가치가 커집니다.

도입 전 Controller가 필요한 Extended Feature와 Istio Ambient 조합을 지원하는지 검증합니다.

---

## 13. 완료 기준

- [ ] GatewayClass·Gateway·Route 소유자가 구분됩니다.
- [ ] Cross-namespace Reference가 명시적으로 승인됩니다.
- [ ] Route Status와 실제 Data Plane을 함께 감시합니다.
- [ ] 기존 Ingress Annotation의 대응표가 있습니다.
- [ ] Canary Controller 간 Traffic 소유권 충돌이 없습니다.

# Reference

- [Kubernetes Gateway API](https://gateway-api.sigs.k8s.io/)
- [[Spring Cloud Gateway 보안 라우팅]]
- [[Argo Rollouts Blue-Green 배포]]
