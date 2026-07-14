---
id: Chaos Engineering과 Game Day
started: 2026-07-01
tags:
  - ✅DONE
  - Reliability
  - Chaos-Engineering
  - Game-Day
group:
  - "[[Infra K8S]]"
---
# Chaos Engineering과 Game Day

## 1. 개요

Chaos Engineering은 시스템에 무작위 장애를 만드는 활동이 아니라, 정상 상태에 대한 가설을 세우고 통제된 실패를 주입해 복원력을 검증하는 실험 방법입니다.

```text
Steady State 정의
  -> 장애 가설
  -> 최소 Blast Radius 실험
  -> 관측과 Abort
  -> 복구
  -> 학습과 개선
```

Game Day는 사람, Runbook, 권한, 커뮤니케이션까지 포함한 운영 훈련입니다. 자동 Chaos Experiment가 기술 동작을 반복 검증한다면 Game Day는 실제 Incident 대응 체계를 검증합니다.

---

## 2. 장애 주입과 Chaos Engineering의 차이

Pod를 삭제하는 명령 하나는 Chaos Engineering이 아닙니다. 다음 요소가 있어야 실험입니다.

- 사용자 관점의 정상 상태
- 실패 가설과 기대 동작
- 영향 범위와 중단 조건
- 관측 Signal
- 복구 방법
- 결과와 후속 작업

운영 환경에서 처음 실행하지 않습니다. Local·Stage에서 자동화와 복구를 검증한 뒤 범위를 점진적으로 넓힙니다.

---

## 3. Steady State

Steady State는 CPU나 Pod 수가 아니라 사용자 경험으로 정의합니다.

- 예약 성공률이 SLO 이내입니다.
- 배차 조회 P95가 기준 이내입니다.
- Outbox Oldest Age가 임계치 이내입니다.
- Error Budget Burn Rate가 정상입니다.

실험 전후 같은 Query로 측정할 수 있어야 합니다.

---

## 4. 가설 예시

```text
가설:
단일 Application Pod를 종료해도
예약 성공률과 P95는 SLO를 유지하고
30초 안에 Replica가 복구된다.
```

좋은 가설은 실패를 기대하는 것이 아니라 시스템이 유지해야 할 행동과 시간을 명시합니다.

---

## 5. 실험 성숙도

| 단계 | 실험 | 검증 대상 |
|---|---|---|
| 1 | Pod Kill | Replica, Readiness, Graceful Shutdown |
| 2 | CPU·Memory Pressure | Limit, HPA, Load Shedding |
| 3 | Network Delay·Loss | Timeout, Retry, Circuit Breaker |
| 4 | Node Drain | PDB, Topology, Volume 재연결 |
| 5 | Redis·DB Failover | Connection 재수립, 정합성 |
| 6 | AZ 경로 차단 | Multi-AZ, NAT, Load Balancer |
| 7 | Control Plane 도구 장애 | GitOps·Observability 독립성 |

작은 실패가 통과하지 못하면 더 큰 실패로 진행하지 않습니다.

---

## 6. Blast Radius

Blast Radius는 Namespace, Tenant, Traffic 비율, 시간으로 제한합니다.

- 테스트 전용 Tenant부터 시작합니다.
- Replica 하나 또는 Node 하나만 대상으로 합니다.
- 업무 저부하 시간과 짧은 Duration을 사용합니다.
- Label Selector를 명확히 하고 Wildcard를 피합니다.
- Production 실행에는 별도 승인과 자동 만료를 둡니다.

Chaos 도구의 ServiceAccount가 Cluster-admin이면 실험 도구 자체가 큰 위험입니다.

---

## 7. Abort Condition

다음 조건에서는 즉시 중단합니다.

- Critical Journey Error Rate가 한도를 넘습니다.
- Data Loss 또는 Tenant 격리 위반이 의심됩니다.
- 복구 Automation이 동작하지 않습니다.
- 관측성이 사라져 상태를 판단할 수 없습니다.
- 실험 대상 밖 서비스에 영향이 나타납니다.

Abort는 실패가 아니라 안전 장치가 정상 동작한 결과입니다.

