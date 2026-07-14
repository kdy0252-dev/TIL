---
id: CRD와 Operator Reconciliation 설계
started: 2026-06-30
tags:
  - ✅DONE
  - K8S
  - CRD
  - Operator
  - Reconciliation
group:
  - "[[Infra K8S]]"
---
# CRD와 Operator Reconciliation 설계

## 1. Kubernetes를 확장한다는 의미

CRD는 Kubernetes API에 새로운 Resource Type을 추가한다. Controller가 CRD의 Desired State를 읽고 실제 상태를 맞추면 Operator Pattern이 된다.

```text
사용자: Database.spec.replicas = 3
Controller: 현재 Replica 관찰 -> 차이 계산 -> Resource 생성/수정
Status: Ready replicas = 3, Condition = Ready
```

핵심은 명령을 한 번 실행하는 것이 아니라 상태가 계속 어긋날 수 있다고 보고 반복해서 수렴시키는 Control Loop다.

## 2. Spec과 Status

`spec`은 사용자가 원하는 상태이고 `status`는 Controller가 관찰한 결과다. Controller가 Spec에 실행 결과를 써넣으면 GitOps와 경쟁하고 사용자의 의도를 변경하게 된다.

Status에는 단순 Boolean보다 Condition을 사용한다. `type`, `status`, `reason`, `message`, `observedGeneration`을 기록하면 현재 Status가 최신 Spec을 반영했는지 알 수 있다.

## 3. Reconciliation은 멱등적이어야 한다

같은 Event가 중복 전달되거나 Controller가 재시작될 수 있다. Reconcile을 여러 번 실행해도 추가 Resource가 계속 생기지 않고 같은 Desired State로 수렴해야 한다.

```text
나쁜 방식: Event 수신 -> 무조건 새 Job 생성
좋은 방식: Desired Job 이름/상태 확인 -> 없거나 달라졌을 때만 변경
```

외부 API 호출도 Idempotency Key, 현재 상태 조회와 Retry 분류가 필요하다. Kubernetes Event 전달을 정확히 한 번이라고 가정하지 않는다.

## 4. Owner Reference와 Garbage Collection

Controller가 만든 Deployment와 Service에 Custom Resource를 Owner로 지정하면 Owner 삭제 시 종속 Resource도 Garbage Collection할 수 있다. Cluster Scope와 Namespace Scope 관계, Controller Owner의 단일성 규칙을 이해해야 한다.

외부 Cloud Resource는 Kubernetes Garbage Collector가 삭제할 수 없다. 이때 Finalizer를 사용해 외부 정리를 마친 뒤 Custom Resource 삭제를 완료한다.

## 5. Finalizer가 삭제를 멈추는 방식

Finalizer가 있는 Resource를 삭제하면 즉시 사라지지 않고 `deletionTimestamp`가 설정된다. Controller는 외부 Database나 DNS를 정리한 뒤 Finalizer를 제거한다.

외부 API가 영구 실패하거나 Controller가 사라지면 Resource가 Terminating에 갇힌다. 정리 작업은 재시도 가능하고 멱등적이어야 하며, 수동 복구 절차도 있어야 한다. Finalizer를 강제로 제거하면 외부 Resource가 고아로 남을 수 있다.

## 6. Requeue와 오류 처리

모든 실패를 같은 간격으로 무한 재시도하면 장애 난 외부 API를 더 압박한다. 일시 오류는 Exponential Backoff, 사용자 Spec 오류는 Status Condition 갱신 후 변경 Event 대기, 긴 작업은 진행 상태를 기록하고 재진입 가능하게 만든다.

Controller가 한 Resource의 느린 작업 때문에 전체 Queue를 막지 않도록 Worker 동시성과 외부 API Rate Limit을 함께 조절한다.

## 7. CRD Schema와 Versioning

OpenAPI Schema로 필수 필드, Enum, Pattern과 구조를 검증한다. Schema가 느슨하면 잘못된 Spec이 저장된 뒤 Controller 깊은 곳에서 실패한다.

`v1alpha1`에서 `v1beta1`, `v1`으로 발전할 때 Served Version과 Storage Version을 구분한다. 두 Version의 Schema가 다르면 Conversion Webhook이 필요할 수 있다. Field를 제거하거나 의미를 바꾸는 것은 API 사용자와의 호환성 문제다.

## 8. 언제 Operator를 만들지 말아야 할까

한 번 실행하는 배포 Script나 단순 Config 묶음은 Helm과 Job으로 충분할 수 있다. Operator는 Controller 운영, CRD Versioning, 권한, Upgrade와 장애 대응이라는 장기 비용을 만든다.

반복적인 상태 관찰, 자동 복구, 순서 있는 Upgrade·Backup처럼 도메인 운영 지식을 지속적으로 실행해야 할 때 가치가 크다.

## 9. 실무에서 빠지기 쉬운 설계

EKS Add-on, Argo Rollouts, Gateway API와 Observability Stack은 이미 여러 CRD와 Controller에 의존한다. 이를 단순 YAML Resource로만 보면 Controller 중단, CRD Version 불일치와 Finalizer 교착을 진단하기 어렵다.

각 Operator의 소유 Resource, Reconciliation 상태, CRD Upgrade 순서와 실패 시 영향 범위를 기록한다. Application Metric만이 아니라 Work Queue Depth, Reconcile Error, Duration과 오래된 Generation을 관측해야 한다.

## 10. 기억할 점

Operator는 Kubernetes 안에서 실행되는 자동화 Script가 아니다. Desired State와 Actual State의 차이를 반복적으로 줄이는 작은 분산 시스템이다. 멱등성, 상태 표현, 재시도와 API 호환성이 설계의 중심이다.

# Reference
- [Kubernetes Operator Pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Custom Resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
- [Finalizers](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/)
