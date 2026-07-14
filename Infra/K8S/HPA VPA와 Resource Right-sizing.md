---
id: HPA VPA와 Resource Right-sizing
started: 2026-07-03
tags:
  - ✅DONE
  - K8S
  - Autoscaling
  - HPA
  - VPA
group:
  - "[[Infra K8S]]"
---
# HPA VPA와 Resource Right-sizing

## 1. 수평 확장과 수직 조정

HPA는 Pod 수를 바꾸고 VPA는 Pod의 CPU·Memory Request를 조정한다. 둘은 같은 문제를 다른 축에서 해결한다.

```text
HPA: replicas 3 -> 8
VPA: request 250m/512Mi -> 500m/768Mi
```

HPA는 병렬 처리 가능한 Stateless Workload의 부하 변화에 적합하다. VPA는 실제 사용량과 Request의 차이를 학습해 Right-sizing하는 데 유용하지만 적용 과정에서 Pod 재시작이 필요할 수 있다.

## 2. HPA의 CPU Utilization 계산

CPU Utilization Target은 Node 전체 CPU가 아니라 `현재 사용량 / Pod CPU Request` 비율이다. Request가 100m인 Pod가 80m를 사용하면 80%다. Request를 절반으로 낮추면 같은 사용량도 160%가 되어 HPA가 더 민감하게 확장한다.

대략적인 Replica 계산은 다음과 같다.

```text
desiredReplicas = ceil(currentReplicas × currentMetric / targetMetric)
```

Request가 없으면 CPU Utilization 기반 계산이 불완전해진다. Autoscaling과 Resource 설정은 독립된 항목이 아니다.

### Request와 Limit은 서로 다른 계약이다

`requests`는 Scheduler가 Pod를 어느 Node에 배치할지 판단하는 예약량이다. Node의 실제 여유가 많아 보여도 모든 Pod의 Request 합이 Allocatable Capacity를 넘으면 새 Pod는 Pending이 된다. Cluster Autoscaler와 Karpenter도 이 Pending Pod의 Request를 보고 필요한 Node 크기를 계산한다.

`limits`는 Container가 사용할 수 있는 상한이다. CPU와 Memory는 상한을 넘었을 때 동작이 다르다.

| Resource | Request | Limit 초과 시 동작 |
|---|---|---|
| CPU | Scheduling 예약량, HPA Utilization의 분모 | CFS Throttling으로 실행 시간이 제한됨 |
| Memory | Scheduling 예약량, Node 과밀 배치 판단 | Container가 OOMKilled될 수 있음 |

CPU는 압축 가능한 Resource라 Limit에 도달해도 Process가 바로 종료되지는 않지만 Latency가 길어진다. Memory는 압축할 수 없어 상한을 넘으면 Process가 종료될 수 있다. 따라서 두 Resource에 같은 비율을 기계적으로 적용해서는 안 된다.

### Workload 특성에 따른 Resource Profile

실제 배포에서는 모든 서비스에 같은 기본값을 복사하지 않고 역할에 따라 다른 Profile을 둘 수 있다. 다음은 네 가지 Workload를 구분한 예다.

| Workload | CPU Request | CPU Limit | Memory Request | Memory Limit | 해석 |
|---|---:|---:|---:|---:|---|
| Core API | 750m | 2500m | 2Gi | 5Gi | JVM Heap과 높은 업무 처리량을 고려 |
| Gateway | 200m | 1000m | 768Mi | 2Gi | Routing 중심이지만 순간 Traffic Burst 허용 |
| BFF | 100m | 1000m | 512Mi | 1536Mi | 비교적 작은 정상 사용량과 Burst 여유 |
| Metrics Job | 150m | 1000m | 768Mi | 3Gi | Batch 집계 중 Memory Peak를 고려 |

이 값은 정답이 아니라 초기 운영 계약이다. Request 대비 Limit 비율이 큰 Workload는 평소에는 많은 Pod가 한 Node에 배치되지만 동시에 Burst가 발생하면 CPU 경합이나 Memory Pressure가 커질 수 있다. 특히 Memory Limit이 Request의 여러 배라면 모든 Pod가 Limit 근처까지 사용하는 상황을 Node가 수용할 수 있는지 확인해야 한다.

JVM Workload의 Memory Limit은 Heap만 보고 정하지 않는다.

```text
Container Memory
  = Heap
  + Metaspace
  + Thread Stack
  + Direct Buffer
  + Code Cache
  + Native Library
```

`-Xmx`를 Container Limit과 같게 두면 Native Memory가 들어갈 공간이 없어 OOMKill이 발생할 수 있다. `container_memory_working_set_bytes`, `jvm_memory_used_bytes`, Native Memory와 OOM Event를 함께 관찰해 안전 여유를 둔다.

### Right-sizing의 반복 절차

