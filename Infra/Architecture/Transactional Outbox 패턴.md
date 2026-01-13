---
id: Transactional Outbox 패턴
started: 2026-01-13
tags:
  - ✅DONE
  - Architecture
  - Messaging
  - CDC
group:
  - "[[Architecture]]"
---
# Transactional Outbox 패턴: CDC를 통한 무결점 메시지 발행 전략

## 1. 개요 (Introduction)

분산 시스템의 정합성을 보장하기 위한 가장 큰 난제는 **"데이터베이스 업데이트와 메시지 발행의 원자성(Atomicity)"** 을 확보하는 것입니다. 이를 해결하기 위한 전술로 **Transactional Outbox 패턴** 은 이제 선택이 아닌 필수가 되었습니다.

과거에는 애플리케이션 레벨에서 주기적으로 DB를 조회하는 Polling 방식이 주로 쓰였으나, 최근에는 **CDC(Change Data Capture)** 기술의 발전으로 인해 인프라 레벨에서 훨씬 견고하고 실시간성이 뛰어난 구현이 가능해졌습니다. 본 문서에서는 이전의 Polling 방식과 현대적인 CDC 기반 방식의 차이를 조명하고, 구체적인 구현 전략을 다룹니다.

---

## 2. 왜 Transactional Outbox인가? (The Dual Write Problem)

마이크로서비스에서 비즈니스 로직(DB 저장)과 이벤트 발행(Kafka 전송)을 순차적으로 시도하면 반드시 실패 케이스가 발생합니다.
1. **DB 저장 성공 / 메시지 발행 실패**: 네트워크 장애 등으로 메시지가 소실되어 데이터 불일치 발생.
2. **메시지 발행 성공 / DB 트랜잭션 롤백**: 실제 데이터는 없는데 이벤트만 전파되어 좀비 데이터 발생.

이러한 **이중 쓰기(Dual Write)** 문제를 해결하기 위해, 비즈니스 데이터와 이벤트 메시지를 **하나의 DB 트랜잭션**으로 동일한 물리적 저장소에 기록하는 것이 Outbox 패턴의 핵심입니다.

---

## 3. 구현 방식의 진화: Polling vs CDC

### 3.1 이전 기술: 폴링 기반 (Application-level Polling)
애플리케이션 내의 스케줄러가 주기적으로 `Outbox` 테이블을 `SELECT` 하여 발행되지 않은 메시지를 찾아 보내는 방식입니다.
- **특징**: 단순 구현 가능 (`Spring Scheduler`).
- **한계**:
    - **지연(Latency)**: 폴링 주기만큼 실시간성이 떨어짐.
    - **DB 부하**: 데이터가 없어도 계속해서 DB를 자극함.
    - **삭제 감지 불가**: 물리적 삭제 이벤트를 처리하기 매우 복잡함.

### 3.2 현대적 기술: CDC 기반 (Infrastructure-level log-based)
DB의 트랜잭션 로그(WAL, Binlog 등)를 직접 구독하여 `Outbox` 테이블에 인서트되는 순간을 즉시 포착하는 방식입니다.
- **특징**: **Debezium**과 같은 도구를 사용하여 DB에 부하를 주지 않고 실시간으로 Kafka로 전달.
- **장점**: 압도적인 실시간성, DB 부하 최소화, 애플리케이션 코드 간소화.

---

## 4. CDC 기반 Outbox 아키텍처 설계

전체 흐름은 다음과 같습니다.
1. **App**: 비즈니스 정보와 이벤트를 로컬 트랜잭션으로 저장합니다.
2. **DB**: `Outbox` 데이터가 바이너리 로그에 기록됩니다.
3. **Debezium**: 로그를 모니터링하다가 `Outbox` 데이터 발생 시 이를 낚아챕니다.
4. **Kafka**: Debezium이 이벤트를 Kafka 토픽으로 즉시 쏩니다.
5. **Consumer**: 메시지를 소비하고 비즈니스를 처리합니다.

