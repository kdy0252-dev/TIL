---
id: Firebase Cloud Messaging
started: 2026-06-14
tags:
  - ✅DONE
  - Infra
  - Firebase
  - Messaging
group:
  - "[[Infra]]"
---
# Firebase Cloud Messaging: 신뢰성 있는 Push 알림 처리

## 1. 개요 (Overview)
**Firebase Cloud Messaging(FCM)**은 서버가 Android, iOS, Web Client로 Push Message를 전송하는 서비스입니다. Java 서버에서는 Firebase Admin SDK를 사용하여 Device Token이나 Topic을 대상으로 메시지를 발송합니다.

Push 전송은 외부 네트워크 호출이며 사용자의 Device 상태에 따라 실패할 수 있으므로, 핵심 비즈니스 트랜잭션과 직접 결합하지 않는 것이 중요합니다.

---

## 2. 메시지 흐름

```text
Business Transaction
  -> Push Outbox 저장
  -> Scheduler가 발송 대상 Claim
  -> Firebase Admin SDK
  -> FCM
  -> Device
  -> 성공 / 재시도 / 영구 실패 기록
```

Outbox를 사용하면 비즈니스 데이터 커밋과 Push 요청 생성을 같은 로컬 트랜잭션에 포함하고, 실제 외부 전송은 별도 Worker가 처리할 수 있습니다.

---

## 3. 기본 발송

```java
Message message = Message.builder()
        .setToken(deviceToken)
        .setNotification(Notification.builder()
                .setTitle(title)
                .setBody(body)
                .build())
        .putData("screen", "BOOKING_DETAIL")
        .putData("bookingId", bookingId.toString())
        .build();

String messageId = FirebaseMessaging.getInstance().send(message);
```

Notification Payload는 OS가 표시를 담당하고, Data Payload는 앱이 화면 이동이나 추가 처리를 결정할 때 사용합니다. 민감한 개인정보를 Push Payload에 넣지 않아야 합니다.

---

## 4. 실패 분류

| 분류 | 예 | 처리 |
|---|---|---|
| 재시도 가능 | 일시적 네트워크 오류, 서버 과부하 | Backoff + Jitter 후 재시도 |
| 영구 실패 | 잘못되거나 만료된 Token | Token 비활성화 후 종료 |
| 설정 오류 | Credential, Project 불일치 | 즉시 알람, 재시도 제한 |
| 요청 오류 | Payload 크기·형식 오류 | 코드 또는 데이터 수정 |

모든 오류를 동일하게 재시도하면 유효하지 않은 Token 때문에 Queue가 계속 밀릴 수 있습니다.

---

## 5. 실무 사례 적용 관점
이 사례는 Firebase 설정과 FCM Adapter를 분리하고, Push Outbox를 Quartz Job이 Batch 단위로 처리합니다. 처리 상태, 최대 시도 횟수, 재시도 지연, 처리 Timeout과 Retention을 별도 정책으로 관리합니다.

이 구조의 핵심은 다음과 같습니다.

- Domain은 Firebase SDK에 직접 의존하지 않습니다.
- Out Port가 Push 발송 계약을 정의합니다.
- Adapter가 Firebase Message와 오류를 기술별 형태로 변환합니다.
- 동일 Outbox를 여러 인스턴스가 중복 발송하지 않도록 Claim 상태를 원자적으로 변경합니다.
- 오래된 성공·실패 이력을 주기적으로 정리합니다.

---

## 6. 운영 지표
- 대기·처리 중·성공·실패 Outbox 수
- 발송 지연 시간과 처리 시간
- 오류 코드별 실패율
- 재시도 횟수 분포
- 만료 Token 비율
- Scheduler가 마지막으로 성공한 시각

---

## 7. Token Lifecycle
Device Token은 영구 식별자가 아닙니다. 앱 재설치, Data 삭제, 복원과 FCM 정책에 따라 바뀌거나 만료됩니다.

```text
App Token 발급·갱신
  -> Backend 등록
  -> 사용자·Device 연결
  -> 발송
  -> UNREGISTERED 응답
  -> Token 비활성화
```