1. 정상·Peak·Batch 구간의 CPU와 Memory 사용량을 수집한다.
2. P50이 아니라 P95와 최대값, OOM 및 Throttling을 함께 본다.
3. Request는 정상 Peak를 안정적으로 수용하면서 Node 과밀 배치를 막도록 조정한다.
4. Limit은 비정상 폭주를 제한하되 정상 Burst와 Runtime Overhead를 수용하도록 정한다.
5. k6 Load·Spike·Soak Test로 Latency와 회복 시간을 재검증한다.
6. VPA Recommendation과 실제 배포값의 차이를 정기적으로 검토한다.

CPU Limit은 Java처럼 Latency에 민감한 서비스에서 심한 Throttling을 만들 수 있으므로 CPU Request만 명시하고 Limit을 두지 않는 전략도 가능하다. 다만 공유 Cluster의 공정성과 장애 범위를 고려해 Namespace Quota, PriorityClass와 함께 결정해야 한다.

## 3. CPU만으로 부족한 경우

I/O 대기형 API는 요청이 쌓여도 CPU가 낮을 수 있다. Queue Consumer는 Queue Length, Gateway는 RPS나 동시 요청, Thread Pool 서비스는 Active Task와 Queue Wait가 더 직접적인 부하 신호다.

Application Metric을 쓸 때 “Replica가 늘면 Metric이 실제로 줄어드는가”를 묻는다. 외부 Database가 병목이면 Pod를 늘릴수록 Connection과 부하만 증가할 수 있다.

## 4. Scale-up과 Scale-down의 시간축

급격한 Scale-up은 장애를 줄이지만 많은 Pod가 동시에 시작하며 DB Connection Storm과 Image Pull Burst를 만든다. Scale-down이 너무 빠르면 잠깐의 부하 감소 뒤 다시 확장하는 Flapping이 생긴다.

HPA Behavior의 Stabilization Window와 변화량 정책으로 속도를 조절한다. Startup Probe와 초기 Metric 제외 기간도 Cold Start 중 잘못된 신호를 줄인다.

## 5. VPA의 동작 Mode

VPA Recommender는 과거 사용량, OOM Event와 현재 Resource를 보고 추천값을 만든다. `Off` Mode는 추천만 관찰하므로 도입 초기에 안전하다. 자동 적용 Mode는 Workload Resource를 갱신하며 실행 중 Pod 교체가 발생할 수 있다.

`minAllowed`, `maxAllowed`, `controlledResources`로 범위를 제한한다. Memory Peak가 드문 Application은 짧은 관측 기간만 보고 Request를 낮추면 다음 Peak에 OOM이 날 수 있다.

## 6. HPA와 VPA를 함께 쓸 때

HPA가 CPU Utilization을 사용하면서 VPA가 CPU Request를 계속 바꾸면 HPA의 분모도 변해 두 Controller가 서로 영향을 준다. 일반적으로 HPA가 CPU를 제어한다면 VPA는 Memory만 조정하거나 Recommendation 용도로 사용한다. Custom/External Metric HPA는 이 충돌을 줄일 수 있다.

KEDA는 Event Source를 기반으로 HPA를 생성·관리한다. 같은 Workload에 별도 HPA를 중복 생성하지 않고 Ownership을 명확히 한다.

## 7. 부하 테스트로 검증하기

Autoscaling Test는 최대 처리량 숫자만 측정하지 않는다.

- 부하 시작부터 새 Pod Ready까지 걸린 시간
- Pending이 Node 증설을 기다린 시간
- Scale-up 중 오류율과 P95/P99 Latency
- DB Connection과 Cache Miss 증가
- 부하 종료 후 Scale-down과 비용 회수 시간

K6 같은 부하 도구로 계단형, 급증형과 장시간 부하를 나눠 실행해야 Controller의 시간 특성을 볼 수 있다.

## 8. 실무에서 빠지기 쉬운 설계

Helm에 HPA 설정이 있어도 Target Metric의 선택 근거, Request 보정 과정과 Node Autoscaler까지의 연쇄가 설명되지 않으면 운영 중 왜 확장되지 않았는지 알기 어렵다. VPA가 없다면 오래된 Request가 실제 사용량과 크게 어긋나 Capacity와 비용을 왜곡할 수 있다.

먼저 VPA Recommendation과 실제 P95·Peak 사용량으로 Request를 교정한다. 이후 HPA/KEDA Metric이 부하를 선행해서 표현하는지 검증하고, Pod 확장부터 Karpenter Node Ready까지 전체 시간을 SLO와 비교한다.

## 9. 기억할 점

Autoscaling은 무한 Capacity가 아니라 지연된 Feedback Control이다. 올바른 Metric, 정확한 Request, 안전한 변화 속도와 하위 의존성의 여유가 함께 있어야 부하를 흡수한다.

Replica를 1개로 고정하고 HPA를 비활성화한 Workload는 Resource 값이 적절해도 Pod 또는 Node 장애 시 가용성을 제공하지 못한다. Resource Right-sizing과 고가용성은 별도 문제이며 최소 Replica, Topology 분산, PDB와 Autoscaling을 함께 설계해야 한다.

# Reference
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Vertical Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/vertical-pod-autoscale/)
- [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [[KEDA Event-driven Autoscaling]]