---

## 5. 실전 구현 예제 (Spring Boot + JPA)

### 5.1 Outbox 테이블 설계

```java
@Entity
@Table(name = "outbox")
@Getter @NoArgsConstructor
public class OutboxEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Debezium이 이 필드를 보고 발행할 Kafka 토픽을 결정할 수 있음 (Outbox Router 활용)
    private String aggregateType;
    private String aggregateId;
    private String eventType;
    
    @Column(columnDefinition = "TEXT")
    private String payload; // JSON serialized data

    @Column(nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    public OutboxEntity(String type, String id, String eventType, String payload) {
        this.aggregateType = type;
        this.aggregateId = id;
        this.eventType = eventType;
        this.payload = payload;
    }
}
```

### 5.2 비즈니스 로직에서의 활용 (쓰기 작업)

애플리케이션은 더 이상 메시지 발행(`kafkaTemplate.send`)에 신경 쓰지 않습니다. 오직 DB 저장에만 집중합니다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final OutboxRepository outboxRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public void createOrder(OrderRequest request) {
        // 1. 비즈니스 엔티티 저장
        OrderEntity order = orderRepository.save(new OrderEntity(request));

        // 2. 이벤트 페이로드 생성
        OrderCreatedEvent event = new OrderCreatedEvent(order.getId(), order.getCustomerId());
        String payload = objectMapper.writeValueAsString(event);

        // 3. Outbox 테이블에 기록 (로컬 트랜잭션 포함)
        OutboxEntity outbox = new OutboxEntity(
            "ORDER", 
            order.getId().toString(), 
            "ORDER_CREATED", 
            payload
        );
        outboxRepository.save(outbox);
        
        // 커밋 완료 시, Debezium이 바이너리 로그에서 위 레코드를 감지하여 Kafka로 보냄
    }
}
```

---

## 6. 운영 및 고도화 전략

### 6.1 Outbox Router (Debezium SMT)
Debezium의 **SMT(Single Message Transform)** 기능을 사용하면, `Outbox` 테이블로 들어오는 모든 데이터를 하나의 카프카 토픽이 아닌, `aggregateType` 필드 값에 따라 서로 다른 토픽으로 자동 라우팅할 수 있어 구조가 매우 깔끔해집니다.

### 6.2 데이터 삭제 (Purging)
CDC 방식도 결국 `Outbox` 테이블을 경유하므로 데이터가 계속 쌓입니다.
- **해결책**: Debezium이 데이터를 읽어간 후, 일정 시간이 지난 데이터를 배치로 삭제하거나, DB의 `TTL(Time To Live)` 기능을 활용하여 자동 삭제되도록 설정해야 합니다.

### 6.3 최소 한 번 전송 (At-least-once) 보장
CDC 방식은 브로커 장애 시 로그 리더가 마지막 위치를 기억했다가 재개하므로 메시지 유실이 없습니다. 다만 중복 발행 가능성이 있으므로 **컨슈머의 멱등성** 처리가 반드시 수반되어야 합니다.

---
## 7. 결론
Transactional Outbox 패턴은 분산 시스템의 아킬레스건인 데이터 정합성 문제를 인프라 레벨에서 우아하게 해결합니다. 특히 **Log-based CDC**와의 결합은 개발자에게는 비즈니스 로직에만 집중하게 하고, 시스템에는 강력한 신뢰성과 실시간성을 부여하는 최상의 조합입니다.

단순한 Polling 방식에서 벗어나, CDC 기반의 견고한 이벤트 파이프라인을 구축하여 장애에 강한 MSA를 설계하시기 바랍니다.

# Reference
- [Debezium Official: The Outbox Pattern](https://debezium.io/blog/2019/02/19/using-the-outbox-pattern/)
- [Microservices.io: Transactional Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Confluent: Reliable Microservices with the Outbox Pattern](https://www.confluent.io/blog/reliable-microservices-data-exchange-with-the-outbox-pattern/)
