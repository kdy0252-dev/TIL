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

# Reference
- [Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Vertical Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/vertical-pod-autoscale/)
- [[KEDA Event-driven Autoscaling]]
