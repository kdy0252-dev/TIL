---
id: Istio
started: 2025-09-20
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Istio

## 1. 개요 (Overview)
**Istio**는 마이크로서비스 아키텍처(MSA)의 복잡성을 해결하기 위해 등장한 **서비스 메시(Service Mesh)** 솔루션의 사실상 표준(De facto standard)입니다.
수많은 마이크로서비스 간의 통신(Network)을 애플리케이션 코드의 수정 없이 인프라 계층에서 투명하게 제어, 보안, 관측할 수 있게 해줍니다.

기존에는 개발자가 각 서비스 코드에 Retry, Timeout, Circuit Breaker, Tracing 로직을 라이브러리(Hystrix, Ribbon 등) 형태로 심어야 했으나, Istio는 **사이드카(Sidecar) 패턴**을 이용하여 이를 네트워크 프록시 레벨로 위임했습니다. 이를 통해 "비즈니스 로직"과 "네트워크 운영 로직"을 완벽하게 분리합니다.

---

## 2. 아키텍처 (Architecture)

Istio는 크게 **Data Plane**과 **Control Plane**으로 나뉩니다. (Istio 1.5+ 부터 Control Plane이 `istiod`라는 단일 바이너리로 통합되었습니다.)

### 2.1 Data Plane (Envoy Proxy)
- **Sidecar Pattern**: 쿠버네티스(Kubernetes) Pod 안에 애플리케이션 컨테이너와 함께 `Envoy Proxy` 컨테이너가 배포됩니다.
- **역할**:
    - 해당 Pod로 들어오고 나가는 **모든 네트워크 트래픽을 가로챕니다(Intercept)**. (iptables 사용)
    - 서비스 디스커버리, 로드 밸런싱, 헬스 체크, 인증(TLS), 메트릭 수집을 수행합니다.
- **특징**: C++로 작성된 고성능 L4/L7 프록시로, 오버헤드가 적습니다.

### 2.2 Control Plane (istiod)
- **Pilot**: 서비스 디스커버리 정보를 Envoy가 이해할 수 있는 설정(xDS API)으로 변환하여 전파합니다. 트래픽 관리 정책을 관장합니다.
- **Citadel**: 인증서(Certificate)를 발급하고, 키 로테이션을 관리하여 **mTLS(Mutual TLS)** 보안을 담당합니다.
- **Galley**: 설정(Configuration) 유효성 검증 및 배포를 담당합니다.
- **역할**: Envoy 프록시들에게 "어떻게 동작해야 하는지" 지시하는 사령관 역할을 합니다. 트래픽은 Control Plane을 거치지 않습니다.

---

## 3. 핵심 기능 (Key Features)

### 3.1 트래픽 관리 (Traffic Management)
- **Intelligent Routing**: HTTP 헤더, URL, 쿠키 등을 기반으로 트래픽을 특정 버전(v1, v2)으로 라우팅할 수 있습니다.
- **Traffic Splitting**: 카나리 배포(Canary Release) 시 "트래픽의 95%는 v1, 5%는 v2"와 같이 정밀한 가중치 기반 분산이 가능합니다.
- **Circuit Breaker**: 특정 서비스가 장애 상태일 때, 즉시 차단(Fail Fast)하여 전체 장애 전파(Cascading Failure)를 막습니다.
- **Fault Injection**: 의도적으로 지연(Delay)이나 에러(Abort)를 주입하여 시스템의 복원력을 테스트할 수 있습니다 (Chaos Engineering).

### 3.2 보안 (Security)
- **mTLS (Mutual TLS)**: 서비스 간 통신을 자동으로 암호화합니다. 개발자가 인증서를 관리할 필요 없이 투명하게 적용됩니다.
- **Authentication/Authorization**: JWT 검증이나 서비스 간 접근 제어 정책(`AuthorizationPolicy`)을 적용할 수 있습니다.

