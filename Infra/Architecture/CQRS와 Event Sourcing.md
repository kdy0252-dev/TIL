---
id: CQRS와 Event Sourcing
started: 2026-01-13
tags:
  - ✅DONE
  - Architecture
  - DDD
  - CDC
group:
  - "[[Architecture]]"
---
# CQRS와 Event Sourcing: CDC 기반의 고성능 데이터 동기화 아키텍처

## 1. 개요 (Introduction)

현대적인 분산 시스템에서 데이터의 정합성을 유지하면서도 초고속 조회를 제공하는 것은 영원한 숙제입니다. 전통적인 CRUD 모델은 도메인이 복잡해질수록 읽기(Query) 성능 최적화가 쓰기(Command) 모델의 무결성을 해치는 결과를 초래합니다.

이를 해결하기 위해 등장한 **CQRS(Command Query Responsibility Segregation)**와 **Event Sourcing**은 최근 **CDC(Change Data Capture)** 기술과 결합하여 그 강력함이 배가되었습니다. 이 문서에서는 이전의 동기화 방식들을 되짚어보고, 왜 CDC 기반의 비동기 동기화가 표준으로 자리 잡았는지 상세히 다룹니다.

---

## 2. 데이터 동기화 기술의 진화

### 2.1 1세대: 애플리케이션 레벨 동기화 (Dual Write)
비즈니스 로직 내부에서 쓰기 DB와 조회용 DB(ElasticSearch, Redis 등)에 직접 데이터를 쓰는 방식입니다.
- **방식**: `db.save(data); readDb.save(data);`
- **문제점**: 원자성(Atomicity) 보장이 어렵습니다. 쓰기 DB 저장은 성공했는데 조회 DB 저장이 실패하면 데이터 불일치가 발생합니다. (이른바 '이중 쓰기' 문제)

### 2.2 2세대: 폴링 기반 동기화 (Query-based Polling)
조회 모델 업데이트 프로세스가 주기적으로 쓰기 DB를 감시(SELECT)하여 변경분만 가져가는 방식입니다.
- **방식**: `SELECT * FROM table WHERE updated_at > :last_check`
- **문제점**: DB에 지속적인 부하를 주며, 실시간성이 떨어집니다. 또한 물리적 삭제(Hard Delete)를 감지할 수 없습니다.

### 2.3 3세대: 로그 기반 CDC (Log-based CDC)
DB의 트랜잭션 로그(WAL, Binlog)를 직접 구독하여 변경사항을 낚아채는 방식입니다.
- **특징**: DB에 쿼리를 날리지 않으므로 성능 부하가 거의 없으며, 삭제를 포함한 100%의 변경 이력을 실시간으로 포착합니다.

---

## 3. CDC 기반 CQRS 아키텍처 설계

CDC를 활용한 CQRS는 조회 모델(Read Model)로의 데이터 전파를 완전히 인프라 레이어로 위임합니다.

### 3.1 전체 아키텍처 (Conceptual Flow)
1. **Command**: 사용자가 주문을 생성하면 쓰기 DB(RDBMS)에만 저장합니다.
2. **Capture**: **Debezium** 같은 CDC 커넥터가 DB 로그에서 변경 이벤트를 감지합니다.
3. **Stream**: 이벤트를 Kafka 토픽으로 발행합니다.
4. **Projecting**: Consumer(Sink)가 Kafka에서 이벤트를 읽어 조회 최적화 DB(NoSQL, OS 등)의 스키마에 맞게 변환하여 저장합니다.

---

## 4. 실전 구현 예제 (Java Spring Boot + Debezium JSON)

이 예제에서는 Debezium이 쏜 CDC 이벤트를 수신하여 조회 모델(Projection)을 업데이트하는 Java 코드를 구현합니다.

### 4.1 Debezium CDC 이벤트 구조 (JSON)
Debezium은 변경 전(`before`)과 변경 후(`after`) 데이터를 포함한 상세한 정보를 보냅니다.

```json
{
  "before": { "id": 1, "name": "Old Name", "balance": 1000 },
  "after": { "id": 1, "name": "New Name", "balance": 1500 },
  "op": "u", // c: create, u: update, d: delete
  "ts_ms": 1673582345678
}
```

