---
id: Istio 트래픽 모니터링 및 Sidecar
started: 2026-01-13
tags:
  - ✅DONE
  - Infra
  - Mesh
  - Istio
  - K8s
group:
  - "[[Infra]]"
---
# Istio 가이드: Sidecar 패턴을 이용한 트래픽 모니터링 및 관리

## 1. 개요 (Introduction)

마이크로서비스 아키텍처(MSA)가 복잡해짐에 따라, 서비스 간의 통신(East-West Traffic)을 관리하고 가시성을 확보하는 것이 시스템 운영의 핵심 과제가 되었습니다. **Istio**는 애플리케이션 코드의 수정 없이 서비스 메시(Service Mesh)를 구축하여 트래픽 관리, 보안, 관측성(Observability)을 제공하는 오픈소스 플랫폼입니다.

본 가이드에서는 Istio의 핵심인 **Sidecar 패턴**의 개념을 이해하고, 실제 환경에서 Istio를 다운로드하고 설치하여 트래픽을 모니터링하는 전 과정을 상세히 다룹니다.

---

## 2. Sidecar 패턴과 서비스 메시

### 2.1 Sidecar 패턴이란?
애플리케이션 컨테이너 옆에 별도의 프록시 컨테이너(Envoy)를 배치하는 아키텍처 패턴입니다. 오토바이에 장착된 사이드카처럼 애플리케이션과 생명주기를 함께하며 통신 기능을 대행합니다.

- **관점 분리**: 개발자는 비즈니스 로직에만 집중하고, 로깅/모니터링/보안/트래픽 제어는 사이드카가 담당합니다.
- **언어 독립성**: 애플리케이션의 구현 언어와 상관없이 통일된 네트워크 제어가 가능합니다.

### 2.2 Istio 아키텍처
- **Data Plane**: Envoy 프록시로 구성되며, 모든 서비스 간 통신을 제어합니다.
- **Control Plane (istiod)**: 프록시 설정, 서비스 발견(Service Discovery), 인증 및 정책을 관리합니다.

---

## 3. Istio 설치 및 설정 (Installation)

### 3.1 Istio 다운로드
먼저 로컬 환경 또는 서버에서 `istioctl` 클라이언트를 다운로드해야 합니다.

```bash
# 1. 최신 버전 Istio 다운로드 스크립트 실행
curl -L https://istio.io/downloadIstio | sh -

# 2. 다운로드된 디렉토리로 이동 (예: istio-1.24.1)
cd istio-$(istioctl version --short --remote=false)

# 3. PATH 환경 변수 추가 (어디서든 istioctl을 사용하기 위침)
export PATH=$PWD/bin:$PATH
```

### 3.2 Kubernetes에 Istio 설치
Istio는 다양한 설치 프로필을 제공합니다. 개발 및 데모용인 `demo` 프로필을 사용하여 설치해 보겠습니다.

```bash
# 기본 데모 프로필로 Istio 설치
istioctl install --set profile=demo -y
```

설치가 완료되면 `istio-system` 네임스페이스에 `istiod`와 `istio-ingressgateway`가 실행되는 것을 확인할 수 있습니다.

### 3.3 사이드카 주입(Sidecar Injection) 활성화
특정 네임스페이스의 파드(Pod)에 자동으로 사이드카 프록시가 주입되도록 레이블을 설정합니다.

```bash
# default 네임스페이스에 자동 주입 활성화
kubectl label namespace default istio-injection=enabled
```

이후 `default` 네임스페이스에 배포되는 모든 애플리케이션 파드에는 Envoy 프록시 컨테이너가 자동으로 추가됩니다.

---

## 4. 트래픽 모니터링 애드온 설치 (Observability)

Istio는 수집된 지표를 시각화하기 위해 다양한 오픈소스 도구들과 통합됩니다.

### 4.1 애드온 설치 가이드
Istio 설치 패키지 내의 `samples/addons` 디렉토리에 포함된 매니페스트를 사용합니다.

```bash
# Prometheus (지표 수집), Grafana (대시보드), Jaeger (분산 트레이싱), Kiali (가시화) 설치
kubectl apply -f samples/addons
```

### 4.2 Kiali를 이용한 트래픽 가시화
**Kiali**는 서비스 메시의 전체 구조와 트래픽 흐름을 실시간 그래프로 보여주는 핵심 대시보드입니다.

```bash
# Kiali 대시보드 실행
istioctl dashboard kiali
```

Kiali 대시보드에 접속하면 다음과 같은 지표를 한눈에 볼 수 있습니다:
- **Graph**: 네임스페이스 내 서비스 간 의존성 및 트래픽 흐름도
- **Health**: 각 서비스의 성공률 및 지연 시간 (Request per second, P99 latency)
- **Validation**: Istio 설정 객체(VirtualService, DestinationRule)의 유효성 검사 결과

---

## 5. 실무 설정법: 트래픽 관리 (Traffic Management)

모니터링을 넘어 특정 트래픽을 제어하는 설정법입니다.

### 5.1 VirtualService (라우팅 규칙)
특정 비율로 트래픽을 나누는 Canary 배포 설정 예시입니다.

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

### 5.2 DestinationRule (부하 분산 정책)
연결 풀(Connection Pool)이나 이상점 감지(Outlier Detection) 설정을 정의합니다.

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
  trafficPolicy:
    loadBalancer:
      simple: RANDOM
```

---

## 6. 보안 및 트래픽 암호화 (mTLS)

Istio는 사이드카 간의 통신에 자동으로 **Mutual TLS (mTLS)**를 적용하여 네트워크 데이터를 암호화합니다.

- **PeerAuthentication**: 네임스페이스 전체 또는 특정 서비스의 암호화 정책을 설정합니다.
- **가시성**: Kiali 그래프 상에서 잠금 아이콘(Lock)을 통해 현재 통신이 암호화되어 있는지 시각적으로 확인할 수 있습니다.

---

## 7. 결론

Istio는 사이드카 패턴을 통해 인프라 레이어에서 거대한 MSA 시스템을 통제할 수 있는 강력한 도구입니다.
- **istioctl**로 간편하게 클러스터를 제어하고,
- **Automatic Injection**으로 운영 부담을 줄이며,
- **Kiali/Prometheus** 조합으로 블랙박스 같던 동적 트래픽을 낱낱이 파헤치십시오.

초기 학습 곡선은 다소 높을 수 있으나, 시스템의 규모가 커질수록 Istio가 제공하는 가시성과 보안성은 대체 불가능한 자산이 될 것입니다.

# Reference
- [Istio Official Documentation](https://istio.io/latest/docs/setup/getting-started/)
- [Kiali Official Documentation](https://kiali.io/docs/)
- [Envoy Proxy Documentation](https://www.envoyproxy.io/docs)
- [Service Mesh Patterns - O'Reilly Media](https://www.oreilly.com/library/view/service-mesh-patterns/9781492055112/)
