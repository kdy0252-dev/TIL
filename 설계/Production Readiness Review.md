---
id: Production Readiness Review
started: 2026-07-14
tags:
  - ✅DONE
  - Architecture
  - Reliability
  - Operations
group: "[[설계]]"
---

# Production Readiness Review: 서비스를 운영에 내보내기 전에 확인할 것

기능 개발이 끝났다는 사실은 서비스가 운영 준비를 마쳤다는 뜻이 아니다. 개발 환경에서 정상 동작하는 애플리케이션도 실제 트래픽, 부분 장애, 배포 실패, 자격 증명 유출과 데이터 복구 상황을 만나면 전혀 다른 모습을 보인다.

**Production Readiness Review(PRR)**는 서비스를 운영 환경에 배포해도 되는지 판단하는 기술 검토 과정이다. 단순한 체크리스트 검사가 아니라 서비스의 위험을 발견하고, 그 위험을 관측하고 복구할 수 있는지를 증거로 확인하는 데 목적이 있다.

---

## 1. Production Ready의 의미

기술은 다음과 같은 단계를 거쳐 성숙한다.

| 단계 | 의미 | 예시 |
|---|---|---|
| 도입 | 라이브러리나 인프라가 존재한다 | Circuit Breaker 의존성을 추가했다 |
| 적용 | 실제 요청 흐름에서 동작한다 | 외부 API 실패 시 Circuit이 열린다 |
| 운영 | 상태를 관측하고 대응할 수 있다 | Open 상태 Metric과 Alert가 있다 |
| 검증 | 장애 실험으로 복구 능력을 입증했다 | 의존 서비스 장애 중 목표 오류율을 지켰다 |

PRR이 확인하는 것은 마지막 두 단계다. “Health Check가 있다”보다 “잘못된 Health Check가 장애를 확대하지 않는가”가 중요하고, “Backup이 있다”보다 “Backup으로 목표 시간 안에 복구해 보았는가”가 중요하다.

운영 준비도는 제품의 속성이 아니라 **지속적으로 갱신되는 상태**다. 트래픽, 데이터 크기, 의존 시스템과 조직 구조가 변하면 이전에 통과한 판단도 다시 검토해야 한다.

---

## 2. 검토를 시작하기 전에 알아야 할 것

PRR은 아키텍처 그림만 보고 진행할 수 없다. 먼저 시스템의 경계와 목표를 명확히 해야 한다.

### 서비스 경계

- 사용자가 진입하는 API와 비동기 Consumer는 무엇인가?
- 데이터베이스, Cache, Message Broker 중 서비스가 소유하는 것은 무엇인가?
- 외부 인증, 결제, 지도, 알림처럼 통제할 수 없는 의존성은 무엇인가?
- 장애가 발생했을 때 함께 영향을 받는 Blast Radius는 어디까지인가?

### 신뢰성 목표

모든 서비스를 무조건 이중화하는 것은 비용 효율적이지 않다. 먼저 사용자 관점의 목표를 정해야 한다.

- **SLI**: 성공률, 지연 시간, 처리 지연, 데이터 신선도처럼 실제로 측정할 값
- **SLO**: 일정 기간 동안 허용할 목표 수준
- **RTO**: 장애 후 서비스를 복구해야 하는 최대 시간
- **RPO**: 장애 시 허용할 수 있는 최대 데이터 손실 범위

예를 들어 “가용성이 높아야 한다”는 검증할 수 없다. 반면 “최근 28일간 예약 생성 요청의 99.9%가 1초 안에 성공한다”는 측정하고 판단할 수 있다.

### 트래픽과 데이터 특성

평균 요청량만으로는 용량을 설계할 수 없다. Peak RPS, 요청 크기, Read·Write 비율, 비동기 적체량, 데이터 증가율과 특정 Tenant의 편중을 함께 봐야 한다. 사용자 요청뿐 아니라 Batch, Migration, Cache Warming처럼 같은 자원을 경쟁하는 작업도 포함한다.

---

## 3. 아키텍처와 의존성 검토

시스템 Diagram에는 정상 경로뿐 아니라 실패 경로가 보여야 한다. 요청이 어디에서 Timeout되고, Retry가 몇 번 발생하며, 최종 실패가 어디에 저장되는지를 설명할 수 있어야 한다.

