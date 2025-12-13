---
id: Kafka Connect
started: 2025-12-13
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Kafka Connect

## 1. 개요 (Overview)
**Kafka Connect** 는 Apache Kafka와 다른 데이터 시스템(DB, Search Index, File System 등) 간에 데이터를 확장 가능하고 신뢰성 있게 스트리밍하기 위한 프레임워크다.

일반적으로 Kafka Producer/Consumer 코드를 직접 작성하지 않고도, 설정(Configuration)만으로 데이터를 import/export 할 수 있게 해준다.

### 1-1. 핵심 컴포넌트
- **Connector**: 데이터를 어디서 가져올지(Source), 어디로 보낼지(Sink)를 정의하는 논리적 작업 단위.
- **Task**: Connector가 작업을 병렬로 수행하기 위해 나누는 실행 단위.
- **Worker**: Connector와 Task를 실제로 실행하는 프로세스.
- **Converter**: 데이터를 저장할 때 형식을 변환 (JsonConverter, AvroConverter 등).

---

## 2. 분산 모드 vs 단독 모드

### 2-1. Standalone (단독 모드)
- 단일 프로세스로 실행. 설정이 파일로 관리됨.
- 개발 및 테스트 용도.

### 2-2. Distributed (분산 모드) ✨(Production)
- 여러 Worker 노드가 클러스터를 구성.
- Kafka 토픽을 사용하여 설정, 오프셋, 상태를 공유.
- REST API를 통해 런타임에 Connector를 추가/제거 가능.
- 고가용성(HA) 및 확장성(Scale-out) 지원.

---

## 3. 설치 및 실행 (Installation)
Kafka Connect는 Apache Kafka 바이너리에 포함되어 있다. 하지만 실제로는 JDBC 등 다양한 플러그인이 미리 포함된 **Confluent Platform**을 사용하는 것이 편리하다.

### 3-1. Docker Compose (Kafka + Connect)
`cp-kafka-connect` 이미지를 사용하여 구성한다.

```yaml
version: '2'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.3.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.3.0
    depends_on: [zookeeper]
    ports: [9092:9092]
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  connect:
    image: confluentinc/cp-kafka-connect:7.3.0
    depends_on: [kafka]
    ports: [8083:8083] # REST API 포트
    environment:
      CONNECT_BOOTSTRAP_SERVERS: kafka:9092
      CONNECT_REST_PORT: 8083
      CONNECT_GROUP_ID: compose-connect-group
      CONNECT_CONFIG_STORAGE_TOPIC: docker-connect-configs
      CONNECT_OFFSET_STORAGE_TOPIC: docker-connect-offsets
      CONNECT_STATUS_STORAGE_TOPIC: docker-connect-status
      CONNECT_KEY_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_VALUE_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      # 중요: 플러그인 경로 설정
      CONNECT_PLUGIN_PATH: "/usr/share/java,/usr/share/confluent-hub-components"
```

---

## 4. 실습: JDBC Source Connector 설정
DB의 테이블 데이터를 Kafka 토픽으로 가져오는 JDBC Connector를 REST API로 등록해본다.

### 4-1. Connector 등록 요청 (curl)
```bash
curl -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d '{
  "name": "jdbc-source-postgres",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
    "tasks.max": "1",
    "connection.url": "jdbc:postgresql://postgres:5432/mydb",
    "connection.user": "user",
    "connection.password": "password",
    "mode": "incrementing",
    "incrementing.column.name": "id",
    "topic.prefix": "postgres-",
    "poll.interval.ms": 1000
  }
}'
```
- **mode**: `incrementing`은 ID가 증가할 때마다 가져옴 (Insert 감지). Update 감지하려면 `timestamp` 모드 사용 필요.
- **topic.prefix**: 테이블명 앞에 붙을 접두사. (예: `products` 테이블 -> `postgres-products` 토픽 생성)

---

## 5. Spring Boot Consumer 구현
Kafka Connect가 DB에서 데이터를 퍼올려 Kafka 토픽(`postgres-products`)에 넣으면, Spring Boot 애플리케이션이 이를 소비(Consume)한다.

### 5-1. Dependencies (build.gradle)
```groovy
dependencies {
    implementation 'org.springframework.kafka:spring-kafka'
    implementation 'com.fasterxml.jackson.core:jackson-databind'
}
```

### 5-2. Application.yaml
```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    consumer:
      group-id: my-group
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "*"
```

### 5-3. Kafka Listener Service
Kafka Connect(JSON Converter)가 보낸 데이터 구조(Schema + Payload)를 파싱하여 처리한다.

```java
@Service
@Slf4j
public class ConnectOwnerService {

    // Connect가 생성한 토픽 구독
    @KafkaListener(topics = "postgres-products")
    public void consume(String message) {
        log.info("Raw Message: {}", message);
        
        // Kafka Connect의 기본 JSON 포맷은 { "schema": {...}, "payload": {...} } 형태임
        try {
            ObjectMapper mapper = new ObjectMapper();
            JsonNode root = mapper.readTree(message);
            JsonNode payload = root.path("payload");
            
            if (!payload.isMissingNode()) {
                Long id = payload.get("id").asLong();
                String name = payload.get("name").asText();
                Double price = payload.get("price").asDouble();
                
                log.info("Processed Product: ID={}, Name={}, Price={}", id, name, price);
                // 비즈니스 로직 수행 (예: 검색엔진 인덱싱, 알림 발송)
            }
        } catch (Exception e) {
            log.error("Failed to parse message", e);
        }
    }
}
```

## 6. 결론
Kafka Connect를 사용하면 **"DB -> App -> Kafka"** 가 아니라 **"DB -> Kafka Connect -> Kafka -> App"** 구조가 된다.
- **장점**: 개발자가 DB 연결 및 폴링 로직을 짤 필요가 없다. (Connect가 담당)
- **단점**: Connect 클러스터 운영 부담. 상세한 필터링 로직을 넣기 어렵다 (SMT - Simple Message Transform을 써야 함).

이것을 더 발전시켜 Log-based로 DB 변경사항을 완벽하게 캡처하는 것이 바로 **Debezium** 이다.
