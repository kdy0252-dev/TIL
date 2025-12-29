---
id: CQRS Pattern
started: 2025-04-10
tags:
  - ✅DONE
group:
  - "[[Java Spring Design Pattern]]"
---
# CQRS Pattern (Command and Query Responsibility Segregation)

## 1. 개요 (Overview)
**CQRS**는 시스템의 상태를 변경하는 **명령(Command/Write)** 책임과 상태를 조회하는 **쿼리(Query/Read)** 책임을 물리적 또는 논리적으로 완벽하게 분리하는 아키텍처 패턴입니다.

Bertrand Meyer의 **CQS (Command Query Separation)** 원칙인 "질문(Query)이 대답을 수정해서는 안 되고, 명령(Command)이 값을 반환해서는 안 된다"는 개념을 시스템 아키텍처 레벨로 확장한 것입니다. 서비스가 커질수록 모델은 복잡해지는데, 하나의 객체(Entity)로 '복잡한 비즈니스 로직 처리'와 '다양한 화면 조회'를 모두 감당하려다 보니 발생하는 성능 및 유지보수 문제를 해결합니다.

---

## 2. 왜 필요한가? (Problem & Solution)

### 2.1 기존 아키텍처(CRUD)의 한계
- **불일치**: 도메인 모델은 데이터 정합성과 비즈니스 룰 처리에 최적화되어 있지만, UI 화면은 여러 테이블을 조인하거나 통계 데이터를 필요로 합니다.
- **성능 병목**: 대개 조회 요청이 쓰기 요청보다 훨씬 많습니다(Read:Write = 100:1). 하지만 동일한 Entity와 DB를 쓰면, 쓰기 트랜잭션의 락(Lock)이 조회를 방해하거나, 조회용 인덱스가 쓰기 성능을 저하시킵니다.
- **복잡도**: 조회 요구사항을 맞추기 위해 Entity에 온갖 게터와 관계 매핑이 추가되어, 핵심 도메인 로직이 희석됩니다.

### 2.2 CQRS의 구조 (Architecture)
1. **Command Side (쓰기)**
    - **목적**: 데이터의 무결성 보장, 비즈니스 로직 수행.
    - **특징**: 정규화된 RDBMS, 엄격한 트랜잭션, ORM(JPA) 사용. 복잡한 유효성 검사 수행.
    - **반환**: 보통 Void나 ID만 반환.
2. **Query Side (읽기)**
    - **목적**: 빠른 조회, 화면에 맞는 데이터 제공.
    - **특징**: 반정규화(De-normalized)된 테이블, NoSQL(MongoDB, Elasticsearch), Redis 캐시 사용. 단순 Select.
    - **반환**: DTO(Data Transfer Object) 반환.

---

## 3. 구현 레벨 (Implementation Levels)

CQRS는 반드시 DB를 쪼개야 하는 것이 아닙니다. 복잡도에 따라 단계를 선택해야 합니다.

### Level 1: 코드 레벨의 분리 (Logical Separation)
DB는 하나지만, 내부 서비스 클래스와 모델을 분리합니다.
- `OrderCommandService`: `Order` 엔티티를 사용하여 상태 변경.
- `OrderQueryService`: `OrderDto` 또는 `JdbcTemplate`, `MyBatis`를 사용하여 조회 전용 쿼리 수행.
- **장점**: 구현 단순, 모델의 복잡도 감소.
- **단점**: DB 부하 분산 효과는 없음.

### Level 2: DB의 분리 (Physical Separation)
Master-Slave(Replica) 구조를 활용합니다.
- **Command**: Master DB에 씀.
- **Query**: Slave DB(Replica)에서 읽음. DB 부하가 분산됨.

