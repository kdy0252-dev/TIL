---
id: Kafka와 MQ의 구조 및 동작 차이 (Kafka vs RabbitMQ)
started: 2025-09-30
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Kafka와 MQ의 구조 및 동작 차이 (Kafka vs RabbitMQ)

## 1. 개요 (Overview)
**Apache Kafka**와 **RabbitMQ(Message Queue)**는 모두 비동기 시스템 간 통신을 위한 미들웨어이지만, 탄생 목적과 내부 아키텍처가 완전히 다릅니다.

- **RabbitMQ**: 전통적인 **메시지 브로커(Message Broker)**. 메시지의 신뢰성 있는 전달, 복잡한 라우팅, 큐잉(Queueing)에 최적화되어 있습니다. "우편 배달부"와 같습니다. (배달하면 끝)
- **Apache Kafka**: **분산 이벤트 스트리밍 플랫폼(Event Streaming Platform)**. 대용량 실시간 로그 처리, 데이터 파이프라인, 재생(Replay)에 최적화되어 있습니다. "도로망과 CCTV"와 같습니다. (차가 지나가도 기록이 남음)

이 문서에서는 두 기술의 아키텍처적 차이, 성능 특성, 그리고 언제 무엇을 써야 하는지를 깊이 있게 다룹니다.

---

## 2. 아키텍처 비교 (Architecture Comparison)

### 2.1 RabbitMQ: Smart Broker, Dumb Consumer
- **Broker 중심 설계**: 브로커가 메시지의 상태(어떤 소비자가 읽었는지, Ack 받았는지)를 모두 관리합니다.
- **Push Model**: 브로커가 컨슈머에게 메시지를 밀어줍니다(Push). 컨슈머가 느리면 `Prefetch Count` 조절 등을 통해 과부하를 막습니다.
- **Complex Routing**: Exchange Type(Direct, Fanout, Topic, Headers)을 통해 메시지를 매우 유연하게 라우팅할 수 있습니다.
- **Transient**: 기본적으로 소비된 메시지는 **즉시 삭제**됩니다.

### 2.2 Kafka: Dumb Broker, Smart Consumer
- **Consumer 중심 설계**: 브로커는 단순히 파일 시스템에 메시지를 저장(Append)할 뿐, 누가 읽었는지 신경 쓰지 않습니다. 컨슈머가 직접 자신의 읽은 위치(**Offset**)를 관리합니다.
- **Pull Model**: 컨슈머가 자신의 속도에 맞춰 브로커로부터 메시지를 가져옵니다(Pull).
- **Log Structure**: 메시지는 파일(Segment)에 순차적으로 저장되며, 소비되어도 설정된 기간(Retention Policy) 동안 **삭제되지 않습니다**.
- **High Throughput**: 묶음 처리(Batching)와 제로 카피(Zero-Copy) 기술을 통해 압도적인 처리량을 자랑합니다.

---

## 3. 주요 기능 상세 비교 (Detailed Features)

| 특징 | RabbitMQ (Message Queue) | Apache Kafka (Event Streaming) |
| :--- | :--- | :--- |
| **메시지 영속성** | 소비 후 즉시 삭제 (Memory 우위) | 디스크에 일정 기간 보관 (Disk 우위) |
| **처리 모델** | FIFO (큐 당 순서 보장) | Partition 내에서만 순서 보장 (전역 순서 보장 X) |
| **확장성** | 수직 확장(Scale-up)이 쉬우나 수평 확장은 제한적 | 파티션(Partition) 단위 수평 확장(Scale-out)이 매우 강력함 |
| **프로토콜** | AMQP, MQTT, STOMP (표준) | TCP 기반 자체 Binary 프로토콜 |
| **재생(Replay)** | 불가능 (삭제됨) | **가능** (Offset을 되감아서 과거 데이터 다시 처리 가능) |
| **속도** | Latency(지연 시간)가 낮음 (Real-time) | Throughput(처리량)이 높음 (High-volume) |

---

## 4. 성능 동작 원리 (Internal Mechanism)

### 4.1 RabbitMQ의 메커니즘
1. **Producer**가 `Exchange`에 메시지를 보냅니다.
2. `Exchange`는 `Binding Rule`에 따라 적절한 `Queue`로 메시지를 복사합니다.
3. `Queue`는 컨슈머에게 메시지를 전달하고, **Ack(확인)** 응답을 기다립니다.
4. Ack를 받으면 메모리/디스크에서 메시지를 영구 삭제합니다.
> **병목**: 브로커가 복잡한 라우팅과 상태 관리를 하므로, 트래픽이 몰리면 브로커 CPU/Memory 부하가 커집니다.