### 동기 호출

외부 호출에는 최소한 다음 정책이 필요하다.

- Connection Timeout과 Read Timeout을 분리한다.
- 상위 요청의 Deadline보다 하위 Timeout의 합이 짧아야 한다.
- Retry는 일시적이고 안전하게 반복할 수 있는 실패에만 적용한다.
- Retry에 Exponential Backoff와 Jitter를 적용해 동시 재시도를 분산한다.
- 장애가 지속되면 Circuit Breaker와 Load Shedding으로 자원 고갈을 막는다.

여러 계층이 각각 세 번씩 Retry하면 한 사용자 요청이 기하급수적으로 늘어날 수 있다. Retry 소유자는 한 계층으로 정하고, 전체 Retry Budget을 관리해야 한다.

### 비동기 처리

Message Broker나 Outbox를 사용한다고 메시지 처리가 자동으로 안전해지는 것은 아니다. Consumer 중단, 중복 전달, 순서 변경과 Poison Message를 다뤄야 한다.

- Event에는 중복을 판별할 안정적인 식별자가 있어야 한다.
- Consumer는 동일 Event를 여러 번 받아도 결과가 같아야 한다.
- 재시도 횟수와 Backoff, DLQ 이동 조건을 명시한다.
- 처리 실패와 Oldest Message Age를 Metric으로 측정한다.
- 외부 Side Effect 성공 후 내부 상태 저장에 실패한 경우를 Reconciliation으로 복구한다.

이때 [[멱등성과 Reconciliation]], [[신뢰성 있는 비동기 처리]], [[In-flight Deduplication]]은 서로 다른 문제를 해결한다. 멱등성은 반복 실행의 결과를 안정화하고, In-flight Deduplication은 동시에 들어온 동일 작업을 합치며, Reconciliation은 불일치한 상태를 최종적으로 수렴시킨다.

---

## 4. 데이터 보호와 복구 가능성

데이터 계층에서 가장 위험한 오해는 고가용성과 Backup을 같은 것으로 보는 것이다.

- **Replication과 Multi-AZ**는 Instance나 가용 영역 장애에서 서비스 중단을 줄인다.
- **Backup과 Point-in-Time Recovery**는 삭제, 손상과 운영 실수에서 데이터를 되돌린다.
- **Cross-Region 복제**는 Region 단위 재해에 대비한다.

각 수단이 해결하는 실패가 다르므로 RTO와 RPO에 맞게 조합해야 한다.

### 복구 훈련에서 확인할 내용

1. Backup에서 새로운 Database를 복원한다.
2. 애플리케이션의 Connection 정보를 안전하게 전환한다.
3. Migration과 Schema Version의 호환성을 확인한다.
4. 핵심 Record 수와 업무 불변식을 검증한다.
5. 실제 복구 시간과 손실 범위를 기록한다.

Backup Job의 성공 표시만 확인해서는 충분하지 않다. 암호화 Key, 권한, Network 경로 또는 Version 차이 때문에 복원할 수 없는 Backup도 존재한다.

Multi-tenancy 시스템이라면 Tenant Context가 Thread Pool, 비동기 Event와 Connection 재사용 과정에서 누출되지 않는지도 별도로 시험한다. 한 Tenant의 데이터가 다른 Tenant에 노출되는 문제는 단순 장애보다 심각한 보안 사고가 된다.

---

## 5. 보안과 공급망

운영 보안은 애플리케이션 인증만으로 끝나지 않는다. Source Code에서 Container Image와 Runtime Identity까지 전체 공급망을 검토해야 한다.

### 비밀 정보 관리

- Git에는 Secret 값이 아니라 Secret의 이름과 참조만 저장한다.
- 장기 Access Key보다 Workload Identity와 짧은 수명의 자격 증명을 사용한다.
- Secret Manager와 KMS의 접근 권한을 최소화한다.
- Log, CI Artifact, Terraform State와 Rendered Manifest의 노출 가능성을 검사한다.
- Rotation 절차를 자동화하고 실제 무중단 교체를 시험한다.

### 빌드와 배포 무결성

