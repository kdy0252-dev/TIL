---
id: Temporal.io
started: 2025-12-10
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Temporal.io

## 1. 개요 (Overview)
**Temporal**은 마이크로서비스 환경에서 **신뢰성 있는(Reliable) 워크플로우 실행**을 보장하는 오픈 소스 **오케스트레이션 엔진(Orchestration Engine)**입니다.

분산 시스템, 특히 마이크로서비스 아키텍처(MSA)에서는 네트워크 장애, 서버 다운, 배포로 인한 재시작 등 다양한 실패 시나리오가 존재합니다. 기존 시스템에서는 이를 해결하기 위해 큐(Queue), DB 트랜잭션, 스케줄러 등을 복잡하게 엮어서 사용해야 했습니다.

Temporal은 **"내결함성(Fault Tolerance)을 코드 레벨에서 추상화"** 하여, 개발자가 비즈니스 로직에만 집중하면 장애 복구, 재시도, 상태 저장은 플랫폼이 알아서 처리해주는 **Durable Execution** 개념을 제공합니다. 
Uber의 Cadence 프로젝트에서 파생되었으며, 현재는 독립적으로 발전하여 널리 쓰이고 있습니다.

---

## 2. 해결하고자 하는 문제 (Motivation)

### 2.1 분산 트랜잭션 (Distributed Transaction)
- 서비스 A -> 서비스 B -> 서비스 C 로 이어지는 비즈니스 로직에서 B가 실패하면 A를 롤백해야 합니다 (SAGA 패턴).
- Temporal은 코드로 SAGA 패턴을 명시적으로 작성하고, 실패 시 보상 트랜잭션(Compensation)을 자동으로 수행하도록 도울 수 있습니다.

### 2.2 장기 실행 프로세스 (Long Running Process)
- "사용자 가입 후 3일 뒤에 환영 이메일 발송"과 같은 로직을 구현하려면 DB에 상태를 저장하고 배치를 돌리거나 `Delay Queue`를 써야 합니다.
- Temporal에서는 `Workflow.sleep(Duration.ofDays(3))` 한 줄로 구현 가능합니다. 프로세스가 3일 동안 죽어 있어도(Hydration), 깨어날 때 정확히 상태를 복구합니다.

---

## 3. 핵심 아키텍처 및 동작 원리 (Architecture)

Temporal은 크게 **Temporal Server (Cluster)** 와 **Worker**로 구성됩니다.

### 3.1 Temporal Server (Backend)
- 상태 관리와 스케줄링을 담당하는 중앙 서버입니다.
- **Frontend Service**: 클라이언트 및 워커와의 통신 담당 (gRPC).
- **History Service**: 핵심 컴포넌트. 워크플로우의 모든 이벤트(Event History)를 DB(Cassandra, MySQL 등)에 기록하고 관리합니다.
- **Matching Service**: Task Queue를 관리하고 실행할 워커에게 태스크를 분배합니다.
- **Worker Service**: 백그라운드 작업 처리.

### 3.2 Worker (Client Application)
- 실제 비즈니스 로직(Workflow, Activity 코드)이 실행되는 프로세스입니다.
- Temporal Server에 접속하여 Task Queue를 폴링(Polling)하고, 할당된 작업을 수행한 후 결과를 서버에 보고합니다.
- 워커는 무상태(Stateless)로 확장 가능합니다.

### 3.3 Durable Execution Mechanism (이벤트 히스토리)
- 워크플로우가 실행되면, 모든 단계(Activity 시작, 완료, Timer 설정 등)가 **Event History**라는 로그로 서버에 저장됩니다.
- 만약 워커가 죽었다가 다시 살아나면, Temporal SDK는 서버에서 Event History를 받아와서 코드를 처음부터 다시 실행(Replay)합니다.
- **이미 실행된 단계(History에 있는 단계)** 는 실제 실행하지 않고 결과만 리턴받는 식으로 스킵하여, 중단된 지점의 상태(변수 값 등)를 완벽하게 복원합니다.
- 따라서 Workflow 코드는 반드시 **결정적(Deterministic)** 이어야 합니다. (Random, System.currentTimeMillis() 등 사용 금지 -> `Workflow.currentTimeMillis()` 사용).

---

## 4. 주요 개념 (Concepts)

### 4.1 Workflow
- 전체 비즈니스 프로세스의 흐름(오케스트레이션)을 정의합니다.
- 상태를 가질 수 있으며, 결정적(Deterministic)이어야 합니다.
- 외부 시스템 통신, I/O 작업 등은 직접 할 수 없고 **Activity**를 호출해야 합니다.

### 4.2 Activity
- Workflow 내에서 수행되는 단일 작업 단위입니다.
- 비결정적인 작업(API 호출, DB 조회, 파일 쓰기 등)은 모두 여기서 합니다.
- 실패 시 재시도(Retry) 정책을 설정할 수 있습니다.

