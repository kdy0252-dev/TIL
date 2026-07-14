---
id: AWS Secrets Manager와 KMS Envelope Encryption
started: 2026-06-22
tags:
  - ✅DONE
  - AWS
  - Security
  - KMS
group:
  - "[[Infra AWS]]"
---
# AWS Secrets Manager와 KMS Envelope Encryption

## 1. Secret 관리는 저장 위치만의 문제가 아니다

Database Password를 Git에서 Secrets Manager로 옮겼다고 끝나지 않는다. 생성, 암호화, 전달, 사용, 회전, 폐기와 감사까지 전체 수명 주기를 설계해야 한다.

```text
생성 -> 암호화 저장 -> 권한 있는 Workload에 전달
    -> 사용과 감사 -> 회전 -> 이전 값 폐기
```

Kubernetes Secret은 기본적으로 Base64 표현일 뿐이다. etcd 암호화, RBAC, 외부 Secret Store와 전달 방식이 함께 필요하다.

## 2. Envelope Encryption

Secrets Manager는 Secret 값을 Data Key로 암호화하고 Data Key를 KMS Key로 다시 암호화하는 Envelope Encryption을 사용한다. 큰 데이터를 KMS가 직접 매번 암호화하는 대신 빠른 대칭 Data Key와 중앙 Key 통제를 결합한다.

조회 시 호출자는 `secretsmanager:GetSecretValue`뿐 아니라 Customer Managed Key를 사용한다면 적절한 `kms:Decrypt` 권한도 필요하다. Key Policy와 IAM Policy 중 한쪽만 보고 판단하면 권한 오류나 과도한 허용이 생긴다.

## 3. AWS 관리 Key와 Customer Managed Key

AWS 관리 Key는 시작이 간단하다. Customer Managed Key는 Key Policy, Rotation, Cross-account, 비활성화와 삭제 통제를 세밀하게 설계할 수 있다.

환경별 격리와 규제 요구가 크면 Key를 분리하되 Secret마다 Key를 하나씩 만드는 과도한 분리는 피한다. Key 삭제는 복구 불가능한 Data Loss로 이어질 수 있으므로 대기 기간과 승인 절차가 필요하다.

## 4. Runtime 전달 방식

### 애플리케이션이 직접 조회

AWS SDK로 필요할 때 조회하고 짧게 Cache한다. 최신 값 반영과 감사가 명확하지만 API 장애, 비용, Cold Start와 Cache 만료 정책을 고려해야 한다.

### External Secrets Operator

외부 Secret을 Kubernetes Secret으로 동기화한다. 기존 애플리케이션과 호환되지만 값이 etcd와 Namespace에 복제된다. Refresh Interval과 삭제 정책, Operator 권한이 중요하다.

### Secrets Store CSI Driver

Secret을 Volume File로 Mount할 수 있다. Environment Variable보다 Process Dump와 `/proc` 노출을 줄일 수 있지만 File 변경을 Application이 다시 읽는지 검증해야 한다.

## 5. Environment Variable의 함정

환경 변수는 설정이 간단하지만 Pod 명세, 진단 출력, Crash Report와 Child Process로 노출될 수 있고 실행 중 값 교체가 어렵다. Secret 값을 Log에 출력하지 않고 Actuator의 환경 정보도 마스킹한다.

## 6. Rotation

Rotation은 값을 바꾸는 기능이 아니라 Consumer가 중단 없이 새 값으로 넘어가는 Protocol이다.

```text
새 Credential 생성
 -> 새 값 검증
 -> Consumer 전환
 -> 이전 연결 Drain
 -> 이전 Credential 폐기
```

Database는 새 Password 반영 시 Connection Pool의 기존 Connection과 신규 Connection이 섞인다. 즉시 이전 값을 폐기하면 정상 요청이 실패할 수 있다. 다중 사용자 Rotation 또는 짧은 중첩 기간을 고려하고 실패 시 Rollback 경로를 둔다.

## 7. 권한과 감사

- Secret ARN을 환경과 서비스 단위로 제한한다.
- `ListSecrets`와 Wildcard Resource를 기본 권한으로 주지 않는다.
- Resource Policy로 Cross-account 접근과 Public Access를 검토한다.
- CloudTrail에서 조회와 정책 변경을 탐지한다.
- Secret 값 자체는 Log와 Alarm Message에 포함하지 않는다.

## 8. Terraform과 Helm을 통과할 때 생기는 복제본

Secret을 변수로 받는 Terraform Resource는 값을 State에 남길 수 있다. `sensitive = true`는 CLI 출력의 마스킹이지 State 암호화가 아니다. Helm Values에 평문 값을 만들면 CI Workspace, Artifact, Argo CD Diff와 Kubernetes Secret까지 복제될 수 있다.

따라서 IaC는 Secret 값 자체보다 Secret ARN과 접근 관계를 선언하는 편이 안전하다. Runtime에 Pod가 임시 AWS Credential로 값을 읽으면 배포 Pipeline이 평문을 알 필요가 없다. 외부 Secret Operator를 사용한다면 동기화된 Kubernetes Secret 역시 보호 대상이라는 사실은 변하지 않는다.

## 9. Rotation 중 실제로 일어나는 일

Database Password를 회전했다고 가정하자. Secrets Manager의 값은 바뀌었지만 이미 열린 Connection은 이전 인증으로 계속 살아 있고, 새 Connection부터 새 Password를 요구한다. Application Cache가 오래된 값을 들고 있다면 Pool 확장이나 재연결 순간에만 간헐적 인증 실패가 나타난다.

이 문제는 새 Credential을 먼저 허용하고 Consumer가 새 값을 읽는 것을 확인한 뒤 이전 Credential을 폐기하는 방식으로 완화한다. Rotation Test는 API 성공 여부가 아니라 Connection Pool 재생성, Pod 재시작, 일시적 AWS API 실패까지 포함해야 한다.

## 10. 실무에서 빠지기 쉬운 설계

평문을 받을 수 있는 Terraform·Helm 경로만 있고 외부 Secret Store가 없다면 값은 Git 밖에서도 State, CI Log와 Generated File에 남을 수 있다. 이때 “Kubernetes Secret으로 옮겼다”는 해결이 아니다.

보완의 핵심은 Secret 종류와 복제 지점을 먼저 그리는 것이다. 이후 Secrets Manager와 KMS 경계를 정하고, Workload Identity로 Secret별 조회 권한을 부여하며, 직접 조회·CSI·동기화 중 한 소비 모델을 선택한다. 마지막에는 실제 회전 동안 오류율과 재연결을 관측한다.

## 11. 기억할 점

Secret 보안의 중심은 암호문 저장이 아니라 평문이 존재하는 시간과 장소를 최소화하는 것이다. 누가 읽었는지 추적할 수 있고, 유출 시 짧은 시간 안에 새 값으로 교체되며, Consumer가 중단 없이 따라갈 때 비로소 수명 주기가 완성된다.

# Reference
- [Secrets Manager encryption and decryption](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html)
- [Rotate AWS Secrets Manager secrets](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)
- [Good practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/)
