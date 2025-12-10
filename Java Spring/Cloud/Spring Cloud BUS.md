---
id: Spring Cloud BUS
started: 2025-08-24
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Bus

## 1. 개요 (Overview)
**Spring Cloud Bus**는 분산 시스템의 노드들을 **경량 메시지 브로커(RabbitMQ, Kafka)**로 연결하여, 상태 변경(State Change)이나 이벤트(Event)를 브로드캐스팅(Broadcasting)하는 프레임워크입니다.
가장 대표적인 사용 사례는 **Spring Cloud Config의 설정 변경 사항을 전체 마이크로서비스에 실시간으로 전파(Refresh)**하는 것입니다. 각 노드마다 일일이 API를 호출할 필요 없이, 버스에 메시지 하나만 쏘면 모든 노드가 이를 받아 처리합니다.

---

## 2. 아키텍처 및 동작 원리

### 2.1 메시지 브로커 연동
Spring Cloud Bus는 **Spring Cloud Stream**을 기반으로 동작합니다. 따라서 Stream이 지원하는 Binder(Kafka, RabbitMQ)가 클래스패스에 있어야 합니다.
- **Topic/Exchange**: 기본적으로 `springCloudBus`라는 이름의 토픽(또는 익스체인지)을 사용합니다.
- **Consumer Group**: 각 애플리케이션 인스턴스는 서로 다른 그룹(또는 익명 그룹)으로 간주되어 모든 인스턴스가 메시지를 수신합니다(Pub/Sub 모델). 단, `spring-boot-admin` 같은 모니터링 도구는 특정 이벤트를 필터링해서 받을 수도 있습니다.

### 2.2 설정 갱신 흐름 (Config Refresh Flow)
1.  개발자가 Git 저장소의 `application.yml`을 수정하고 커밋/푸시합니다.
2.  (옵션) Webhook이 트리거되어 Config Server의 `/actuator/bus-refresh` 엔드포인트를 호출합니다.
3.  Config Server는 "설정이 바뀌었다"는 `RefreshRemoteApplicationEvent` 이벤트를 Bus(Kafka/RabbitMQ)에 발행합니다.
4.  Bus를 구독하고 있던 모든 마이크로서비스 인스턴스들이 이 이벤트를 수신합니다.
5.  각 인스턴스는 `ContextRefresher`를 실행하여 Config Server로부터 최신 설정을 다시 읽어오고, `@RefreshScope` 빈들을 갱신합니다.

---

## 3. 핵심 기능 (Key Features)

### 3.1 Global & Targeted Broadcast
이벤트를 전체 노드에 보낼 수도 있지만, 특정 서비스만 타겟팅할 수도 있습니다.
- **Global**: 모든 서비스 갱신.
- **Targeted**: `destination` 파라미터를 사용하여 특정 서비스(`customers:**`) 또는 특정 인스턴스(`customers:8080`)만 지정 가능합니다. ant-style 패턴 매칭을 지원합니다.
    - 예: `POST /actuator/bus-refresh?destination=customers:**`

### 3.2 Custom Event (사용자 정의 이벤트)
설정 갱신 외에도, 사용자가 정의한 비즈니스 이벤트(예: 캐시 초기화, 세션 만료 등)를 전체 노드에 전파하는 용도로 활용할 수 있습니다.

---

## 4. 구현 예제

### 4.1 의존성 추가 (Kafka 예시)
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-bus-kafka'
implementation 'org.springframework.boot:spring-boot-starter-actuator'
```

### 4.2 설정 (application.yml)
```yaml
spring:
  cloud:
    bus:
      enabled: true
      # id: 구분자로 쓰임. 보통 application 이름 + 포트 + 랜덤값 조합
    stream:
      kafka:
        binder:
          brokers: localhost:9092
          
management:
  endpoints:
    web:
      exposure:
        include: bus-refresh # 엔드포인트 노출
```

### 4.3 커스텀 이벤트 발행 및 수신

**1) 이벤트 정의**
`RemoteApplicationEvent`를 상속받아야 합니다. 직렬화를 위해 기본 생성자와 getter/setter가 필요합니다.
```java
public class MyCacheClearEvent extends RemoteApplicationEvent {
    
    private String cacheName;

    public MyCacheClearEvent(Object source, String originService, String destinationService, String cacheName) {
        super(source, originService, destinationService);
        this.cacheName = cacheName;
    }
    // Getter, NoArgsConst...
}
```

**2) 이벤트 발행 (Publisher)**
`ApplicationEventPublisher`를 사용합니다.
```java
@Service
@RequiredArgsConstructor
public class CacheService {
    
    private final ApplicationEventPublisher publisher;
    private final BusProperties busProperties; // 내 서비스 ID 알기 위해

    public void clearGlobalCache(String cacheName) {
        // null destination = 전체 전송
        MyCacheClearEvent event = new MyCacheClearEvent(this, busProperties.getId(), null, cacheName);
        publisher.publishEvent(event);
    }
}
```

**3) 이벤트 수신 (Listener)**
`@EventListener`로 받습니다.
```java
@Component
@Slf4j
public class MyEventListener {

    @EventListener
    public void onCacheClear(MyCacheClearEvent event) {
        log.info("Received clear cache event for: {}", event.getCacheName());
        // 실제 캐시 삭제 로직 수행
    }
}
```

---

## 5. 트러블슈팅 및 팁

### 5.1 Bus Trace
`/actuator/httptrace` 처럼 Bus를 타고 흐른 이벤트들의 이력을 보고 싶다면 `spring.cloud.bus.trace.enabled=true`를 설정합니다. (단, 메모리를 먹으므로 운영에선 주의)

### 5.2 이벤트 루프 주의
내가 발행한 이벤트를 나도 다시 받는 구조입니다(`ack`가 아님). `RemoteApplicationEvent`에는 `originService` 필드가 있어, 내가 보낸 건지 남이 보낸 건지 식별할 수 있습니다. Spring Cloud Bus는 기본적으로 자신이 보낸 이벤트는 무시하도록 처리되어 있지만, 커스텀 로직 짤 때 주의해야 합니다.

# Reference
- [Spring Cloud Bus Documentation](https://docs.spring.io/spring-cloud-bus/docs/current/reference/html/)
- [Broadcasting Your Own Events](https://www.baeldung.com/spring-cloud-bus#custom-events)
- [Env Refresh with Spring Cloud Bus](https://spring.io/guides/gs/centralized-configuration/)