### 4.3 Signal & Query
- **Signal**: 실행 중인 Workflow에 외부에서 데이터를 주입(이벤트 전달)할 때 사용합니다. (예: "배송 준비 중인데 '주소 변경' 시그널 도착")
- **Query**: 실행 중인 Workflow의 현재 내부 상태를 조회할 때 사용합니다.

---

## 5. 예제 (Example) - Java SDK

### 5.1 SAGA 패턴을 이용한 주문 처리 (Order Saga)

**1. Activity Interface 정의**
```java
@ActivityInterface
public interface OrderActivities {
    void reserveCredit(String orderId, int amount);
    void chargeCard(String orderId, int amount);
    void fulfillOrder(String orderId);
    
    // 보상 트랜잭션 (Compensations)
    void refundCard(String orderId, int amount);
    void releaseCredit(String orderId, int amount);
}
```

**2. Workflow 구현 (Saga Logic)**
```java
@WorkflowInterface
public interface OrderWorkflow {
    @WorkflowMethod
    void processOrder(String orderId, int amount);
}

public class OrderWorkflowImpl implements OrderWorkflow {
    // Activity Stub 생성 (Retry 옵션 설정)
    private final OrderActivities activities = Workflow.newActivityStub(OrderActivities.class,
            ActivityOptions.newBuilder()
                    .setStartToCloseTimeout(Duration.ofSeconds(10))
                    .setRetryOptions(RetryOptions.newBuilder().setMaximumAttempts(3).build())
                    .build());

    @Override
    public void processOrder(String orderId, int amount) {
        // Temporal SAGA Helper 클래스
        Saga saga = new Saga(new Saga.Options.Builder().setParallelCompensation(false).build());
        
        try {
            // 1. 크레딧 예약
            activities.reserveCredit(orderId, amount);
            // 성공 시 보상 로직 등록 (스택에 쌓임)
            saga.addCompensation(() -> activities.releaseCredit(orderId, amount));

            // 2. 카드 결제
            activities.chargeCard(orderId, amount);
            saga.addCompensation(() -> activities.refundCard(orderId, amount));

            // 3. 주문 완료 처리
            activities.fulfillOrder(orderId);
            
        } catch (ActivityFailure e) {
            // 어느 단계에서든 실패하면 즉시 보상 트랜잭션 실행 (역순)
            saga.compensate();
            throw e; // 호출자에게 실패 알림
        }
    }
}
```

**3. Worker 실행**
```java
public static void main(String[] args) {
    WorkflowServiceStubs service = WorkflowServiceStubs.newLocalServiceStubs();
    WorkflowClient client = WorkflowClient.newInstance(service);
    WorkerFactory factory = WorkerFactory.newInstance(client);

    Worker worker = factory.newWorker("OrderTaskQueue");
    worker.registerWorkflowImplementationTypes(OrderWorkflowImpl.class);
    worker.registerActivitiesImplementations(new OrderActivitiesImpl());

    factory.start(); // Polling 시작
}
```

---

## 6. 장점과 한계 (Pros & Cons)

### 장점
1. **복잡한 상태 관리 제거**: DB에 `status` 컬럼 만들고 `UPDATE` 치는 로직이 사라집니다. 코드가 곧 설계도가 됩니다.
2. **강력한 가시성**: Web UI에서 워크플로우의 현재 위치, 변수 값, 에러 스택 트레이스, 재시도 횟수 등을 실시간으로 볼 수 있습니다.
3. **무한 재시도와 타임아웃**: "30일 동안 재시도", "1시간 뒤 타임아웃" 등의 정책을 코드 설정만으로 적용 가능합니다.
4. **테스트 용이성**: `TestWorkflowEnvironment`를 제공하여 시간 여행(Time-skipping) 테스트가 가능합니다(예: 3일 뒤 로직을 1초 만에 테스트).

### 단점 및 한계
1. **학습 곡선**: "결정적 코드(Deterministic Code)" 작성 규칙 등 패러다임 변화에 적응해야 합니다.
2. **운영 복잡성**: Temporal Server 클러스터(Frontend, History, Matching, DB, ES)를 직접 운영하려면 난이도가 높습니다. (Managed Service인 Temporal Cloud 사용 권장 추세).
3. **Latency**: 일반적인 API 호출보다는 오버헤드(DB 기록, 큐잉)가 있으므로, 초저지연(Low Latency) 시스템에는 부적합합니다.

# Reference
- [Temporal Documentation](https://docs.temporal.io/)
- [Money Transfer Example (Java)](https://github.com/temporalio/samples-java/tree/main/core/src/main/java/io/temporal/samples/moneytransfer)
- [Saga Pattern in Temporal](https://docs.temporal.io/dev-guide/java/patterns/saga)