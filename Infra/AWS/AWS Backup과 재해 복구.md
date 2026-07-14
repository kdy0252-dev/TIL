---
id: AWS Backup과 재해 복구
started: 2026-06-20
tags:
  - ✅DONE
  - AWS
  - Backup
  - Disaster-Recovery
group:
  - "[[Infra AWS]]"
---
# AWS Backup과 재해 복구

## 1. Backup과 복구는 다르다

Backup Job 성공은 서비스 복구 성공을 보장하지 않는다. 복구 순서, 암호화 Key, DNS, IAM, Application Version과 데이터 정합성이 함께 맞아야 한다.

- RPO는 허용 가능한 데이터 손실 시간이다.
- RTO는 서비스 복구까지 허용 가능한 시간이다.
- Backup Retention은 보관 기간이다.
- 복구 검증은 실제 사용 가능한지 확인하는 과정이다.

## 2. 데이터 분류

모든 Resource를 같은 주기로 백업하면 비용은 늘고 요구는 충족하지 못한다.

| 데이터 | 예시 | 전략 |
|---|---|---|
| 권위 데이터 | RDS 업무 데이터 | Snapshot, PITR, 교차 Region 복사 |
| 재생성 가능 | Cache, Search Index | 원본에서 재구축 절차 |
| Object | Upload, 정적 Asset | Versioning, Replication, Lifecycle |
| Cluster Volume | PVC | CSI Snapshot과 Application 정합성 |
| 설정 | Terraform, Helm, GitOps | Git과 State 백업, Secret 별도 관리 |

## 3. AWS Backup Plan

Tag 기반 Assignment로 보호 대상을 자동 포함하고 Schedule, Lifecycle, Vault와 Copy Action을 선언한다. 중요한 Recovery Point는 별도 계정과 Region의 Vault로 복사한다.

Backup Vault Lock은 보존 기간 전에 Recovery Point가 삭제되는 것을 막아 Ransomware 대응에 도움이 된다. 그러나 잘못된 보존 설정도 쉽게 되돌릴 수 없으므로 Governance Mode에서 검증한 뒤 적용한다.

## 4. RDS 복구

Automated Backup과 Point-in-time Recovery는 지정 시점으로 새 Database Instance를 만든다. 원래 Instance를 제자리에서 되감는 기능으로 오해하면 안 된다.

복구 후 Parameter Group, Security Group, KMS Key, Secret, DNS와 Connection Pool 전환이 필요하다. Multi-AZ는 가용성 기능이고 논리 삭제나 잘못된 Migration을 되돌리는 Backup이 아니다.

## 5. S3와 EBS

S3 Versioning은 덮어쓰기와 삭제 복구에 유용하지만 동일 계정 Credential 탈취에 대비하려면 Object Lock과 Cross-account Replication을 검토한다. EBS Snapshot은 Crash-consistent일 수 있으므로 Database나 File System의 Freeze와 Application 정합성을 고려한다.

## 6. EKS에서의 복구 범위

Deployment와 Config는 GitOps로 재생성할 수 있지만 CRD, 외부 Controller 상태, PVC와 Cluster 외부 AWS Resource는 별도다. Cluster 전체를 백업하기보다 무엇이 Git에서 복원되고 무엇이 Snapshot에서 복원되는지 경계를 작성한다.

## 7. 재해 복구 방식

```text
Backup & Restore < Pilot Light < Warm Standby < Multi-site
낮은 비용/긴 RTO                         높은 비용/짧은 RTO
```

모든 서비스에 Active-Active가 필요한 것은 아니다. 업무 영향과 RTO/RPO를 수치로 정한 뒤 적절한 방식을 선택한다.

## 8. “Snapshot이 있다”가 복구 계획이 아닌 이유

RDS Snapshot을 복원하면 새 Endpoint를 가진 Instance가 생긴다. Application Secret과 DNS를 바꾸고 Schema와 Application Version의 호환성을 확인해야 한다. 암호화 Key나 복구 Role을 잃었다면 Snapshot File이 존재해도 사용할 수 없다.

EKS 역시 GitOps Repository만 복원한다고 끝나지 않는다. CRD가 먼저 설치되어야 Custom Resource를 적용할 수 있고, PVC Data와 외부 Load Balancer·DNS·IAM 연결도 순서가 있다. 복구는 데이터 한 조각이 아니라 의존성 Graph를 다시 세우는 작업이다.

## 9. 복구 훈련에서 측정할 것

훈련은 Backup Job 성공 여부가 아니라 격리된 환경에서 실제 서비스를 올리는 과정이어야 한다. Recovery Point 선택 시간, Restore 대기, DNS 전환, Cache·Index 재구축과 검증 Query까지 시간을 나눠 측정한다.

복구된 데이터가 열리는지만 보지 말고 최신 Transaction 시각, Foreign Key 정합성, Object와 DB 참조 관계, Application의 핵심 사용자 흐름을 확인한다. 측정된 시간이 약속한 RTO보다 길다면 더 잦은 Snapshot이 아니라 복구 자동화나 Warm Standby가 필요할 수 있다.

## 10. 실무에서 빠지기 쉬운 설계

중앙 Backup Plan과 정기 Restore가 선언되지 않고 운영 Database가 Single-AZ라면 AZ 장애 대응과 논리적 데이터 복구가 모두 불확실하다. Multi-AZ를 켜도 삭제된 Row는 돌아오지 않고, Snapshot을 늘려도 Instance Failover는 빨라지지 않는다.

먼저 권위 데이터별 RPO와 RTO를 정하고 PITR, Versioning, Snapshot과 재생성 전략을 연결한다. Recovery Point는 운영자 Credential과 분리된 Vault에 복사하고, KMS·IAM·DNS를 포함한 전체 복구를 반복해야 한다.

## 11. 기억할 점

Backup은 Recovery Point를 만드는 기술이고 재해 복구는 업무를 다시 제공하는 능력이다. 두 능력의 차이는 정기 Restore와 측정된 RTO에서 드러난다.

# Reference
- [AWS Backup Developer Guide](https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html)
- [Restoring a DB instance to a specified time](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html)
- [Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)
