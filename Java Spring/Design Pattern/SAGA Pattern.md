---
id: SAGA Pattern
started: 2025-04-10

tags:
  - ⏳DOING
group:
  - "[[Java Spring Design Pattern]]"
---
# SAGA Pattern (Distributed Transaction)

## 1. 개요 (Overview)
**SAGA Pattern**은 마이크로서비스 아키텍처(MSA)에서 **분산 트랜잭션(Distributed Transaction)**의 데이터 일관성을 보장하기 위한 가장 대표적인 패턴입니다.

모놀리식 환경에서는 단일 데이터베이스의 ACID 트랜잭션(`@Transactional`)을 통해 데이터 무결성을 쉽게 보장할 수 있습니다. 하지만 서비스가 분리되어 DB가 쪼개지면, 더 이상 단일 트랜잭션으로 묶을 수 없습니다.
과거에는 **2PC (Two-Phase Commit, XA Transaction)**를 사용했으나, 이는 블로킹 방식으로 성능이 매우 떨어지고, NoSQL 등 다양한 저장소를 지원하지 못하며, 코디네이터(Coordinator)가 단일 장애 지점(SPOF)이 되는 문제가 있어 클라우드 환경에는 적합하지 않습니다.

SAGA는 긴 트랜잭션(Long Running Transaction)을 **여러 개의 짧은 로컬 트랜잭션의 연속**으로 쪼개고, 중간에 실패하면 **보상 트랜잭션(Compensating Transaction)**을 실행하여 이전 단계를 취소하며 **최종 일관성(Eventual Consistency)**을 달성합니다.

---

## 2. 핵심 원리 (Core Concepts)

### 2.1 ACID vs BASE
SAGA는 ACID를 포기하고 BASE 모델을 따릅니다.
- **Atomicity (원자성)**: SAGA는 물리적 원자성이 아닌 "논리적 원자성"을 보장합니다. (All or Nothing: 모두 성공하거나, 모두 보상되어 원래대로 돌아가거나)
- **Isolation (격리성)**: SAGA의 가장 큰 약점입니다. 트랜잭션 중간 단계의 데이터(Dirty Data)를 다른 사용자가 볼 수 있습니다. 이를 막기 위해 'Semantic Lock'이나 상태 필드(PENDING)를 사용합니다.

### 2.2 보상 트랜잭션 (Compensating Transaction)
- **Ti**: i번째 단계의 정상 트랜잭션.
- **Ci**: Ti가 수행한 변경을 '의미론적으로' 취소하는 트랜잭션.
- 실행 순서 (성공 시): T1 -> T2 -> T3
- 실행 순서 (T3 실패 시): T1 -> T2 -> T3(실패) -> C2 -> C1
- **주의**: C는 반드시 성공해야 합니다(Retriable). 실패하면 사람에게 알람을 보내 수동 처리해야 합니다.

---

## 3. 구현 방식 (Implementation Models)

### 3.1 Choreography (코레오그래피 - 이벤트 기반)
중앙 조율자 없이, 각 서비스가 이벤트를 주고받으며 자율적으로 다음 단계를 수행합니다.

- **흐름 예시**:
  1. `OrderService`: 주문 생성 -> `OrderCreated` 이벤트 발행.
  2. `PaymentService`: `OrderCreated` 구독 -> 결제 시도 -> `PaymentApproved` 발행.
  3. `InventoryService`: `PaymentApproved` 구독 -> 재고 차감 -> `InventoryReduced` 발행.
  4. (만약 재고 부족 시): `InventoryFailed` 발행.
  5. `PaymentService`, `OrderService`: `InventoryFailed` 구독 -> 결제 취소, 주문 취소 (보상).

- **장점**: 구성이 간단하고, 서비스 간 결합도가 낮음. 추가 서비스가 이벤트를 구독하기 쉬움.
- **단점**: 프로세스 흐름이 파편화되어 있어, 전체 비즈니스 로직을 한눈에 파악하기 매우 어려움(Cyclic Dependency 위험).

### 3.2 Orchestration (오케스트레이션 - 중앙 제어 기반)
**SAGA Orchestrator**라는 별도의 서비스(또는 클래스)가 트랜잭션의 전체 흐름을 제어합니다.

