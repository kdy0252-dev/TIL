---
id: Kubernetes NetworkPolicy와 Namespace 격리
started: 2026-07-08
tags:
  - ✅DONE
  - K8S
  - NetworkPolicy
  - Security
group:
  - "[[Infra K8S]]"
---
# Kubernetes NetworkPolicy와 Namespace 격리

## 1. Cluster 내부는 기본적으로 열린 Network다

Kubernetes Network Model은 Pod가 다른 Pod와 직접 통신할 수 있다고 가정한다. 편리하지만 한 Pod가 침해되면 같은 Cluster의 Database, Monitoring Endpoint와 다른 환경으로 이동할 경로도 넓어진다.

NetworkPolicy는 Pod를 중심으로 허용할 Ingress와 Egress를 선언하는 L3/L4 방화벽 규칙이다. Resource를 만들기만 해서는 안 되고 CNI가 실제 Policy Enforcement를 지원해야 한다.

## 2. 선택된 Pod만 격리된다

Policy가 하나도 선택하지 않는 Pod는 기본적으로 모든 Traffic을 허용한다. `podSelector`로 선택된 Pod는 지정된 방향에서 격리되고, 여러 Policy의 허용 규칙은 합집합으로 계산된다. Policy 순서나 명시적 Deny 우선순위는 없다.

```text
Client Egress가 허용하고 Server Ingress도 허용해야 연결 성공
```

한쪽만 열면 Timeout이 발생한다. 이 양방향 평가가 NetworkPolicy 진단의 핵심이다.

## 3. Default Deny에서 시작하기

Namespace에 빈 Selector와 Ingress·Egress를 지정하면 모든 Pod를 기본 격리할 수 있다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: application
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

그 위에 DNS, Gateway, Database와 관측성 수집기처럼 필요한 흐름만 Allow한다. 처음부터 운영에 적용하면 누락된 의존성 때문에 장애가 날 수 있으므로 Flow 관측과 Staging 검증을 거친다.

## 4. Selector는 신뢰 경계다

`podSelector`와 `namespaceSelector`는 Label을 신원처럼 사용한다. 애플리케이션 사용자가 임의로 보안 Label을 붙일 수 있다면 Policy를 우회할 수 있다. Namespace Label은 플랫폼 관리자가 통제하고 Admission Policy로 예약 Label 변경을 제한한다.

```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: gateway
        podSelector:
          matchLabels:
            app.kubernetes.io/name: ingress-gateway
```

두 Selector를 같은 항목에 쓰면 AND 조건이다. 별도 항목으로 나누면 OR가 되어 의도보다 넓게 열릴 수 있다.

## 5. Egress와 DNS

Default-deny Egress를 적용하면 DNS도 막힌다. CoreDNS의 Namespace, Pod Label, UDP/TCP 53을 허용해야 한다. 외부 API는 IP가 자주 바뀌므로 표준 NetworkPolicy의 `ipBlock`만으로 Domain 단위 제어하기 어렵다. Egress Gateway나 CNI 확장 기능을 검토할 수 있다.

Service ClusterIP를 `ipBlock`에 넣는 것도 구현과 NAT 순서에 따라 기대대로 동작하지 않을 수 있다. 가능하면 목적 Workload의 Namespace와 Pod Selector를 사용한다.

## 6. NetworkPolicy가 하지 못하는 것

표준 Policy는 HTTP Path, 사용자 JWT, TLS 신원이나 SQL 권한을 이해하지 못한다. `/admin`만 차단하거나 특정 ServiceAccount의 요청만 허용하려면 Gateway, Service Mesh 또는 Application Authorization이 필요하다.

```text
NetworkPolicy: 어느 IP·Port로 연결 가능한가
Mesh Policy  : 어떤 Workload Identity가 어떤 Service를 호출하는가
Application  : 사용자가 어떤 업무 동작을 할 수 있는가
```

각 계층은 서로 대체하지 않는다.

## 7. 장애를 읽는 방법

Policy 적용 뒤 Timeout이 발생하면 먼저 Source Pod가 Egress 격리 대상인지, Destination Pod가 Ingress 격리 대상인지 본다. 그 다음 실제 Pod Label, Namespace Label, Port와 Protocol을 확인한다. Service가 아니라 최종 Endpoint Pod를 기준으로 생각해야 한다.

CNI가 Policy를 지원하지 않으면 YAML은 정상 생성되지만 Traffic은 계속 통과한다. 반드시 허용 Test뿐 아니라 차단 Test를 자동화한다.

## 8. 실무에서 빠지기 쉬운 설계

공유 Cluster에서 NetworkPolicy가 없으면 개발·검증·운영 Namespace를 나눠도 Network 경계는 생기지 않는다. Namespace는 이름과 관리 범위일 뿐 자동 방화벽이 아니다.

보완할 때는 Namespace별 Default-deny를 기반으로 Gateway→Application, Application→Database, Application→DNS 같은 실제 Data Flow를 Allow한다. 정책 적용 직후의 연결 성공만 보지 않고, 승인되지 않은 Namespace와 임시 Pod에서 접근이 거부되는지도 지속적으로 검사해야 한다.

## 9. 기억할 점

NetworkPolicy는 서비스 목록이 아니라 허용된 통신 Graph를 코드로 표현하는 기술이다. Default Allow에서 예외를 막는 방식보다 Default Deny 위에 필요한 Edge만 추가할 때 의도가 선명해진다.

# Reference
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes Security](https://kubernetes.io/docs/concepts/security/)
