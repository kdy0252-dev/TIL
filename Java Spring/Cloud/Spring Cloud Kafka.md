---
id: Spring Cloud Kafka
started: 2025-08-05
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Kafka

## 1. 개요 (Overview)
**Spring Cloud Kafka**는 엄밀히 말하면 **Spring for Apache Kafka** 프로젝트를 의미하거나, **Spring Cloud Stream**의 Kafka Binder 구현체를 지칭할 때 혼용되어 사용됩니다. 이 문서에서는 **Spring for Apache Kafka** 프로젝트 자체를 중심으로 다룹니다.

Spring Framework의 철학을 Kafka 클라이언트에 적용하여, `KafkaTemplate`을 통한 고수준의 메시지 송신 API와 `@KafkaListener` 애노테이션을 통한 간결한 메시지 수신(POJO Listener) 기능을 제공합니다.

---

## 2. 핵심 구성 요소 (Core Components)

### 2.1 KafkaTemplate
JDBCTemplate과 유사하게, Kafka Producer API를 래핑한 템플릿 클래스입니다.
- 메시지 전송, 비동기 콜백(`CompletableFuture`), 트랜잭션 처리 등을 지원합니다.

### 2.2 @KafkaListener
메시지 소비(Consumer)를 위한 핵심 애노테이션입니다. 복잡한 폴링(Polling) 루프를 숨기고, 메시지가 도착하면 메서드를 호출해주는 **Message-Driven POJO**를 구현합니다.
- 멀티스레드 소비 (`concurrency`), 배치 리스너 (`batchListener`), 파티션 할당, 에러 핸들링 지정 등을 속성으로 제어할 수 있습니다.

### 2.3 Error Handling (재처리 전략)
Kafka는 메시지 처리에 실패했을 때 단순한 재시도뿐만 아니라, 정교한 에러 핸들링 전략이 필요합니다.
- **SeekToCurrentErrorHandler (Default)**: 에러 발생 시 오프셋을 커밋하지 않고 재시도합니다. (Backoff 설정 가능)
- **Dead Letter Queue (DLQ)**: 일정 횟수 이상 실패한 메시지는 별도의 토픽(DLT)으로 보내고, 오프셋을 넘겨서 다음 메시지를 처리하게 합니다. (`DeadLetterPublishingRecoverer`)

---

## 3. 구현 예제

### 3.1 설정 (application.yml)
Spring Boot 자동 설정을 활용하여 간편하게 접속 정보를 세팅합니다.

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    consumer:
      group-id: my-group
      auto-offset-reset: earliest # 오프셋 없을 때 처음부터 읽기
      enable-auto-commit: false # 수동 커밋 권장 (또는 리스너가 끝날 때 커밋)
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
      acks: all # 내구성 강화
```

### 3.2 Producer 구현

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class KafkaProducerService {

    private final KafkaTemplate<String, String> kafkaTemplate;

    public void sendMessage(String topic, String key, String message) {
        // 비동기 전송
        CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(topic, key, message);

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("Sent message to {} with offset {}", topic, result.getRecordMetadata().offset());
            } else {
                log.error("Failed to send message", ex);
            }
        });
    }
}
```

### 3.3 Consumer 구현 (with Retry & DLQ)

```java
@Component
@Slf4j
public class KafkaConsumerService {

    // concurrency = "3": 쓰레드 3개가 돌면서 파티션을 나눠서 처리
    @KafkaListener(topics = "order-events", groupId = "order-group", concurrency = "3")
    public void listen(ConsumerRecord<String, String> record, Acknowledgment ack) {
        log.info("Received Message: {}", record.value());
        
        try {
            processOrder(record.value());
            ack.acknowledge(); // 수동 커밋 (처리가 성공했을 때만)
        } catch (Exception e) {
            log.error("Error processing message", e);
            throw e; // 에러를 던져야 ErrorHandler가 잡아서 재시도하거나 DLQ로 보냄
        }
    }

    private void processOrder(String orderJson) {
        // 비즈니스 로직...
        if (orderJson.contains("fail")) {
            throw new RuntimeException("Simulated Failure");
        }
    }
}
```

### 3.4 에러 핸들러 설정 (Java Config)
Spring Boot 2.5+ 부터는 `CommonErrorHandler`를 사용합니다.

```java
@Bean
public CommonErrorHandler errorHandler(KafkaTemplate<Object, Object> template) {
    // 1. 실패 시 DLQ로 발행하는 Recoverer
    DeadLetterPublishingRecoverer recoverer = new DeadLetterPublishingRecoverer(template);
    
    // 2. 3번 재시도 후(1초 간격) 복구(DLQ 전송)하는 에러 핸들러
    DefaultErrorHandler errorHandler = new DefaultErrorHandler(recoverer, new FixedBackOff(1000L, 3));
    
    // 특정 예외는 재시도 없이 바로 DLQ로
    errorHandler.addNotRetryableExceptions(IllegalArgumentException.class);
    
    return errorHandler;
}
```

---

## 4. 트랜잭션 (Transactions)
DB 업데이트와 카프카 메시지 발행을 원자적(Atomic)으로 처리해야 할 때 사용합니다 (`ChainedTransactionManager`는 Deprecated됨).
Kafka의 `transactional-id`를 설정하고, `@Transactional`을 메서드에 붙이면, Spring이 알아서 Kafka 트랜잭션(`beginTransaction`, `commit`, `abort`)을 관리해줍니다. 이를 통해 **Exactly-Once Semantics (EOS)**에 근접한 처리가 가능합니다.

# Reference
- [Spring for Apache Kafka Documentation](https://docs.spring.io/spring-kafka/reference/html/)
- [Kafka Retry & DLQ Guide](https://www.baeldung.com/spring-kafka-execution-strategy)
- [Kafka Transaction in Spring](https://docs.spring.io/spring-kafka/reference/html/#transactions)