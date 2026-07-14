---
id: Kubecost Kubernetes 비용 관리
started: 2026-07-06
tags:
  - ✅DONE
  - K8S
  - Kubecost
  - FinOps
group:
  - "[[Infra K8S]]"
---
# Kubecost Kubernetes 비용 관리

## 1. 개요 (Overview)

Kubecost는 Kubernetes Resource 사용량과 Cloud Billing Data를 결합해 Namespace, Workload, Label, Team별 비용을 추정합니다. 이 배포 사례에서는 AWS Cost and Usage Report(CUR), S3, Athena와 IRSA를 연결해 EKS 내부 할당 비용과 AWS 청구 데이터를 함께 분석합니다.

```text
AWS CUR -> S3 -> Athena
                    \
Kubernetes Metric -> Kubecost -> Allocation / Efficiency / Savings
```

목표는 단순히 전체 Cloud Bill을 보는 것이 아니라 **어떤 서비스와 환경이 비용을 만들었고, 요청한 Resource 대비 실제로 얼마나 사용했는지** 설명하는 것입니다.

---

## 2. 비용 모델

Kubernetes Pod 비용은 대략 다음 요소로 구성됩니다.

```text
Pod Cost
  = CPU Allocation Cost
  + Memory Allocation Cost
  + GPU Cost
  + Persistent Volume Cost
  + Network Cost
  + Shared Cluster Cost 배분
```

여기서 Allocation은 실제 사용량만을 뜻하지 않습니다. Scheduler가 예약한 Request나 Node에서 점유한 몫을 기준으로 비용을 배분할 수 있습니다. CPU 사용률이 낮아도 Request가 크면 다른 Pod가 그 Node를 활용하지 못하므로 비용 책임이 발생합니다.

Idle Cost는 Node Capacity 중 Workload에 할당되지 않은 부분입니다. 이를 플랫폼 공통 비용으로 둘지, Namespace 비율로 재분배할지는 조직의 FinOps 정책입니다.

---

## 3. Metric과 Billing Data의 차이

Prometheus Metric은 Resource 사용과 Allocation을 세밀하게 보여주지만 실제 할인, 세금, Support Fee까지 알지 못합니다. CUR은 실제 AWS 청구에 가깝지만 Kubernetes Workload 정보를 직접 갖지 않습니다.

Kubecost는 두 데이터를 결합합니다.

- Kubernetes Metric: Pod, Container, Node, PVC의 시간별 사용과 요청
- AWS 가격 정보: Instance, Storage, Network 단가
- CUR/Athena: Savings Plans, Reserved Instance, Credit 등 실청구 보정

데이터 지연도 다릅니다. Metric은 거의 실시간이지만 CUR은 보통 지연 생성됩니다. 당일 비용은 추정치, 지난 청구 기간은 조정된 값이라는 차이를 Dashboard에 명시해야 합니다.

---

## 4. CUR, S3, Athena 연결

AWS CUR은 세부 비용 레코드를 S3에 전달하고 Athena가 이를 Query합니다. Kubecost는 IRSA로 Athena Query와 결과 Bucket에 접근합니다.

필요한 권한 범주는 다음과 같습니다.

- Athena Query 실행과 상태 조회
- Glue Catalog Database·Table 조회
- CUR Bucket과 Athena Result Bucket 읽기·쓰기
- 필요한 경우 Cost Explorer 또는 Pricing API 조회

IAM Policy를 `*`로 넓히기보다 대상 Bucket, Workgroup, Database를 제한합니다. Kubecost ServiceAccount와 IAM Role의 Trust Policy도 Namespace와 이름을 고정합니다.

Athena Query 자체도 비용이므로 CUR Partition과 압축 형식을 사용하고 불필요한 전체 Scan을 피합니다.

---

## 5. Allocation 기준

비용을 책임 단위에 연결하려면 Label 규약이 필요합니다.

| 기준 | 용도 | 주의점 |
|---|---|---|
| Namespace | 환경 또는 큰 조직 단위 | 공유 Namespace에서는 책임이 섞임 |
| Workload | Service별 비용 | Job과 임시 Workload 이름 정규화 필요 |
| Label | Team, Product, Cost Center | 누락·오타를 Admission 단계에서 통제 |
| Annotation | 외부 회계 코드 | 변경 이력과 허용 값 관리 필요 |

`team`, `product`, `environment`, `cost-center`처럼 안정된 Label을 Helm 공통 Template에서 강제하면 비용 미분류 영역을 줄일 수 있습니다.

사용자가 임의로 비용 Label을 바꿀 수 있다면 Showback 신뢰도가 떨어집니다. 허용 값 검증과 Ownership Review가 필요합니다.

---

## 6. Shared Cost 배분

CoreDNS, Ingress Controller, Istio, Observability, Jenkins 같은 Platform Workload는 특정 서비스 하나의 비용이 아닙니다. 배분 방식은 다음 중 하나를 선택합니다.

- 별도 Platform Cost로 유지
- Namespace 직접 비용 비율로 배분
- CPU·Memory 사용 비율로 배분
- Service별 고정 가중치로 배분

어떤 방식도 완벽하지 않으므로 반복 가능한 규칙이 더 중요합니다. 월마다 배분 공식을 바꾸면 추세 비교가 불가능합니다.

Prod 안정성을 위해 유지하는 여유 Capacity를 낭비로만 분류해서도 안 됩니다. Availability 목표에 필요한 Headroom과 진짜 Idle을 구분합니다.

---

## 7. Request Right-sizing

Kubecost Efficiency는 Request와 실제 사용의 관계를 보여줍니다.

