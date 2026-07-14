---
id: Temporal 비동기 워크플로우 패턴 (Callback & MQ)
started: 2026-01-27
tags:
  - Temporal
  - Workflow
  - Architecture
group:
  - "[[Temporal]]"
---

# Temporal 비동기 워크플로우 패턴 가이드 (Callback & MQ)

## 1. 개요 (Overview)
Temporal 워크플로우에서 가장 강력한 기능 중 하나는 외부 시스템과의 **비동기 상호작용**을 처리하는 정교한 방식이다. 일반적인 HTTP 비동기 호출은 단순히 응답을 기다리지 않는 Non-blocking 방식이지만, Temporal의 비동기 패턴은 시스템 리소스를 완전히 해제한 상태에서 외부의 응답이 올 때까지 워크플로우의 상태를 안전하게 보존한다.

본 문서는 외부 시스템(예: 타 서비스의 비동기 API, 메시지 큐 등)과의 연동 시 사용할 수 있는 핵심 패턴인 **Asynchronous Activity Completion**과 **MQ Signal/Wait Pattern**에 대해 상세히 기술한다.

---

## 2. Asynchronous Activity Completion (콜백 방식)
이 패턴은 액티비티가 즉시 완료되지 않고 외부 시스템으로부터 "완료 알림(Callback)"을 받을 때까지 대기 상태로 남아있는 방식이다. 오케스트레이터가 작업을 요청(Event)만 하고, 실제 작업이 끝났다는 보고를 받을 때까지 스레드를 점유하지 않는 진정한 의미의 비동기 워크플로우를 구현할 수 있다.

### 2.1 동작 원리
1. **Task Token 발행**: 액티비티 실행 시 Temporal 서버가 생성한 고유한 `TaskToken`을 획득한다.
2. **요청 발송**: 외부 서비스에 요청을 보낼 때 이 `TaskToken`을 함께 전달한다.
3. **상태 보존**: 액티비티 메서드는 종료되지만, Temporal 서버에는 "아직 완료되지 않음"으로 표시된다.
4. **외부 응답**: 작업을 끝낸 외부 시스템이 `TaskToken`과 결과를 담아 콜백 API를 호출한다.
5. **액티비티 완료**: 오케스트레이터의 `ActivityCompletionClient`가 해당 토큰을 찾아 액티비티를 성공(또는 실패) 처리한다.

### 2.2 단계별 구현 방법

#### 1단계: Activity 구현 변경 (Orchestrator)
액티비티가 요청을 보낸 후 즉시 리턴하되, `doNotCompleteOnReturn()`을 호출하여 대기 상태를 유지한다.

```java
import io.temporal.activity.Activity;
import io.temporal.activity.ActivityExecutionContext;
import java.util.Base64;

public class VehicleRegistrationActivitiesImpl implements VehicleRegistrationActivities {

    @Override
    public void registerVehicle(VehicleActivityDto vehicleDetails) {
        // 1. 현재 액티비티의 컨텍스트와 고유 태스크 토큰 획득
        ActivityExecutionContext context = Activity.getExecutionContext();
        byte[] taskToken = context.getTaskToken();
        String tokenString = Base64.getEncoder().encodeToString(taskToken);

        // 2. 외부 서비스(EU)에 요청 전송 (토큰을 포함)
        restClient.post()
                .uri("/api/v3/vehicles")
                .header("X-Temporal-Token", tokenString)
                .body(vehicleDetails)
                .retrieve()
                .toBodilessEntity();

        // 3. 메서드가 리턴되어도 액티비티가 완료되지 않도록 설정
        context.doNotCompleteOnReturn();
    }
}
```

#### 2단계: 콜백 수신용 API 생성 (Orchestrator)
외부 시스템이 작업을 마치고 호출할 Webhook 엔드포인트를 정의한다.

```java
@RestController
@RequiredArgsConstructor
public class ActivityCallbackController {
    private final ActivityCompletionClient completionClient;

    @PostMapping("/api/callback/vehicle-registration")
    public void completeRegistration(@RequestBody CallbackRequest request) {
        byte[] token = Base64.getDecoder().decode(request.getToken());

        if (request.isSuccess()) {
            // 해당 토큰의 액티비티를 성공으로 처리하고 결과 데이터 전달
            completionClient.complete(token, request.getResult());
        } else {
            // 실패 원인과 함께 액티비티를 실패 처리
            completionClient.reportFailure(token, new RuntimeException(request.getErrorMessage()));
        }
    }
}
```

