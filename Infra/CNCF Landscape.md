---
id: CNCF Landscape
started: 2026-01-23
tags:
  - ✅DONE
  - Infra
  - CloudNative
  - CNCF
  - Kubernetes
  - Architecture
group:
  - "[[Infra]]"
---
# CNCF Landscape: 클라우드 네이티브 생태계의 지형도

## 개요

**CNCF(Cloud Native Computing Foundation)** Landscape은 현대 소프트웨어 아키텍처의 표준인 클라우드 네이티브 생태계를 구성하는 수많은 오픈 소스 프로젝트와 상용 솔루션을 체계적으로 분류한 지형도이다. 클라우드 네이티브 컴퓨팅은 공용, 사설 및 하이브리드 클라우드와 같은 현대적이고 역동적인 환경에서 확장 가능한 애플리케이션을 구축하고 실행할 수 있는 능력을 의미한다.

이 문서는 CNCF Landscape의 각 레이어(Layer)와 기둥(Column)을 분석하여, 엔지니어가 비즈니스 요구사항에 맞는 적절한 기술 스택을 선택하고 클라우드 네이티브 여정을 설계하는 데 도움을 주기 위해 작성되었다.

---

## 1. Provisioning (프로비저닝)

애플리케이션이 실행될 기반 인프라를 구축하고 관리하며 보안을 강화하는 단계이다.

### 1.1. Infrastructure (인프라스트럭처)
클라우드 네이티브의 하부 토대이다.
- **Bare Metal**: 직접 하드웨어를 관리하는 리눅스 서버 환경
- **Public Cloud**: AWS, Google Cloud, Azure 등
- **Virtualization**: VMware, KVM 등 가상화 기술

### 1.2. Automation & Configuration (자동화 및 설정)
인프라를 코드로 관리(IaC)하고 일관된 상태를 유지한다.
- **대표 도구**: Terraform, Ansible, Pulumi, CloudFormation
- **핵심 가치**: 수동 조작을 배제한 재현 가능성(Reproducibility) 확보

### 1.3. Security & Compliance (보안 및 컴플라이언스)
컨테이너 환경의 취약점 진단, 런타임 보안, 정책 관리를 담당한다.
- **주요 프로젝트**: **Falco** (런타임 보안), **OPA (Open Policy Agent)** (정책 엔진), **Kyverno**, **Trivy** (이미지 스캔)

### 1.4. Key Management (키 관리)
비밀번호, API 키, 인증서 등 민감 정보를 안전하게 관리한다.
- **대표 도구**: **HashiCorp Vault**, SPIFFE/SPIRE (ID 부여)

---

## 2. Runtime (런타임)

컨테이너가 실제로 실행되는 환경에서 필요한 리소스를 제공한다.

### 2.1. Cloud Native Storage (스토리지)
상태 유지(Stateful) 애플리케이션을 위해 컨테이너의 라이프사이클과 독립적인 데이터 저장소를 제공한다.
- **주요 프로젝트**: **Rook** (Ceph 오케스트레이션), **Longhorn**, OpenEBS

### 2.2. Container Runtime (컨테이너 런타임)
컨테이너 이미지를 실제 프로세스로 실행하는 저수준 엔진이다.
- **주요 프로젝트**: **containerd**, **CRI-O**

### 2.3. Cloud Native Network (네트워크)
컨테이너 간 통신과 가상 네트워크를 관리하는 CNI(Container Network Interface) 영역이다.
- **주요 프로젝트**: **Cilium** (eBPF 기반), **Calico**, Flannel

---

## 3. Orchestration & Management (오케스트레이션 및 관리)

분산 환경에서 컨테이너의 배치, 확장, 연결을 자동화한다.

### 3.1. Scheduling & Orchestration
클라우드 네이티브의 심장부이다.
- **독보적 리더**: **Kubernetes (K8s)**
- **대안/특화**: Nomad, Docker Swarm

### 3.2. Coordination & Service Discovery
서비스가 서로를 찾고 상태를 공유하는 메커니즘이다.
- **주요 프로젝트**: **CoreDNS**, **etcd** (K8s의 상태 저장소)

### 3.3. Service Mesh
마이크로서비스 간의 트래픽 관리, 보안(mTLS), 관측성을 담당하는 가상 베리어다.
- **주요 프로젝트**: **Istio**, **Linkerd**, Consul