### 3.3 관측 가능성 (Observability)
- **Metrics**: 요청 수, 응답 시간, 에러율 등의 골든 시그널을 Prometheus 포맷으로 자동 수집합니다.
- **Distributed Tracing**: `x-request-id` 헤더 전파를 통해 분산된 트랜잭션 추적(Jaeger, Zipkin)을 지원합니다.
- **Access Logs**: 모든 트래픽의 상세 접근 로그를 남깁니다.

---

## 4. 주요 Custom Resources (CRD)
Istio는 K8s CRD(Custom Resource Definition)를 통해 설정합니다.

1. **VirtualService**: 라우팅 규칙을 정의합니다. (어디로 보낼까?)
    - 예: `/api/v1/*`은 v1 서비스로, `/api/v2/*`는 v2 서비스로.
2. **DestinationRule**: 목적지에 도달한 후 어떻게 처리할지 정의합니다. (Cluster IP 내부 로드밸런싱, Connection Pool, Outlier Detection 등)
3. **Gateway**: 메시(Mesh) 외부에서 들어오는 트래픽(Ingress)이나 나가는 트래픽(Egress)을 제어하는 로드밸런서 설정.
4. **ServiceEntry**: 메시 외부의 서비스(예: Google API, 외부 DB)를 메시 내부 레지스트리에 등록하여 관리.

---

## 5. 예제 (Example)

### 5.1 카나리 배포 (Canary Deployment) 예시
기존 `reviews` 서비스 v1에 90%, 새로 배포한 v2에 10%의 트래픽을 흘려보내는 설정입니다.

**Routing Rules (VirtualService)**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90
    - destination:
        host: reviews
        subset: v2
      weight: 10
```

**Subset Definition (DestinationRule)**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

### 5.2 서킷 브레이커 설정 (DestinationRule)
`my-service`에 대해 동시 연결 수를 제한하고, 5xx 에러가 연속 발생하면 해당 인스턴스를 로드밸런싱 풀에서 제외(Ejection)합니다.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: my-service
spec:
  host: my-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 1
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
```

---

## 6. 장점과 단점 (Pros & Cons)

### 장점
- **Polyglot**: Java, Go, Node.js 등 언어에 상관없이 일관된 네트워크 정책 적용 가능.
- **Decoupling**: 개발자는 비즈니스 로직에만 집중, 운영자는 네트워크/보안 정책에 집중 가능.
- **Visibility**: 복잡한 마이크로서비스 통신 흐름을 시각화(Kiali 등)하기 좋음.

### 단점
- **Complexity**: 아키텍처가 매우 복잡하며, 쿠버네티스에 대한 깊은 이해가 필요. 학습 곡선이 가파름.
- **Resource Usage**: 모든 Pod에 Envoy Sidecar가 붙으므로 CPU/Memory 리소스 사용량이 증가함 (특히 메모리).
- **Latency**: 프록시를 두 번(송신측, 수신측) 거치므로 미세한 네트워크 지연 시간이 추가됨.

---

## 7. 운영 및 튜닝 포인트 (Operational Tips)

1. **Sidecar Resource Limit**: Envoy 프록시의 메모리 사용량을 모니터링하고 적절한 Limit을 걸어야 합니다. 설정(CRD)이 많아질수록 Envoy 메모리 사용량이 늘어납니다 (`Sidecar` 리소스로 범위 제한 필요).
2. **Proxy Injection 제어**: 네임스페이스 라벨(`istio-injection=enabled`)을 통해 자동 주입을 관리하거나, 특정 Pod 어노테이션으로 제외(`sidecar.istio.io/inject: "false"`)할 수 있습니다.
3. **디버깅**: `istioctl proxy-config` 명령어를 통해 Envoy의 현재 설정, 클러스터 정보, 라우트 정보 등을 조회하여 문제를 분석해야 합니다.

# Reference
- [Istio Official Docs](https://istio.io/latest/docs/)
- [Envoy Proxy](https://www.envoyproxy.io/)
- [Kiali (Service Mesh Visualization)](https://kiali.io/)