- **흐름 예시**:
  1. `OrderSagaManager`가 시작됩니다.
  2. `OrderSagaManager` -> `PaymentService`: "결제해라" (Command).
  3. `PaymentService` -> `OrderSagaManager`: "성공했다" (Reply).
  4. `OrderSagaManager` -> `InventoryService`: "재고 줄여라" (Command).
  5. `InventoryService` -> `OrderSagaManager`: "실패했다" (Reply).
  6. `OrderSagaManager` -> `PaymentService`: "결제 취소해라" (Compensating Command).

- **장점**: 비즈니스 흐름이 한곳에 정의되어 있어 이해와 관리가 쉬움. 서비스 간 순환 참조 방지.
- **단점**: 오케스트레이터 로직이 복잡해질 수 있음. 인프라 복잡도 증가.

---

## 4. 구현 코드 예제 (Orchestration with Java)

간단한 오케스트레이터를 Java 코드로 구현한 예시입니다. 실제 상용 환경에서는 **Axon Framework**, **Temporal**, **Eventuate Tram** 같은 프레임워크 사용을 권장합니다.

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class OrderSagaOrchestrator {

    private final OrderService orderService;
    private final PaymentService paymentService;
    private final InventoryService inventoryService;

    // SAGA 시작점
    public void createOrder(OrderRequest request) {
        Long orderId = null;
        try {
            // Step 1: 주문 생성 (PENDING)
            orderId = orderService.createOrder(request);
            
            // Step 2: 결제 시도
            paymentService.processPayment(orderId, request.getAmount());
            
            // Step 3: 재고 차감
            inventoryService.decreaseStock(request.getProductId(), request.getQuantity());
            
            // Step 4: 주문 완료 (CONFIRMED)
            orderService.completeOrder(orderId);
            
        } catch (Exception e) {
            log.error("SAGA Failed: {}", e.getMessage());
            compensate(orderId, e);
        }
    }

    // 보상 트랜잭션 수행
    private void compensate(Long orderId, Exception reason) {
        // 어디까지 성공했는지에 따라 역순으로 취소해야 함을 인지해야 함.
        // 여기서는 단순화를 위해 모든 것을 취소 시도.
        
        try {
            inventoryService.increaseStock(orderId); // 재고 복구 (이미 차감된 경우만)
        } catch (Exception e) {
            log.error("Critical: Stock Compensation Failed! Manual Intervention Required.");
        }

        try {
            paymentService.cancelPayment(orderId); // 결제 취소
        } catch (Exception e) {
             log.error("Critical: Payment Compensation Failed!");
        }

        orderService.failOrder(orderId, reason.getMessage()); // 주문 실패 처리
    }
}
```

---

## 5. 운영 시 고려사항 (Operational Considerations)

### 5.1 멱등성 (Idempotency)
분산 환경에서는 네트워크 오류나 타임아웃으로 인해 메시지가 중복 전달될 수 있습니다. (e.g., 결제 요청이 두 번 옴)
- 모든 트랜잭션(특히 보상 트랜잭션)은 멱등해야 합니다.
- 같은 요청이 여러 번 와도 결과는 한 번만 실행한 것과 같아야 합니다.
- 보통 `TransactionId`나 `OrderId`를 유니크 키로 활용하여 중복 처리를 막습니다.

### 5.2 격리성 문제 해결 (Isolation issues)
SAGA 수행 중에 다른 트랜잭션이 끼어드는 것을 어떻게 막을까요?
- **Semantic Lock**: 해당 데이터에 `is_locked` 또는 `status=PENDING` 같은 마킹을 하여 다른 트랜잭션이 건드리지 못하게 합니다.
- **Commutative Updates**: 순서가 바뀌어도 상관없는 연산(예: 덧셈, 뺄셈)으로 설계합니다.
- **Optimistic Offline Lock**: 버전 관리(Versioning)를 통해 충돌을 감지합니다.

### 5.3 프레임워크 선택 가이드
- **간단한 워크플로우**: Kafka/RabbitMQ를 이용한 단순 Choreography.
- **복잡하고 긴 워크플로우**: Temporal (추천), Spring State Machine.
- **Event Sourcing과 결합**: Axon Framework.

# Reference
- [Microservices Patterns (Chris Richardson)](https://microservices.io/patterns/data/saga.html)
- [Temporal.io - SAGA Pattern](https://docs.temporal.io/design-patterns/saga/)
- [Microsoft Architecture Checklists](https://docs.microsoft.com/en-us/azure/architecture/patterns/saga)