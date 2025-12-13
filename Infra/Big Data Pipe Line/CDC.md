---
id: CDC
started: 2025-12-13
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# CDC (Change Data Capture)

## 1. 개요 (Overview)
**CDC(Change Data Capture)** 는 데이터베이스의 데이터 변경(Insert, Update, Delete)을 실시간으로 감지하여 포착하고, 이를 다른 시스템(Data Warehouse, Cache, Search Engine 등)으로 전송하는 기술 또는 디자인 패턴을 의미한다.

현대의 마이크로서비스 아키텍처(MSA)나 이벤트 기반 아키텍처(EDA)에서 데이터 동기화는 핵심적인 과제이며, CDC는 이를 해결하는 가장 효율적인 방법 중 하나다.

### 1-1. 왜 필요한가?
- **실시간 데이터 동기화**: 배치(Batch) 처리의 지연 시간을 제거하고 실시간성을 확보.
- **마이크로서비스 간 느슨한 결합**: 소스 DB를 직접 조회(Polling)하지 않고 변경 이벤트만 구독.
- **마이그레이션**: 무중단 DB 마이그레이션 전략의 핵심 기술.
- **CQRS 패턴 구현**: 명령(Command) 모델의 변경사항을 조회(Query) 모델로 전파.

---

## 2. CDC 구현 방식 (Implementation Patterns)

### 2-1. 쿼리 기반 (Query-based / Polling)
애플리케이션이 주기적으로 DB를 조회하여 변경사항을 감지하는 방식.
- **원리**: `updated_at` 같은 타임스탬프 컬럼이나 `version` 컬럼을 주기적으로 `SELECT` 하여 확인.
- **장점**: 구현이 쉽다. 별도의 DB 설정이 거의 필요 없다.
- **단점**:
    - **DB 부하**: 잦은 폴링으로 인한 성능 저하.
    - **데이터 유실**: 폴링 주기 사이에 발생했다가 사라진 데이터나 중간 변경사항을 놓칠 수 있음.
    - **Delete 감지 불가**: 물리적으로 삭제된 행(Hard Delete)은 쿼리로 찾을 수 없다 (Soft Delete 강제 필요).

### 2-2. 로그 기반 (Log-based)
DB의 트랜잭션 로그(WAL, Binlog 등)를 직접 읽어서 변경사항을 추출하는 방식. (Debezium이 사용하는 방식)
- **원리**: DB가 내부적으로 기록하는 Redo Log / Write Ahead Log를 파싱.
- **장점**:
    - **완전성**: 모든 변경사항(Delete 포함)을 100% 감지 가능.
    - **저부하**: 실제 쿼리를 날리지 않으므로 DB 성능 영향이 적음.
    - **실시간성**: 로그 기록 즉시 이벤트 발생.
- **단점**: 구현이 복잡하고 DB 벤더마다 로그 포맷이 다름. (이를 해결해주는 것이 Debezium)

---

## 3. 실습: 쿼리 기반 CDC 구현 (Java Spring Boot)
가장 기초적인 형태의 CDC인 **Polling 방식** 을 Spring Boot로 구현해본다. 복잡한 인프라 없이 애플리케이션 레벨에서 구현 가능하다.

### 3-1. 사전 준비 (Server Setup)
- **Database**: PostgreSQL (Docker로 실행)
- **Table**: `products` 테이블에 `updated_at` 컬럼 필수.

#### Docker Compose (Postgres)
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
```

#### Table Schema
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 업데이트 시 자동으로 updated_at 갱신하는 트리거 (Postgres 기준)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();
```

### 3-2. Java Spring Boot 구현
Spring Scheduler를 사용하여 주기적으로 변경된 데이터를 Polling 하는 예제.

#### build.gradle
```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-web'
    runtimeOnly 'org.postgresql:postgresql'
}
```

#### Entity
```java
@Entity
@Table(name = "products")
@Getter @Setter
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
    private BigDecimal price;
    private LocalDateTime updatedAt;
}
```

#### Repository
```java
public interface ProductRepository extends JpaRepository<Product, Long> {
    // 마지막 확인 시간 이후에 변경된 데이터 조회
    List<Product> findByUpdatedAtGreaterThan(LocalDateTime lastCheckTime);
}
```

#### Polling CDC Service
```java
@Service
@Slf4j
public class PollingCdcService {

    private final ProductRepository productRepository;
    private LocalDateTime lastCheckTime = LocalDateTime.now(); // 초기화: 서버 시작 시점부터 감지

    public PollingCdcService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    // 5초마다 실행
    @Scheduled(fixedDelay = 5000)
    @Transactional(readOnly = true)
    public void captureChanges() {
        log.info("Checking for changes since: {}", lastCheckTime);

        List<Product> changedProducts = productRepository.findByUpdatedAtGreaterThan(lastCheckTime);

        if (changedProducts.isEmpty()) {
            return;
        }

        for (Product product : changedProducts) {
            // 변경 이벤트 발행 (Kafka로 보내거나, 로직 처리)
            publishEvent(product);
            
            // Cursor 이동 (가장 최신 시간으로 업데이트)
            if (product.getUpdatedAt().isAfter(lastCheckTime)) {
                lastCheckTime = product.getUpdatedAt();
            }
        }
    }

    private void publishEvent(Product product) {
        log.info("[CDC Event] Product Changed: ID={}, Name={}", product.getId(), product.getName());
        // TODO: KafkaTemplate.send("product-changes", product);
    }
}
```

#### Main Application (Enable Scheduling)
```java
@SpringBootApplication
@EnableScheduling // 스케줄링 활성화
public class CdcApplication {
    public static void main(String[] args) {
        SpringApplication.run(CdcApplication.class, args);
    }
}
```

---

## 4. 한계점 및 발전 (Limitations)
위의 Polling 방식은 간단하지만 치명적인 한계가 있다.
1. **Hard Delete 감지 불가**: `DELETE FROM products WHERE id = 1` 실행 시, 행이 사라지므로 `updated_at`을 조회할 수 없다.
2. **폴링 주기 딜레이**: 5초 주기로 설정했다면 최대 5초의 지연이 발생한다. 주기를 줄이면 DB 부하가 급증한다.

이러한 문제를 해결하기 위해 **Log-based CDC** (Debezium 등)가 사용된다. 이는 DB의 변경 로그(WAL)를 직접 구독하므로 삭제 이벤트까지 정확히, 실시간으로 감지할 수 있다.

> **Note**: 다음 문서 [Debezium](./Debezium.md) 에서 Log-based CDC의 구체적인 구현을 다룬다.