### Level 3: 이종 저장소와 이벤트 소싱 (Polyglot Persistence)
Write DB(MySQL)와 Read DB(Elasticsearch, MongoDB)를 아예 다른 종류로 가져갑니다.
- **Command**가 이벤트를 발행하면, **Query** 쪽에서 이를 구독하여 자신에게 맞는 형태로 데이터를 가공해 저장합니다.
- **예**: 주문이 발생하면 -> Kafka 이벤트 발행 -> 검색 서비스가 구독하여 Elasticsearch 인덱싱.

---

## 4. 예제 코드 (Spring Boot + Kafka)

**Level 3** 방식의 간단한 예제입니다.

### 4.1 Command Side
```java
@Service
@RequiredArgsConstructor
public class OrderCommandService {
    private final OrderRepository orderRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Transactional
    public void createOrder(CreateOrderCommand command) {
        // 1. 핵심 비즈니스 로직 및 DB 저장
        Order order = new Order(command.getUserId(), command.getProductId());
        order.validate();
        orderRepository.save(order);

        // 2. 이벤트 발행 (비동기)
        OrderPlacedEvent event = new OrderPlacedEvent(order.getId(), order.getTotalPrice(), ...);
        kafkaTemplate.send("order-events", event);
    }
}
```

### 4.2 Query Side (Projector)
이벤트를 받아 읽기 전용 DB(여기선 MongoDB 가정)에 '화면에 보여주기 딱 좋은 형태'로 저장합니다.
```java
@Component
@RequiredArgsConstructor
public class OrderQueryProjector {
    
    private final OrderQueryRepository mongoRepository; // MongoDB

    @KafkaListener(topics = "order-events", groupId = "query-service-group")
    public void handle(OrderPlacedEvent event) {
        // 복잡한 조인 없이 바로 꺼내 쓸 수 있도록 데이터 가공 (Denormalization)
        OrderView view = OrderView.builder()
                .orderId(event.getOrderId())
                .userName(event.getUserName()) // 이미 이벤트에 포함되어 있다고 가정
                .productName(event.getProductName())
                .status("PLACED")
                .updatedAt(LocalDateTime.now())
                .build();
        
        mongoRepository.save(view);
    }
}
```

### 4.3 Query Side (Controller)
```java
@RestController
@RequiredArgsConstructor
public class OrderQueryController {
    private final OrderQueryRepository mongoRepository;

    @GetMapping("/orders/{id}")
    public Mono<OrderView> getOrder(@PathVariable String id) {
        // 복잡한 로직 없이 바로 반환 (Fast)
        return mongoRepository.findById(id); 
    }
}
```

---

## 5. 운영 시 고려사항 (Operational Considerations)

### 5.1 결과적 일관성 (Eventual Consistency)
이벤트 기반 CQRS의 가장 큰 난제입니다. 사용자가 "저장" 버튼을 누르고 목록 화면으로 리다이렉트되었는데, 아직 이벤트가 컨슈밍되지 않아 목록에 안 보일 수 있습니다 (**Replication Lag**).
- **해결책 1**: UI에서 낙관적 업데이트(Optimistic UI) 처리 (성공했다고 가정하고 JS로 리스트에 추가).
- **해결책 2**: 저장 직후에는 강제로 Master DB에서 읽어오거나, 잠시 로딩 스피너를 보여줌.

### 5.2 이벤트 버전 관리 및 리플레이
이벤트 스키마가 변경되거나 버그로 인해 Read DB 데이터가 꼬였다면?
- Command DB(또는 Event Store)는 진실의 원천(Source of Truth)입니다.
- Read DB를 싹 다 지우고, 처음부터 이벤트를 다시 재생(Replay)하여 Read DB를 재구축할 수 있어야 합니다.

### 5.3 정말로 필요한가?
CQRS는 시스템 복잡도를 2배 이상 높입니다. (동기화 이슈, 관리 포인트 증가).
단순한 관리자 페이지나 트래픽이 적은 서비스에는 **추천하지 않음.** Level 1(코드 분리) 정도면 충분.

# Reference
- [Martin Fowler - CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Microsoft Azure - CQRS Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)
- [Axon Framework Guide](https://docs.axoniq.io/reference-guide/)