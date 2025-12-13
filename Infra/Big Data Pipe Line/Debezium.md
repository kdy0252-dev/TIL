---
id: Debezium
started: 2025-12-13
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Debezium

## 1. 개요 (Overview)
**Debezium** 은 가장 널리 사용되는 오픈소스 분산 **CDC(Change Data Capture)** 플랫폼이다.
데이터베이스의 로우 레벨 변경사항(Transaction Log)을 모니터링하여, Insert/Update/Delete 이벤트를 스트림으로 변환한다.

일반적으로 Kafka Connect 위에서 동작하는 **Source Connector** 형태로 사용되지만, 애플리케이션 내부에 라이브러리로 내장하여(**Embedded**) 사용할 수도 있다.

### 1-1. 주요 지원 DB
- MySQL (Binlog)
- PostgreSQL (WAL - pgoutput)
- MongoDB (Oplog)
- Oracle (LogMiner)
- SQL Server (CDC)

---

## 2. 아키텍처 및 동작 원리

### 2-1. Debezium + Kafka Connect (표준 방식)
1. DB에서 변경 발생 (Commit).
2. Debezium Connector(Kafka Connect Worker 내부)가 DB 로그를 읽음.
3. 변경 전(Before) 값과 변경 후(After) 값을 포함한 이벤트를 생성.
4. Kafka 토픽에 JSON/Avro 형태로 전송.

### 2-2. Debezium Embedded (내장 방식)
Kafka나 Kafka Connect 클러스터 없이, **Java 애플리케이션 내부**에서 Debezium 엔진을 직접 실행.
- **장점**: 인프라 복잡도 감소 (Kafka 불필요).
- **단점**: HA(고가용성)를 직접 관리해야 함.

---

## 3. 설치 및 설정 (Kafka Connect 방식)
이미 Kafka Connect가 떠 있다고 가정하고, Debezium Postgres 커넥터를 등록하는 방법이다.

### 3-1. DB 설정 (Postgres)
PostgreSQL의 `wal_level`을 `logical`로 변경해야 한다.
```sql
ALTER SYSTEM SET wal_level = logical;
-- DB 재기작 필요
```

### 3-2. Connector 등록 (JSON)
```bash
curl -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d '{
  "name": "debezium-postgres-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "mydb",
    "database.server.name": "my-server", 
    "plugin.name": "pgoutput"
  }
}'
```
- **database.server.name**: 토픽 이름의 접두사가 됨. (예: `my-server.public.products`)

---

## 4. 실습: Spring Boot + Debezium Embedded Engine
Kafka 없이 Spring Boot 앱에서 바로 DB 변경사항을 리스닝하는 **Embedded Engine** 구현 예제.

### 4-1. Dependencies (build.gradle)
```groovy
dependencies {
    implementation 'io.debezium:debezium-api:1.9.6.Final'
    implementation 'io.debezium:debezium-embedded:1.9.6.Final'
    implementation 'io.debezium:debezium-connector-postgres:1.9.6.Final' // DB에 맞는 커넥터 필수
}
```

### 4-2. Debezium 설정 및 실행 Service
```java
@Service
@Slf4j
public class DebeziumListenerService {

    private final Executor executor = Executors.newSingleThreadExecutor();
    private DebeziumEngine<ChangeEvent<String, String>> debeziumEngine;

    @PostConstruct
    public void start() {
        // Debezium 설정 (Properties)
        Properties props = new Properties();
        props.setProperty("name", "engine");
        props.setProperty("connector.class", "io.debezium.connector.postgresql.PostgresConnector");
        
        // 오프셋 저장소 (파일 기반) - 로컬 테스트용
        props.setProperty("offset.storage", "org.apache.kafka.connect.storage.FileOffsetBackingStore");
        props.setProperty("offset.storage.file.filename", "/tmp/offsets.dat");
        props.setProperty("offset.flush.interval.ms", "60000");

        // DB 연결 정보
        props.setProperty("database.hostname", "localhost");
        props.setProperty("database.port", "5432");
        props.setProperty("database.user", "postgres");
        props.setProperty("database.password", "password");
        props.setProperty("database.dbname", "mydb");
        props.setProperty("database.server.name", "my-app-db-server");
        
        // 플러그인 설정
        props.setProperty("plugin.name", "pgoutput");

        // 엔진 빌드 (JSON 포맷으로 데이터 수신)
        debeziumEngine = DebeziumEngine.create(Json.class)
                .using(props)
                .notifying(this::handleChangeEvent)
                .build();

        // 비동기 실행
        executor.execute(debeziumEngine);
        log.info("Debezium Engine Started!");
    }

    @PreDestroy
    public void stop() throws IOException {
        if (debeziumEngine != null) {
            debeziumEngine.close();
        }
    }

    // 변경 이벤트 핸들러
    private void handleChangeEvent(ChangeEvent<String, String> event) {
        String key = event.key();
        String value = event.value();
        
        log.info("Key: {}, Value: {}", key, value);

        // JSON 파싱 (Jackson 등 사용)
        // Value 내부의 'op' 필드(c, u, d)를 확인하여 분기 처리
        // 'after' 필드에서 실제 데이터 추출
    }
}
```

### 4-3. 트랜잭션 로그 데이터 구조 (예시)
위의 `event.value()`로 들어오는 JSON 예시.
```json
{
  "before": null,
  "after": {
    "id": 1,
    "name": "Debezium Book",
    "price": 25000
  },
  "source": { "version": "1.9.6.Final", "connector": "postgresql", ... },
  "op": "c",  // c: create, u: update, d: delete
  "ts_ms": 1678888888888
}
```

---

## 5. 결론 및 요약
| 구분 | Debezium (Log-based) | Polling (Query-based) |
| :--- | :--- | :--- |
| **원리** | DB 로그(WAL) 직접 파싱 | 주기적인 SELECT 조회 |
| **Delete 감지** | 가능 (완벽함) | 불가능 (Soft Delete 필요) |
| **실시간성** | 매우 높음 (ms 단위) | 낮음 (Polling 주기에 의존) |
| **구축 난이도** | 높음 (Kafka 등 필요) | 낮음 (코드만 있으면 됨) |
| **시스템 부하** | 낮음 (소스 DB 영향 최소화) | 높음 (잦은 쿼리 부하) |

결론적으로 **본격적인 데이터 파이프라인**을 구축하거나 **완전한 정합성**이 필요하다면 **Debezium** 이 정답이다. 소규모 내부 동기화에는 Polling이 가볍고 빠를 수 있다.