```text
CPU Efficiency = CPU Usage / CPU Request
Memory Efficiency = Memory Usage / Memory Request
```

평균값만 보고 Request를 낮추면 Peak에서 Throttling이나 OOMKill이 발생합니다. 다음을 함께 봅니다.

- P95·P99 사용량
- 배포·Batch·월말 같은 주기적 Peak
- HPA 목표와 Scale-out 지연
- JVM Heap, Native Memory, Page Cache
- 장애 시 Traffic Failover로 늘어나는 부하

권장치는 자동 적용하지 않고 Pull Request로 검토합니다. 비용 절감은 SLO와 Error Budget을 훼손하지 않는 범위에서 수행합니다.

---

## 8. Karpenter와 비용 최적화

Kubecost는 어떤 Node Pool이 Idle한지 보여주고 Karpenter는 실제 Node 구성을 바꿉니다. 두 도구의 역할은 다릅니다.

- Kubecost: 비용과 비효율을 관찰하고 후보를 제시
- Karpenter: Pod 요구 조건을 만족하는 Node를 Provision·Consolidate

Spot 전환은 단가를 낮추지만 Interrupt 위험을 높입니다. Stateless, 재시도 가능한 Workload부터 적용하고 PDB, Topology Spread, Graceful Shutdown을 검증합니다.

Node Consolidation 직후 Kubecost 추정치가 흔들릴 수 있으므로 일·주 단위로 추세를 봅니다.

---

## 9. Network와 Storage 비용

Compute만 최적화하면 비용의 큰 부분을 놓칠 수 있습니다.

- Multi-AZ Traffic과 NAT Gateway Data Processing
- Internet Egress와 CDN Origin Traffic
- EBS Provisioned Capacity와 Snapshot
- Load Balancer 시간·LCU 비용
- Log·Metric·Trace 수집과 보존 비용

Service Mesh나 Observability는 직접 Node Resource뿐 아니라 Network와 Storage를 소비합니다. Signal별 보존 기간과 Sample Rate를 비용 모델에 포함합니다.

PVC가 Workload 삭제 후 남아 있거나 Snapshot Lifecycle이 없으면 사용하지 않는 Storage 비용이 지속됩니다.

---

## 10. Showback과 Chargeback

Showback은 팀에 사용 비용을 보여주지만 실제 예산을 청구하지 않습니다. Chargeback은 회계상 비용을 배부합니다. 초기에는 데이터 품질과 신뢰를 확보하기 위해 Showback부터 시작하는 편이 안전합니다.

월간 Report에는 다음을 포함할 수 있습니다.

- Team·Environment별 Total Cost와 전월 대비 변화
- 미분류 비용 비율
- Idle·Shared Cost
- Request Efficiency가 낮은 상위 Workload
- 비용 증가 원인: Traffic, 배포, 단가, Resource 설정
- 절감 실행과 SLO 영향

비용 숫자만 보내지 말고 변화 원인을 설명해야 팀이 행동할 수 있습니다.

---

## 11. 장애와 데이터 품질

대표적인 실패 양상은 다음과 같습니다.

- Prometheus Retention 부족으로 과거 Allocation이 비어 있음
- CUR Partition이나 Athena Table 오류로 실비용 보정 실패
- Label 변경으로 하나의 Service가 여러 항목으로 분리
- Cluster 이름 충돌로 다른 환경 비용이 합쳐짐
- Athena 권한 또는 Result Bucket 암호화 권한 부족
- Kubecost Upgrade 후 Metric 이름 변경

비용 합계가 AWS Bill과 정확히 일치하지 않을 수 있습니다. 지원 Fee, Tax, Credit, Shared Service 배분과 데이터 지연을 조정한 Reconciliation 기준을 정의합니다.

---

## 12. 운영 점검표

- [ ] Cluster·Environment·Team Label이 안정적으로 부여되는가
- [ ] 미분류 비용 비율을 추적하는가
- [ ] CUR/Athena 데이터 갱신 지연과 Query 실패를 감시하는가
- [ ] Shared Cost 배분 규칙이 문서화되어 있는가
- [ ] Right-sizing 제안에 Peak와 SLO가 반영되는가
- [ ] Network·Storage·Observability 비용을 함께 보는가
- [ ] 비용 변화가 배포·Traffic 변화와 연결되는가
- [ ] Kubecost IAM 권한이 최소 범위인가

---

## 13. 배포 사례 적용 진단과 개선 과제

Kubecost와 CUR/Athena 연결은 구성돼 있지만 Team·Product·Cost Center Label이 Chart 전반에서 강제되지 않으면 미분류 비용과 잘못된 Showback이 생깁니다. 공유 Platform·Idle 비용 배분 기준도 기술 설정만으로 결정되지 않습니다.

Helm/Admission Policy로 비용 Label을 필수화하고 미분류 비율을 경보합니다. Shared Cost 배분식을 문서화해 월별로 고정하며 Right-sizing은 P99·HPA·장애 Headroom을 포함한 PR 제안으로만 적용합니다.

완료 기준은 AWS Bill과 조정 가능한 차이를 설명할 수 있고 미분류 비용이 목표 이하이며, 비용 절감 변경이 SLO와 Resource Saturation을 악화시키지 않았다는 전후 검증이 남는 상태입니다.

---

# Reference

- [Kubecost Documentation](https://www.kubecost.com/install-and-configure/)
- [AWS Cost and Usage Reports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)
- [Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)
- [[Karpenter Node 자동 확장]]
- [[Kubernetes Workload 신뢰성]]