### 4.2 Kafka의 메커니즘
1. **Producer**가 `Topic`의 특정 `Partition`에 메시지를 **Append**(파일 끝에 쓰기)합니다.
2. OS의 **Page Cache**를 적극 활용하여 디스크 쓰기 속도를 메모리 수준으로 높입니다.
3. **Consumer**는 주기적으로 `Fetch` 요청을 보내 메시지를 배치(Batch)로 가져갑니다.
4. 네트워크 전송 시 `sendfile()` 시스템 콜(Zero-Copy)을 사용하여 CPU 개입을 최소화하고 커널 영역에서 바로 NIC로 데이터를 쏩니다.
> **병목**: 디스크 I/O가 병목이 될 수 있지만, 순차 쓰기(Sequential Write)라 HDD에서도 빠릅니다.

---

## 5. 예제 코드 및 설정 (Example)

### 5.1 RabbitMQ (Spring Boot)
"주문이 생성되면 알림 서비스와 배송 서비스로 동시에 전달" (Fanout 방식)

```java
@Configuration
public class RabbitConfig {
    // Fanout Exchange 생성
    @Bean
    public FanoutExchange orderExchange() {
        return new FanoutExchange("order.fanout");
    }

    // 큐 생성
    @Bean public Queue smsQueue() { return new Queue("sms.queue"); }
    @Bean public Queue deliveryQueue() { return new Queue("delivery.queue"); }

    // 바인딩
    @Bean public Binding bindSms() { return BindingBuilder.bind(smsQueue()).to(orderExchange()); }
}

@Service
public class RabbitConsumer {
    @RabbitListener(queues = "sms.queue")
    public void sendSms(OrderMsg msg) {
        System.out.println("문자 발송: " + msg.getId());
    }
}
```

### 5.2 Kafka (Spring Boot)
"주문 이벤트를 로그성으로 저장하고, 여러 컨슈머 그룹이 각자의 속도로 처리"

```java
// Producer
@Service
public class KafkaProducer {
    @Autowired private KafkaTemplate<String, String> kafkaTemplate;

    public void sendOrder(OrderMsg msg) {
        // partition key로 userId 사용 -> 동일 유저 주문은 순서 보장
        kafkaTemplate.send("order-events", msg.getUserId(), json(msg));
    }
}

// Consumer
@Service
public class KafkaConsumer {
    // Group ID가 다르면 동일한 메시지를 각각 다 받을 수 있음 (Pub/Sub)
    @KafkaListener(topics = "order-events", groupId = "analytics-group")
    public void analyze(String msg) {
        // 데이터 분석 로직 (느려도 상관 없음)
    }

    @KafkaListener(topics = "order-events", groupId = "notification-group")
    public void notify(String msg) {
        // 실시간 알림 로직 (빨라야 함)
    }
}
```

---

## 6. 결론: 언제 무엇을 선택해야 하는가?

### RabbitMQ를 선택해야 하는 경우
- **복잡한 라우팅**이 필요할 때 (Topic 기반 필터링 등).
- **메시지 처리 순서**와 **개별 메시지의 배달 보장**이 매우 중요할 때.
- 데이터 처리량이 엄청나게 많지는 않지만, **낮은 지연 시간(Low Latency)**이 필요할 때.
- 장기적인 데이터 저장이 필요 없을 때.

### Kafka를 선택해야 하는 경우
- **대용량 데이터 스트림** (로그, 클릭 이벤트, 센서 데이터)을 처리해야 할 때.
- **이벤트 소싱(Event Sourcing)** 아키텍처를 구현하여 과거 상태를 재생해야 할 때.
- 여러 컨슈머가 같은 데이터를 **다른 목적**으로 동시에 소비해야 할 때.
- 마이크로서비스 간의 데이터 파이프라인(Data Pipeline) 구축 시.

# Reference
- [Kafka vs RabbitMQ](https://www.confluent.io/blog/kafka-vs-rabbitmq/)
- [Spring AMQP Documentation](https://docs.spring.io/spring-amqp/reference/html/)
- [Spring Kafka Documentation](https://docs.spring.io/spring-kafka/reference/html/)