#### 3단계: 외부 서비스 로직 변경 (External Service)
요청 시 받은 토큰을 저장해두었다가 비동기 작업이 완료되는 시점에 콜백을 보낸다.

1. 요청 헤더(`X-Temporal-Token`)에서 토큰을 추출하여 DB나 컨텍스트에 저장한다.
2. 실제 비즈니스 로직(예: 차량 등록)을 수행한다.
3. 작업 완료 후 오케스트레이터의 콜백 API로 토큰과 결과값을 전송한다.

---

## 3. MQ(Message Queue) 기반 비동기 응답 패턴
메시지 큐를 사용하여 통신하는 환경에서도 비동기 처리가 필요하다. 이때는 앞서 설명한 콜백 방식보다 **Signal**을 활용하는 방식이 더 권장된다.

### 3.1 패턴 1: Send & Wait Signal (권장 방식)
액티비티는 단순히 큐에 메시지를 발행하는 역할만 수행하고, 워크플로우 레벨에서 특정 시그널이 올 때까지 `Workflow.await`을 통해 대기한다.

#### 구현 흐름
1. **Activity**: 메시지 큐에 요청을 넣고 즉시 성공 리턴한다. (작업 지시 완료)
2. **Workflow**: `Workflow.await`을 호출하여 응답 시그널이 올 때까지 멈춘다.
3. **External System**: 큐에서 메시지를 꺼내 처리한 후, Temporal Client를 사용하여 해당 Workflow ID로 시그널을 보낸다.
4. **Resumption**: 시그널을 받는 즉시 워크플로우가 재개된다.

#### 코드 예시 (Workflow)
```java
public class RegistrationWorkflowImpl implements RegistrationWorkflow {
    private boolean registrationFinished = false;
    private String registrationResult;

    @Override
    public void start(VehicleDto details) {
        // 1. 메시지 발송 (액티비티는 발행 즉시 종료)
        activities.sendRegistrationMessageToQueue(details);

        // 2. 외부로부터 시그널이 올 때까지 대기 (타임아웃 적용 가능)
        boolean signaled = Workflow.await(Duration.ofHours(24), () -> this.registrationFinished);

        if (!signaled) {
            throw new RuntimeException("차량 등록 응답 타임아웃 발생");
        }

        // 다음 비즈니스 로직 진행...
    }

    @Override
    public void signalRegistrationResult(String result) {
        this.registrationResult = result;
        this.registrationFinished = true; // await 조건 충족
    }
}
```

### 3.2 패턴 2: Async Activity Completion with MQ
섹션 2의 콜백 방식과 동일하지만, 완료 보고를 HTTP가 아닌 MQ 응답 큐를 통해 수행하는 방식이다.

- **Activity**: `TaskToken`을 메시지에 담아 큐에 발행하고 `doNotCompleteOnReturn()` 호출.
- **Consumer**: 오케스트레이터의 응답 큐 Consumer가 메시지를 받으면, 내부의 `TaskToken`을 꺼내 `completionClient.complete()`를 호출.
- **특징**: 토큰을 시스템 간에 계속 전달(Propagate)해야 한다는 번거로움이 있다.

---

## 4. Spring Modulith 이벤트 기반 비동기 패턴
동일한 프로세스(Lighthouse 내 모듈 간) 내에서 비동기적으로 작업을 처리하고 싶은 경우, Spring Modulith의 이벤트를 활용한다. 이는 외부 시스템(MQ 등) 없이도 데이터베이스를 활용한 **Transactional Outbox Pattern**을 가장 간단하게 구현할 수 있는 방법이다.

### 4.1 동작 방식
1. **발행**: 액티비티 내에서 `ApplicationEventPublisher`를 통해 이벤트를 발행한다.
2. **저장**: 발행된 이벤트는 비즈니스 로직과 동일한 트랜잭션 내에서 `EVENT_PUBLICATION` 테이블에 저장된다.
3. **수신**: 다른 모듈의 `@ApplicationModuleListener`가 이벤트를 비동기적으로 처리한다.
4. **보장**: 만약 리스너 처리 중 서버가 다운되어도, DB에 저장된 정보를 바탕으로 재시작 시 자동 재실행된다.

