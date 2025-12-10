---
id: Spring Cloud Stream
started: 2025-08-15
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Stream

## 1. 개요 (Overview)
**Spring Cloud Stream**은 메시지 기반 마이크로서비스를 구축하기 위한 **프레임워크**입니다.
가장 큰 특징은 **미들웨어(메시지 브로커)와의 결합을 끊어내는 추상화(Abstraction)**입니다. 개발자는 Kafka나 RabbitMQ의 구체적인 API를 몰라도, 비즈니스 로직(Producer, Processor, Consumer)에만 집중할 수 있습니다. 브로커 교체 시 코드 변경 없이 설정(Binder)만 바꾸면 됩니다.

---

## 2. 핵심 아키텍처 (Architecture)

### 2.1 Binder (바인더)
외부 메시징 시스템(Kafka, RabbitMQ, Kinesis 등)와의 통신을 담당하는 컴포넌트입니다.
- 애플리케이션과 브로커 사이의 어댑터 역할을 합니다.
- `spring-cloud-stream-binder-kafka`, `spring-cloud-stream-binder-rabbit` 등의 의존성을 추가하면 자동으로 구성됩니다.

### 2.2 Binding (바인딩)
애플리케이션의 입력/출력 채널을 외부 브로커의 목적지(Topic, Exchange)와 연결하는 다리입니다.
- 과거에는 `@EnableBinding`, `@StreamListener` 등을 썼지만, **Spring Cloud Stream 3.x부터는 함수형 프로그래밍(Functional Programming) 모델**로 완전히 대체되었습니다.

### 2.3 Message
헤더(Header)와 페이로드(Payload)를 가진 정규화된 데이터 구조입니다. 어떤 브로커를 쓰든 애플리케이션 내부에서는 통일된 Message 객체를 다룹니다.

---

## 3. 함수형 프로그래밍 모델 (Functional Model)

Java 8의 `java.util.function` 패키지를 활용하여 메시지 처리 로직을 정의합니다. Spring Cloud Stream은 Bean으로 등록된 함수들을 감지하여 자동으로 바인딩을 생성합니다.

| 인터페이스 | 역할 | Kafka 매핑 | 패턴 |
| --- | --- | --- | --- |
| **Supplier<T>** | 데이터 생성 (Source) | Producer | 주기적으로 실행(Poller)되어 메시지 발행 |
| **Consumer<T>** | 데이터 소비 (Sink) | Consumer | 토픽을 구독하고 메시지를 처리 |
| **Function<T, R>** | 데이터 가공 (Processor) | Streams | Input 토픽에서 읽어서 가공 후 Output 토픽으로 전송 |

---

## 4. 구현 및 설정 예제

### 4.1 의존성 추가 (Gradle)
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-stream-kafka'
```

### 4.2 비즈니스 로직 구현 (POJO)
Kafka API가 전혀 없는 순수 Java 코드입니다.

```java
@Configuration
@Slf4j
public class StreamConfig {

    // 1. Producer (Supplier): 1초마다 실행되어 문자열 발행
    @Bean
    public Supplier<OrderEvent> orderSource() {
        return () -> {
            OrderEvent event = new OrderEvent(UUID.randomUUID().toString(), "CREATED");
            log.info("Publishing event: {}", event);
            return event; // 리턴 값이 브로커로 전송됨
        };
    }

    // 2. Processor (Function): 문자열을 받아서 대문자로 변환 후 리턴
    @Bean
    public Function<OrderEvent, String> orderProcessor() {
        return event -> {
            log.info("Processing event: {}", event);
            return "PROCESSED: " + event.getOrderId(); // 리턴 값이 다음 토픽으로 전송됨
        };
    }

    // 3. Consumer (Consumer): 최종 결과 소비
    @Bean
    public Consumer<String> orderSink() {
        return message -> {
            log.info("Consumed message: {}", message);
        };
    }
}
```

### 4.3 설정 바인딩 (application.yml)
함수 이름(`orderSource`, `orderProcessor`, `orderSink`)을 기반으로 채널 이름이 자동 생성됩니다.
- 입력 채널: `<functionName>-in-<index>`
- 출력 채널: `<functionName>-out-<index>`

이 채널들을 실제 카프카 토픽과 매핑합니다.

```yaml
spring:
  cloud:
    stream:
      function:
        definition: orderSource;orderProcessor;orderSink # 활성화할 함수들
      bindings:
          destination: my-input-topic
        upperCase-in-0:
          destination: my-process-topic
        upperCase-out-0:
          destination: my-output-topic
```

# Reference
https://tech.kakaopay.com/post/spring-cloud-stream/