- Dependency와 Container Image의 취약점을 검사한다.
- SBOM을 생성해 배포 Artifact의 구성 요소를 추적한다.
- Image에 서명하고 Admission 단계에서 서명을 검증한다.
- 검증한 동일 Image Digest를 환경 간 승격한다.
- CI Runner와 배포 Controller의 권한을 분리한다.

Kubernetes에서는 Security Context, Pod Security Standards, NetworkPolicy와 RBAC가 함께 작동해야 한다. 하나의 통제만으로 Container Escape, 횡적 이동과 과도한 권한을 모두 막을 수 없다.

---

## 6. Kubernetes Workload의 운영 준비도

Pod가 Running 상태라는 사실은 사용자의 요청을 처리할 준비가 됐다는 뜻이 아니다.

### Probe의 역할 구분

- **Startup Probe**: 초기화가 끝나기 전에 Liveness가 Container를 재시작하는 것을 막는다.
- **Readiness Probe**: 새 요청을 받아도 되는지를 판단한다.
- **Liveness Probe**: 재시작 외에는 회복할 수 없는 상태를 탐지한다.

Database나 외부 API의 일시 장애를 Liveness에 포함하면 모든 Pod가 동시에 재시작되어 장애가 커질 수 있다. 의존성 장애는 보통 Readiness, Circuit Breaker와 Metric으로 다루고 Liveness는 Process 자체의 회복 불가능 상태에 집중한다.

### 배포와 Node 장애

- Resource Request는 Scheduler가 실제 배치 판단에 사용할 수준으로 설정한다.
- Limit로 인한 CPU Throttling과 OOMKill을 관측한다.
- PodDisruptionBudget으로 자발적 중단 중 최소 가용 Replica를 유지한다.
- Topology Spread와 Anti-affinity로 Replica를 Node와 AZ에 분산한다.
- Graceful Shutdown 동안 새 요청을 차단하고 진행 중 요청을 마친다.

Rolling Update나 Blue-Green 배포는 Database Schema 호환성을 자동으로 해결하지 않는다. 구버전과 신버전이 동시에 동작하는 기간을 고려해 Expand–Migrate–Contract 순서로 Schema를 변경해야 한다.

---

## 7. 관측성과 Alert

관측성의 목적은 Dashboard를 많이 만드는 것이 아니라 “사용자에게 어떤 영향이 있고 어디서 시작됐는가”에 빠르게 답하는 것이다.

### 기본 신호

| 신호 | 확인할 질문 |
|---|---|
| Metric | 오류율과 지연 시간이 SLO를 위반하는가? |
| Log | 실패 원인과 업무 식별자를 찾을 수 있는가? |
| Trace | 지연과 오류가 시작된 의존 구간은 어디인가? |
| Profile | CPU와 Memory를 소비하는 Code Path는 어디인가? |

Service, Environment, Version과 Trace ID 같은 공통 속성을 일관되게 사용해야 신호를 연결할 수 있다. 반면 User ID나 요청 URL 전체를 Metric Label에 넣으면 Cardinality가 폭증하므로 제한해야 한다.

좋은 Alert는 증상이 사용자에게 미치는 영향을 알려주고 담당자가 취할 행동으로 이어진다. CPU가 높다는 사실만 알리는 Alert보다 Error Budget 소진 속도, API 오류율과 Queue 처리 지연을 중심으로 구성하는 편이 효과적이다. 각 Alert에는 Owner, 심각도, Dashboard와 Runbook을 연결한다.

---

## 8. 성능과 용량 검증

부하 테스트는 최대 TPS 기록 경쟁이 아니다. 목표 트래픽에서 SLO를 지키고, 과부하가 발생했을 때 시스템이 예측 가능하게 저하되며, 부하가 사라진 뒤 정상으로 회복하는지 확인하는 실험이다.

### k6 시나리오 구성

- **Smoke**: Script와 환경의 기본 동작을 짧게 확인한다.
- **Baseline**: 정상 부하의 지연 시간과 자원 사용량을 기록한다.
- **Load**: 예상 Peak 부하에서 SLO 충족 여부를 확인한다.
- **Stress**: 처리 한계와 병목이 나타나는 지점을 찾는다.
- **Spike**: 순간 유입에서 Queue, Autoscaling과 보호 장치를 검증한다.
- **Soak**: 장시간 실행하며 Memory Leak과 Connection 고갈을 찾는다.