### 4.2 실제 코드 예시

#### 1단계: 도메인 이벤트 정의
```java
// Immutable한 Java Record 사용을 권장한다
public record VehicleRegisteredEvent(
    String vehicleId,
    String ownerName,
    LocalDateTime registeredAt
) {}
```

#### 2단계: 액티비티에서 이벤트 발행
```java
@Component
@RequiredArgsConstructor
public class InternalRegistrationActivitiesImpl implements InternalRegistrationActivities {
    private final ApplicationEventPublisher eventPublisher;

    @Override
    @Transactional
    public void publishRegistrationSuccess(String vehicleId) {
        // 비즈니스 로직 수행 후 이벤트 발행
        // 이 시점에 DB의 EVENT_PUBLICATION 테이블에 기록된다
        eventPublisher.publishEvent(new VehicleRegisteredEvent(vehicleId, "홍길동", LocalDateTime.now()));
    }
}
```

#### 3단계: 다른 모듈에서 비동기 수신
```java
@Component
@RequiredArgsConstructor
public class InsuranceModuleListener {

    // @ApplicationModuleListener는 @Async + @TransactionalEventListener의 조합이다
    @ApplicationModuleListener
    public void on(VehicleRegisteredEvent event) {
        log.info("차량 등록 이벤트 수신: {}", event.vehicleId());
        // 보험 가입 등 후속 비동기 로직 수행
    }
}
```

---

## 5. 패턴 비교 및 선택 가이드

| 비교 항목 | Asynchronous Activity Completion | Send & Wait Signal Pattern (MQ) |
| :--- | :--- | :--- |
| **복잡도** | 중간 (TaskToken 관리 필요) | 낮음 (WorkflowID만 사용) |
| **리소스 효율** | 매우 높음 (대기 중 스레드 미점유) | 매우 높음 (대기 중 스레드 미점유) |
| **추적성** | Pending Activity로 모니터링 가능 | Workflow 상태가 Awaiting 상태로 표시됨 |
| **재표현성** | 외부 시스템이 토큰을 반드시 보관해야 함 | Workflow ID만 알면 어디서든 시그널 가능 |
| **권장 상황** | 1:1 HTTP 콜백 구조일 때 | MQ를 사용하거나 시그널 기반 협업 시 |

### 왜 "Send & Wait Signal"을 더 추천하는가?
1. **결합도 분리**: 액티비티는 "메시지 발송"이라는 자신의 역할만 수행하고 깔끔하게 종료된다.
2. **가독성**: 워크플로우 코드상에서 비즈니스 흐름(요청 -> 대기 -> 응답 처리)이 한눈에 들어온다.
3. **운영 편의성**: 외부 시스템이 장애로 인해 토큰을 잃어버려도, 수동으로 해당 워크플로우에 시그널을 보내 강제 재개가 가능하다.

---

## 5. 구현 시 주의사항

### 5.1 타임아웃 설정 (Timeout)
- **Activity Timeout**: 콜백 방식 사용 시 `StartToCloseTimeout`을 충분히 길게(예: 작업 예상 시간보다 길게) 설정해야 한다. 액티비티가 Pending 상태에서 이 시간이 지나면 타임아웃 오류가 발생한다.
- **Workflow Await Timeout**: 시그널 방식 사용 시 `Workflow.await`의 첫 번째 인자로 최대 대기 시간을 명시하여 좀비 워크플로우가 생기는 것을 방지해야 한다.

### 5.2 멱등성 (Idempotency)
외부 시스템이 중복 응답을 보내거나, 네트워크 순서가 꼬일 수 있다.
- **Signal**: 동일한 시그널이 여러 번 와도 안전하도록 플래그 체크 로직을 넣는다.
- **Completion**: `ActivityCompletionClient.complete()`는 이미 완료된 토큰에 대해 호출되면 에러를 던지므로 예외 처리가 필요하다.

### 5.3 보안 (Security)
- `TaskToken`은 민감한 정보를 담고 있지 않지만, 외부로 노출되는 값이다. Base64 인코딩을 통해 안전하게 전달해야 하며, 콜백 엔드포인트에 대한 인증(API Key 등) 절차를 마련하는 것이 좋다.