한 사용자가 여러 Device를 가질 수 있고 한 Device에서 계정이 바뀔 수 있습니다. Token을 사용자 ID의 단일 필드로만 저장하지 않고 Device·Session 관계와 마지막 확인 시각을 관리합니다.

## 8. Notification과 Data Message

| 유형 | Background | 앱 처리 | 용도 |
|---|---|---|---|
| Notification | OS가 표시 가능 | 제한적 | 단순 알림 |
| Data | 앱 코드가 처리 | 유연함 | 화면 이동·동기화 |
| 혼합 | OS 표시 + Data | 상태에 따라 다름 | 일반적인 Push |

Delivery는 즉시·정확히 한 번을 보장하지 않습니다. Push를 업무 상태의 Source of Truth로 사용하지 않고 앱이 API에서 최신 상태를 다시 조회하게 합니다.

## 9. Multicast와 Batch
다수 Token 발송은 Batch로 나누고 Token별 결과를 처리합니다. 전체 호출 성공이 모든 Token 성공을 뜻하지 않습니다.

```text
500 Tokens
  -> Batch Request
  -> Response[0..499]
  -> 성공 / 만료 / 재시도 분류
```

결과 Index가 입력 Token 순서와 대응되는지 SDK 계약을 확인하고, 개별 실패를 Outbox Target 상태에 반영합니다.

## 10. 중복과 순서
FCM은 Network와 재시도로 중복·지연 가능성이 있습니다. Payload에 Event ID와 업무 Version을 넣고 Client가 이미 처리한 Event나 오래된 상태를 무시하게 할 수 있습니다.

동일 Booking의 변경·취소 알림 순서가 뒤바뀌어도 앱은 API의 현재 상태를 우선해야 합니다.

## 11. TTL과 Collapse
- TTL: 오래된 알림의 전달 가치가 사라지는 시간
- Collapse Key: 아직 전달되지 않은 유사 메시지를 최신 하나로 대체
- Priority: 긴급 메시지와 일반 동기화 구분

모든 메시지를 높은 Priority로 보내면 Device Battery와 Platform 제한에 악영향을 줍니다.

## 12. Outbox 상태와 Exactly-once 환상
DB Claim으로 Server Worker의 중복 처리를 줄여도 FCM 응답 Timeout 뒤 실제 전달 여부는 알 수 없습니다. 같은 Event ID로 재시도하고 Client 중복 방지를 결합합니다.

## 13. Credential
Firebase Service Account Key 파일을 Image나 Git에 넣지 않습니다. Workload Identity Federation 또는 안전한 Secret 주입을 사용하고 Project ID가 환경별로 섞이지 않게 합니다.

## 14. 테스트
- Firebase Adapter Unit Test: Message 변환과 오류 분류
- WireMock·Fake: HTTP 오류와 Timeout
- Test Project Integration: 실제 Token 발송
- Outbox Integration: Claim·Retry·Retention
- Mobile E2E: Foreground·Background·종료 상태

운영 사용자에게 Test Push가 가지 않도록 Project와 Token을 격리합니다.

---

## 15. 실무 사례 적용 진단과 개선 과제

Firebase Admin SDK와 Timeout Test가 존재하지만 Token Lifecycle, Invalid Token 제거, 중복·순서, 대량 발송의 부분 실패를 운영 관점에서 더 표준화해야 합니다. Push 성공 응답은 단말 표시 성공을 뜻하지 않습니다.

발송 요청에 업무 Idempotency Key를 두고 Token별 결과를 저장해 영구 오류 Token을 비활성화합니다. Batch 크기, TTL, Collapse Key를 알림 유형별로 정의하고 Provider 지연·오류율·Invalid Token 비율을 Metric으로 냅니다. Credential은 Workload Identity 또는 Secret Manager로 회전합니다.

완료 기준은 동일 Event 재처리 시 업무 알림이 중복 생성되지 않고, 부분 실패만 안전하게 재시도하며, 만료 Token 정리와 Credential Rotation을 무중단으로 검증한 상태입니다.

---

# Reference
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [Firebase Admin Java SDK](https://firebase.google.com/docs/admin/setup)
- [[Transactional Outbox 패턴]]