### 4.2 조회 모델 업데이트 구현 (Projection Service)

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class AccountReadModelProcessor {

    private final AccountDocumentRepository searchRepository; // ElasticSearch 등 조회 전용 DB
    private final ObjectMapper objectMapper;

    @KafkaListener(topics = "dbserver1.inventory.accounts", groupId = "cqrs-group")
    public void processAccountChange(String message) {
        try {
            JsonNode root = objectMapper.readTree(message);
            String operation = root.get("op").asText();
            JsonNode after = root.get("after");
            JsonNode before = root.get("before");

            switch (operation) {
                case "c": // Create
                case "u": // Update
                    updateReadModel(after);
                    break;
                case "d": // Delete
                    deleteFromReadModel(before.get("id").asLong());
                    break;
                default:
                    log.warn("지원하지 않는 연산 타입: {}", operation);
            }
        } catch (Exception e) {
            log.error("CDC 메시지 처리 실패", e);
            // 에러 핸들링: Dead Letter Queue로 보내거나 재시도
        }
    }

    private void updateReadModel(JsonNode data) {
        AccountDocument doc = AccountDocument.builder()
                .id(data.get("id").asLong())
                .name(data.get("name").asText())
                .balance(data.get("balance").asLong())
                .lastUpdated(LocalDateTime.now())
                .build();
        
        searchRepository.save(doc); // 조회 DB 업데이트
        log.info("조회 모델 업데이트 완료: {}", doc.getId());
    }

    private void deleteFromReadModel(Long id) {
        searchRepository.deleteById(id);
        log.info("조회 모델 삭제 완료: {}", id);
    }
}
```

---

## 5. Event Sourcing과의 결합

이벤트 소싱 환경에서 CDC는 더욱 빛을 발합니다.

### 5.1 이벤트 저장소(Event Store) 활용
이벤트 소싱 시스템은 모든 상태 변경을 `events` 테이블에 기록합니다. 이 테이블에 CDC를 걸면, 시스템 내에서 발생하는 모든 도메인 이벤트가 자동으로 외부 시스템으로 흘러가게 됩니다.

### 5.2 장점 (Why CDC for Event Sourcing?)
1. **무손실 전파**: 메시지 발행 로직이 애플리케이션에 없어도 DB에 기록만 되면 반드시 전파됩니다.
2. **재현성(Replayability)**: 과거의 특정 시점 로그부터 다시 읽어 조회 모델을 처음부터 다시 구축(Rebuilding)할 수 있습니다.

---

## 6. 운영 시 고려해야 할 고급 주제

### 6.1 Schema Evolution
쓰기 DB의 스키마가 변경되면 CDC 이벤트의 구조도 변합니다.
- **해결책**: Schema Registry(Confluent/Apicurio)를 사용하여 이벤트 버전을 관리하고, Consumer 쪽에서 하위 호환성을 유지하도록 설계해야 합니다.

### 6.2 데이터 정합성 (Ordering)
Kafka 파티셔닝 전략이 중요합니다. 동일한 PK를 가진 이벤트는 반드시 동일한 파티션으로 들어가야 순서가 보장됩니다.
- **Debezium 기본 동작**: PK를 Kafka 메시지 키로 사용하므로 메시지 순서가 자연스럽게 보장됩니다.

---

## 7. 결론

CQRS와 Event Sourcing은 기술적 난이도가 높지만, CDC와 결합했을 때 비로소 **"운영 가능한 수준의 견고함"** 을 얻게 됩니다. 과거의 이중 쓰기나 폴링 방식의 불안정함에서 벗어나, DB 로그 기반의 확실한 데이터 파이프라인을 구축하십시오.

비즈니스 로직은 쓰기 모델에만 집중하고, 조회 모델의 동기화는 CDC 레이어에 맡기는 구조가 현대적인 백엔드 설계의 정석입니다.

# Reference
- [Debezium Official Docs: CQRS and Event Sourcing](https://debezium.io/blog/2020/02/10/event-sourcing-vs-cdc/)
- [Martin Fowler: CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Microsoft Azure: Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Confluent: Building a CQRS View with Kafka and Debezium](https://www.confluent.io/blog/build-cqrs-view-with-kafka-and-debezium/)