---

## 6. 결론
Temporal의 비동기 패턴은 복잡한 분산 시스템 간의 조율(Orchestration)을 단순하고 견고하게 만들어준다. 특히 장시간 실행되는 작업(Long-running Process)의 경우, 스레드 리소스를 낭비하지 않는 이러한 비동기 패턴 도입이 필수적이다.

Lighthouse와 같은 모듈 모놀리스 환경에서는 **Spring Modulith 이벤트**를 통한 내부 비동기 처리와, 외부 협업을 위한 **Temporal Signal/Wait** 패턴을 적절히 혼합하여 사용하는 것이 가장 효율적이다.

---

## 7. Reference
- [Temporal Docs: Asynchronous Activity Completion](https://docs.temporal.io/concepts/what-is-asynchronous-activity-completion)
- [Temporal Docs: Signals](https://docs.temporal.io/concepts/what-is-a-signal)
- [Java SDK Samples: Async Completion](https://github.com/temporalio/samples-java/tree/main/src/main/java/io/temporal/samples/asynccompletion)

---

## Appendix: Deep Dive - Task Token의 구조와 역할

### Task Token이란 무엇인가?
Task Token은 Temporal 서버가 특정 Activity Task를 고유하게 식별하기 위해 생성하는 불투명한(Opaque) 바이트 배열이다. 여기에는 워크플로우 ID, 런 ID, 액티비티 ID 등 서버가 해당 작업을 재개하는 데 필요한 정보가 인코딩되어 포함되어 있다.

### ActivityCompletionClient의 상세 기능
이 클라이언트는 워크플로우 외부(예: Spring Controller, Consumer)에서 비동기 액티비티를 완료시키기 위해 사용된다.
- `complete(byte[] taskToken, Object result)`: 성공 처리.
- `completeExceptionally(byte[] taskToken, Exception reason)`: 예외 처리를 통한 실패 보고.
- `reportCancellation(byte[] taskToken, Object details)`: 취소 요청 처리.
- `heartbeat(byte[] taskToken, Object details)`: 장시간 작업 시 살아있음을 알림.

### Workflow.await의 내부 동작
`Workflow.await`은 해당 워크플로우를 "차단(Block)"하는 것이 아니라 "일시 중지(Suspend)" 시킨다.
1. 대기 조건이 `false`인 경우, 워크플로우 상태를 DB에 저장하고 워커 스레드를 반환한다.
2. 외부에서 시그널이나 타이머 이벤트가 도착하면 Temporal 서버가 워커를 다시 깨운다.
3. 워커는 히스토리를 재생(Replay)하며 `Workflow.await` 지점까지 도달하고 조건을 다시 검사한다.
4. 조건이 `true`가 되면 다음 코드로 진행한다.

이러한 Replay 메커니즘 덕분에 서버가 재시작되어도 비동기 대기 상태는 완벽하게 복구될 수 있다.

---

## Appendix 2: 시나리오 예시 - 차량 등록 프로세스 비교

### 기존 방식 (점유형 액티비티)
- **동작**: 오케스트레이터 액티비티 내에서 외부 API를 호출하고 응답이 올 때까지(`200 OK`) 무한 대기.
- **문제점**: 외부 시스템 점검이나 네트워크 지연 발생 시 워커 스레드가 고갈되어 전체 시스템 마비 가능성.

### 개선 방식 (Signal 기반 비동기)
1. **오케스트레이터**: "차량 등록해줘"라는 메시지를 Kafka에 발행 후 즉시 퇴근(스레드 반환).
2. **차량 관리 서비스**: 메시지 수신 후 복잡한 등록 절차(수 분 소요) 수행.
3. **차량 관리 서비스**: 등록 완료 후 "등록 완료(WorkflowID: 123)" 시그널 발행.
4. **오케스트레이터**: 서버가 시그널을 감지하고 해당 워크플로우를 깨워 다음 단계(보험 가입 등) 진행.

이 방식은 각 서비스가 독립적으로 확장(Scaling)될 수 있게 하며, 장애 전파(Cascading Failure)를 차단하는 데 탁월한 효과를 발휘한다.

---
