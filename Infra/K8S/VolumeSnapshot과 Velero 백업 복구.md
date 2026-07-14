---
id: VolumeSnapshot과 Velero 백업 복구
started: 2026-07-13
tags:
  - ✅DONE
  - K8S
  - Backup
  - Storage
  - Velero
group:
  - "[[Infra K8S]]"
---
# VolumeSnapshot과 Velero 백업 복구

## 1. YAML 백업과 데이터 백업은 다르다

Kubernetes Resource YAML을 저장하면 Deployment와 Service는 다시 만들 수 있지만 PVC의 Block Data는 돌아오지 않는다. 반대로 Volume Snapshot만 있으면 어떤 StatefulSet과 Secret, StorageClass가 그것을 사용했는지 알기 어렵다.

```text
Cluster Resource: Namespace, CRD, Deployment, Service, Secret Metadata
Persistent Data : PVC가 가리키는 Volume 내용
External State  : RDS, S3, DNS, IAM처럼 Cluster 밖의 Resource
```

복구 설계는 세 범위를 연결해야 한다.

## 2. CSI VolumeSnapshot

VolumeSnapshot API는 Snapshot 요청을 Kubernetes Resource로 표현하고 CSI Driver가 실제 Storage Snapshot을 만든다.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: data-snapshot
spec:
  volumeSnapshotClassName: ebs-snapshot
  source:
    persistentVolumeClaimName: data
```

VolumeSnapshot, VolumeSnapshotContent와 실제 Cloud Snapshot은 PVC/PV와 비슷한 관계를 가진다. Retain/Delete Policy가 Kubernetes Object 삭제 시 Cloud Snapshot을 보존할지 결정한다.

## 3. Crash-consistent와 Application-consistent

Storage Snapshot은 특정 시점의 Block 상태를 보존하지만 Database Buffer와 진행 중 Transaction이 모두 안전하게 반영됐다는 뜻은 아니다. Crash-consistent Snapshot은 전원 장애 후 재시작 가능한 수준이고, Application-consistent Snapshot은 Application이 Flush·Freeze 또는 Backup Protocol을 수행한 상태다.

Database가 RDS에 있다면 Kubernetes PVC Snapshot보다 RDS PITR이 권위 데이터 보호 수단이다. PVC에 직접 Database를 운영한다면 Pre-hook, Native Backup과 복구 Test를 설계한다.

## 4. Velero의 역할

Velero는 Kubernetes API Resource를 Object Storage에 백업하고 Plugin을 통해 Volume Snapshot이나 File System Backup을 조정한다. Helm Chart가 Git에 있어도 Runtime에 생성된 Namespace Resource, CRD Instance와 특정 시점 상태를 보존할 때 유용하다.

하지만 GitOps와 Velero가 같은 Resource를 동시에 복원하면 Desired State 경쟁이 생길 수 있다. 기반 CRD와 Controller는 GitOps로 설치하고, 그 다음 필요한 Custom Resource와 Data를 복원하는 순서를 정한다.

## 5. Backup Hook

Velero Hook으로 Snapshot 전 Application Command를 실행할 수 있다. Freeze가 오래 걸리거나 Hook 실패를 무시하면 서비스 영향 또는 불완전 Backup이 생긴다. Timeout, 실패 정책과 Unfreeze 보장을 함께 둔다.

일관성 요구가 높은 Database는 범용 Hook보다 Database Native Backup과 Log 기반 PITR을 우선 검토한다.

## 6. 다른 Cluster로 복원할 때

StorageClass 이름, CSI Driver, Availability Zone, IAM Role, KMS Key와 VolumeSnapshotClass가 달라질 수 있다. 원본 Cluster 내부에서 복원 성공했다고 Region 재해 복구가 검증된 것은 아니다.

CRD가 없으면 Custom Resource를 이해할 수 없고, Webhook Service가 준비되기 전에 Resource를 적용하면 Admission이 실패한다. Platform Component, CRD, Namespace Policy, Workload, Data 순서를 설계한다.

## 7. Backup 자체를 보호하기

Velero Object Storage Credential이 운영 Cluster에 있고 같은 Account에서 Backup 삭제 권한까지 가지면 Cluster 침해가 Backup 삭제로 이어질 수 있다. 별도 Account Bucket, Object Lock, 제한된 KMS Key와 삭제 권한 분리를 고려한다.

Backup Retention과 Snapshot Lifecycle은 따로 움직일 수 있으므로 고아 Snapshot과 조기 삭제를 함께 감시한다.

## 8. 실무에서 빠지기 쉬운 설계

GitOps가 있다는 이유로 Cluster Backup이 불필요하다고 생각하거나, EBS Snapshot이 있다는 이유로 모든 상태가 복구된다고 생각하기 쉽다. 실제로는 어떤 Resource가 Git의 Desired State이고 어떤 Data가 Runtime의 유일한 원본인지 분류가 먼저다.

PVC를 사용하는 Workload가 있다면 VolumeSnapshot과 Velero 또는 Native Backup 중 책임을 명확히 하고, 새 Cluster에서 순서대로 복원한다. 정기 Test에는 Application Query와 사용자 흐름까지 포함한다.

## 9. 기억할 점

Kubernetes Backup은 Cluster를 사진처럼 통째로 저장하는 기술이 아니다. 선언 상태, 지속 데이터와 외부 서비스를 서로 다른 복구 수단으로 보호하고 올바른 순서로 재결합하는 과정이다.

# Reference
- [Kubernetes Volume Snapshots](https://kubernetes.io/docs/concepts/storage/volume-snapshots/)
- [Velero Documentation](https://velero.io/docs/)
- [[AWS Backup과 재해 복구]]
