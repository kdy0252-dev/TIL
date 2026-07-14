---
id: CloudTrail Config GuardDuty Security Hub
started: 2026-06-23
tags:
  - ✅DONE
  - AWS
  - Security
  - Audit
group:
  - "[[Infra AWS]]"
---
# CloudTrail Config GuardDuty Security Hub

## 1. 예방 통제만으로는 부족하다

IAM과 Security Group은 잘못된 동작을 막는 예방 통제다. 하지만 허용된 Credential이 탈취되거나 설정이 나중에 변경되면 탐지와 조사 체계가 필요하다.

| 서비스 | 답하는 질문 |
|---|---|
| CloudTrail | 누가 어떤 AWS API를 언제 호출했는가 |
| AWS Config | Resource 설정이 어떻게 변했고 규칙을 지키는가 |
| GuardDuty | 행위와 신호에 위협 징후가 있는가 |
| Security Hub | 여러 보안 Finding을 어디서 우선순위화할 것인가 |

## 2. CloudTrail

Management Event와 필요한 Data Event를 조직·Region 범위 Trail로 수집한다. S3 Object 접근처럼 Data Event는 양이 많고 비용이 들므로 민감 Bucket과 핵심 Resource부터 선택한다.

Log Bucket은 별도 보안 계정에 두고 암호화, Public Access Block, 변경 방지와 수명 주기를 설정한다. Trail 중지, Bucket Policy 변경, KMS Key 비활성화는 즉시 경보한다.

## 3. AWS Config

Config는 현재 상태뿐 아니라 변경 Timeline을 제공한다. 규칙은 “Public S3 금지”, “암호화되지 않은 Volume 금지”처럼 기대 상태를 검사한다.

모든 규칙을 한꺼번에 켜면 비용과 예외 Noise가 커진다. 위험도가 높은 통제부터 적용하고 자동 Remediation은 안전하고 되돌릴 수 있는 항목에만 사용한다.

## 4. GuardDuty

GuardDuty는 CloudTrail, VPC Flow, DNS와 서비스별 신호를 분석한다. Finding은 확정 사고가 아니라 조사 우선순위를 높이는 단서다. Severity, Resource 중요도, 알려진 운영 행위와 함께 평가한다.

Access Key 악용이 의심되면 Key 비활성화만 하지 말고 Session, Role Trust, 최근 API 호출, 생성된 Resource와 Data Access를 조사한다.

## 5. Security Hub와 대응 흐름

Security Hub는 표준 준수 결과와 Finding을 모은다. EventBridge로 Ticket, Chat, Lambda 격리 Workflow에 연결할 수 있다.

```text
Finding -> 중복 제거와 심각도 보정
        -> 소유 팀 지정 -> 조사
        -> 격리/복구 -> 원인과 재발 방지
```

자동 격리는 오탐으로 운영 장애를 만들 수 있다. 인터넷에 공개된 Access Key처럼 확실한 조건과 승인형 조치를 분리한다.

## 6. 계정과 Region 범위

다중 계정에서는 Security 전용 Delegated Administrator를 정하고 새 계정과 새 Region이 자동 포함되게 한다. 한 Region만 활성화하면 사용하지 않는 Region에서 생성된 Resource를 놓칠 수 있다.

## 7. 하나의 보안 사건을 네 서비스로 읽기

평소 사용하지 않던 Region에 Public EC2 Instance가 생성됐다고 하자. CloudTrail은 어떤 Role이 `RunInstances`와 Security Group 변경을 호출했는지 보여준다. Config는 Resource가 언제 Public 상태가 됐는지와 규칙 위반을 기록한다. GuardDuty는 비정상 API 위치나 의심 Network 행위를 Finding으로 만들 수 있고, Security Hub는 관련 Finding을 모아 담당 Workflow로 보낸다.

네 서비스는 같은 Log를 중복 저장하는 도구가 아니다. 행위, 상태, 위협 신호와 대응 대기열이라는 서로 다른 관점을 연결한다.

## 8. 탐지에서 대응까지 끊기는 지점

Finding을 많이 생성해도 Owner와 대응 시간이 없으면 Dashboard의 숫자만 늘어난다. Severity가 높더라도 개발 Sandbox와 개인정보 Database의 우선순위는 다르다. Finding에 Account, Environment, Data Classification과 Resource Owner를 보강해야 한다.

자동 대응도 신중해야 한다. 탈취가 확실한 Access Key 비활성화와 애매한 Network Finding의 Instance 종료는 위험이 다르다. 되돌릴 수 있는 격리, 사람 승인, 완전 자동 조치를 조건별로 나눈다.

## 9. 실무에서 빠지기 쉬운 설계

Application Metric과 Log가 잘 수집돼도 조직 Trail, Config History와 위협 탐지가 없다면 AWS Control Plane에서 발생한 변경을 복원하기 어렵다. 특히 새 Account나 사용하지 않던 Region이 중앙 수집에서 빠지는 경우가 흔하다.

보완은 모든 Account·Region의 조직 Trail과 별도 Log Archive에서 시작한다. 그 위에 위험도가 높은 Config Rule과 GuardDuty를 켜고, Security Hub Finding에 Owner와 대응 SLA를 연결한다. 마지막 단계는 Credential 탈취를 가정한 훈련으로 실제 Timeline을 재구성하는 것이다.

## 10. 기억할 점

보안 관측성은 “누가 무엇을 바꿨는가”, “현재 상태는 안전한가”, “행동이 의심스러운가”, “누가 언제 대응할 것인가”를 모두 답해야 한다. 네 질문 가운데 하나라도 빠지면 탐지는 기록으로만 남거나 사고 조사가 추측에 의존한다.

# Reference
- [AWS CloudTrail User Guide](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html)
- [AWS Config Developer Guide](https://docs.aws.amazon.com/config/latest/developerguide/WhatIsConfig.html)
- [Amazon GuardDuty User Guide](https://docs.aws.amazon.com/guardduty/latest/ug/what-is-guardduty.html)
- [AWS Security Hub User Guide](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