---

## 8. Retry 실험의 함정

Network 지연을 주입하면 Retry가 부하를 증폭할 수 있습니다.

```text
지연 증가
  -> Timeout
  -> Retry 증가
  -> Downstream 부하 증가
  -> 더 큰 지연
```

Retry Count, Backoff, Jitter, Retry Budget, Circuit Breaker와 원래 요청 수를 함께 관찰합니다. 성공률만 보면 Retry Storm을 놓칠 수 있습니다.

---

## 9. 상태 저장 계층 실험

DB·Redis 장애는 데이터 정합성 검사가 핵심입니다.

- RDS Failover 후 Connection Pool이 오래된 연결을 버리는가
- Transaction 결과가 중복 또는 부분 반영되지 않는가
- Redis 전체 유실 뒤 Cache를 재구성할 수 있는가
- Lock 만료 후 오래된 작업자가 쓰지 않는가
- Outbox가 중복 없이 최종 상태로 수렴하는가

가용성 회복만 보고 데이터 오류를 놓치지 않습니다.

---

## 10. 관측성 장애 실험

Loki나 Tempo가 느릴 때 Application이 함께 느려져서는 안 됩니다. Alloy Queue, Drop, Memory와 업무 Pod 축출 여부를 봅니다.

Alertmanager 또는 Teams Relay를 중단해 Notification Failure가 독립 경로로 감지되는지도 시험합니다. 관측 시스템은 자신을 완전히 감시할 수 없으므로 외부 Synthetic 경로가 필요합니다.

---

## 11. Game Day 운영

역할을 미리 나눕니다.

- Experiment Lead: 실험 진행과 중단 결정
- Incident Commander: 대응 우선순위 결정
- Operator: 복구 조치 실행
- Observer: 시간과 Signal 기록
- Communications: 영향과 상태 공유

실제 장애처럼 진행하되 고객 영향이 발생하기 전에 Experiment Lead가 즉시 중단할 권한을 가집니다.

---

## 12. 결과 기록

각 실험은 다음을 남깁니다.

- 날짜, 환경, Image와 Infrastructure Version
- 가설, Steady State, 대상
- 장애 주입 시각과 Duration
- 탐지 시간, 완화 시간, 완전 복구 시간
- SLO와 Error Budget 영향
- 예상과 달랐던 동작
- 후속 작업, Owner, 기한

통과한 실험도 시스템 변경 뒤 다시 실행해야 합니다.

---

## 13. 사례 시스템의 우선 실험

1. Blue-Green 전환 중 이전 Pod 강제 종료
2. Node Drain 중 PDB와 Topology 검증
3. 외부 지도 API에 2초 지연과 5xx 주입
4. Redis Primary Failover와 Cache 전체 삭제
5. RDS Failover와 Connection Pool 회복
6. 단일 NAT 경로 장애
7. Loki·Tempo 수신 차단
8. Outbox Worker 종료와 Lease 만료 후 재처리

현재 PDB·NetworkPolicy와 Multi-AZ 공백이 있으므로 Production 실험 전에 Stage에서 Guardrail을 먼저 구현해야 합니다.

---

## 14. 완료 기준

- [ ] 실험마다 SLO 기반 Steady State가 있습니다.
- [ ] Blast Radius와 Abort Condition이 자동화되어 있습니다.
- [ ] 실행 권한과 대상 Label이 최소 범위입니다.
- [ ] 복구가 사람의 기억이 아니라 Runbook으로 가능합니다.
- [ ] 가용성뿐 아니라 중복·유실·정합성을 검증합니다.
- [ ] 결과에 탐지·완화·복구 시간이 기록됩니다.
- [ ] 발견된 문제에 Owner와 완료 기한이 있습니다.
- [ ] 핵심 실험을 Release 또는 분기마다 반복합니다.

---

# Reference

- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [LitmusChaos Documentation](https://litmuschaos.io/)
- [Chaos Mesh Documentation](https://chaos-mesh.org/docs/)
- [[SLO와 Error Budget 운영]]
- [[Kubernetes Workload 신뢰성]]
- [[신뢰성 있는 비동기 처리]]