### 3.4. API Gateway
클라이언트와 백엔드 서비스 사이의 단일 진입점으로 라우팅과 인증을 수행한다.
- **주요 프로젝트**: **Envoy** (데이터 플레인), **Emissary-ingress**, Kong

---

## 4. App Definition & Development (앱 정의 및 개발)

개발자가 애플리케이션을 빌드하고 배포하며 데이터를 처리하는 도구 모음이다.

### 4.1. Database (데이터베이스)
클라우드 네이티브 환경에 최적화된 DB이다.
- **SQL**: **TiDB**, **Vitess** (MySQL 확장), CockroachDB
- **NoSQL**: MongoDB, Cassandra

### 4.2. Streaming & Messaging
이벤트 기반 아키텍처(EDA)를 위한 비동기 통신 채널이다.
- **주요 프로젝트**: **Strimzi** (Kafka on K8s), **CloudEvents**, RabbitMQ, NATS

### 4.3. Application Definition & Image Build
앱을 패키징하고 배포 형태를 정의한다.
- **대표 도구**: **Helm**, Kustomize, Buildpacks

### 4.4. Continuous Integration & Delivery (CI/CD)
지속적 통합과 배포를 자동화하며, 최근에는 **GitOps**가 주류이다.
- **주요 프로젝트**: **ArgoCD**, **FluxCD** (GitOps), **Tekton**, Jenkins

---

## 5. Observability & Analysis (관측성 및 분석)

복잡한 분산 시스템의 상태를 모니터링하고 문제를 진단한다.

### 5.1. Monitoring (Metric)
시스템의 수치 데이터를 수집하고 시각화한다.
- **사실상 표준**: **Prometheus** + **Grafana**
- **대규모 환경**: Thanos, Cortex

### 5.2. Logging
로그 데이터를 수집하고 중앙에서 검색한다.
- **대표 스택**: **Fluentd**, **Loki**, OpenSearch

### 5.3. Tracing (분산 추적)
요청이 여러 서비스를 통과하는 경로를 추적한다.
- **주요 프로젝트**: **Jaeger**, Zipkin, **OpenTelemetry (Otel)**

---

## 6. CNCF 프로젝트 성숙도 모델

CNCF는 프로젝트의 안정성과 커뮤니티 활성도에 따라 3단계로 관리한다.

1.  **Graduated (졸업)**: 가장 성숙한 단계. 대규모 프로덕션 환경에서 검증되었으며 거버넌스가 안정적임 (예: Kubernetes, Prometheus, Istio, Argo).
2.  **Incubating (인큐베이팅)**: 프로덕션 환경에서 사용 가능하지만, 아직 커뮤니티 확장이 필요한 단계 (예: Cilium, Falco, KEDA).
3.  **Sandbox (샌드박스)**: 실험적인 초기 단계. 혁신적인 아이디어를 수용하는 공간.

---

## 7. 클라우드 네이티브를 향한 전략적 조언

CNCF Landscape은 단순히 도구 목록이 아니라, **"어떻게 하면 인프라 종속성을 탈피하고 민첩성을 확보할 것인가"**에 대한 해답이다.

1.  **표준 지향**: 특정 벤더에 종속되지 않도록 CNCF의 표준 인터페이스(CRI, CNI, CSI)를 준수하는 프로젝트를 선택하라.
2.  **단계적 도입**: 처음부터 모든 레이어를 도입하기보다 K8s(오케스트레이션) -> Prometheus(관측성) -> ArgoCD(배포) 순으로 핵심부터 확장하라.
3.  **Governance 확인**: 프로젝트의 성숙도(Graduated/Incubating)와 업데이트 주기를 반드시 확인하고 도입 여부를 결정하라.
4.  **Platform Engineering**: 개발자가 이 복잡한 Landscape을 일일이 알 필요 없도록, 내부 개발자 플랫폼(IDP)으로 추상화하는 것이 최신 트렌드이다.

# Reference
- [CNCF 공식 랜드스카이프 (Interactive)](https://landscape.cncf.io/)
- [Cloud Native Computing Foundation 공식 홈페이지](https://www.cncf.io/)
- [The New Stack: CNCF Landscape Guide](https://thenewstack.io/guide-to-the-cloud-native-landscape/)
- [CNCF Trail Map: 클라우드 네이티브로 가는 경로](https://github.com/cncf/trailmap)