외부에서 일정한 요청률이 유입되는 시스템은 VU 수만 고정한 Closed Model보다 Arrival-rate 기반 Open Model이 현실을 더 잘 표현할 수 있다. 결과를 볼 때는 평균 대신 P95·P99, 실패율, 처리량, Queue 깊이, Connection Pool, GC와 Database Lock을 함께 관찰한다. 자세한 설계 방법은 [[k6 부하 테스트와 성능 검증]]에서 다룬다.

Capacity Planning은 한 번의 시험 결과가 아니라 성장률을 반영한 반복 과정이다. 현재 Peak 사용량, Replica당 안전 처리량과 Failover 시 감소하는 Capacity를 이용해 여유 용량을 계산한다.

---

## 9. 배포와 롤백

안전한 배포는 Artifact를 전달하는 과정이 아니라 변경의 영향을 제한하고 빠르게 되돌리는 과정이다.

- Build Artifact는 불변이어야 하며 환경별로 다시 빌드하지 않는다.
- 설정과 Secret은 Artifact 밖에서 주입하되 Version과 변경 이력을 추적한다.
- 배포 전후 Migration의 호환성을 검사한다.
- Synthetic Test와 핵심 SLI를 승격 조건으로 사용한다.
- 오류율이나 지연 시간이 기준을 벗어나면 자동으로 중단하거나 Rollback한다.

Rollback이 항상 이전 Version 재배포를 의미하지는 않는다. 이미 비호환 Schema 변경이나 외부 Side Effect가 발생했다면 이전 Code가 동작하지 않을 수 있다. 따라서 Roll-forward, Feature Flag, 보상 처리까지 포함해 복구 전략을 설계한다.

---

## 10. PRR을 실제 증거로 바꾸는 방법

PRR이 문서 서명 절차로 끝나지 않으려면 각 주장에 검증 가능한 증거가 필요하다.

| 주장 | 약한 증거 | 강한 증거 |
|---|---|---|
| 장애에 강하다 | Replica가 3개다 | Node Drain 중 SLO를 지킨 실험 결과 |
| 복구할 수 있다 | 매일 Backup한다 | 격리 환경 복원 시간과 정합성 검증 기록 |
| 확장할 수 있다 | HPA가 있다 | Peak 부하에서 Scale-out 시간과 P95 결과 |
| 안전하게 배포한다 | Blue-Green을 쓴다 | 회귀 감지 후 자동 중단한 배포 기록 |
| 관측 가능하다 | Dashboard가 있다 | 장애 시 Metric에서 Trace와 Log로 연결한 기록 |

검토 결과는 서비스의 위험 목록으로 관리한다. 위험마다 영향도, 발생 가능성, Owner, 완화 방법과 재검토 시점을 기록한다. 모든 위험을 제거하는 것이 목적은 아니다. 어떤 위험을 받아들이는지 명시하고, 장애가 현실이 되었을 때 대응할 수 있도록 만드는 것이 중요하다.

대규모 변경, 핵심 의존성 교체, 트래픽 급증, 새로운 Region 진입과 심각한 장애 이후에는 PRR을 다시 수행한다. 운영에서 얻은 사실이 설계 가정보다 항상 우선한다.

---

## 마무리

Production Ready는 특정 기술 목록을 모두 채운 상태가 아니다. 서비스의 목표와 실패 방식을 이해하고, 장애를 탐지하며, 제한된 범위 안에서 실패하고, 정해진 시간 안에 복구할 수 있는 상태다.

좋은 PRR은 “무엇을 설치했는가”보다 다음 질문에 답한다.

> 이 시스템이 실패하면 어떻게 알 수 있고, 사용자 영향은 어디까지이며, 누가 어떤 근거로 복구할 수 있는가?

이 질문에 Diagram, Metric, Test와 복구 훈련 기록으로 답할 수 있다면 서비스는 단순히 동작하는 단계를 넘어 운영 가능한 단계에 가까워진다.

---

# Reference

- [Google SRE - Production Readiness Reviews](https://sre.google/sre-book/evolving-sre-engagement-model/)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [Kubernetes - Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [[SLO와 Error Budget 운영]]
- [[Chaos Engineering과 Game Day]]
- [[Kubernetes Workload 신뢰성]]
- [[AWS Backup과 재해 복구]]
