---
id: Testcontainer와 TmpFS를 사용한 테스트
started: 2025-05-17
tags:
  - ✅DONE
group:
  - "[[TestContainer]]"
---
# Testcontainer와 TmpFS를 사용한 테스트

## Docker와 TmpFS를 이용한 Test

```kotlin title="build.gradle.kts"
testImplementation("org.testcontainers:testcontainers")  
testImplementation("org.testcontainers:junit-jupiter")

testImplementation("org.testcontainers:kafka")
testImplementation("org.testcontainers:postgresql")
```

```java title="DB Test"
@SpringBootTest
@Testcontainers
public class MyRepositoryTest {

    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test")
        .withTmpFsMapping(Map.of("/var/lib/postgresql/data", "rw")); // tmpfs

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry registry) {
        // 컨테이너의 정보를 spring.datasource.* 프로퍼티로 매핑
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @BeforeAll
    static void startContainer() {
        postgres.start();
    }

    @AfterAll
    static void stopContainer() {
        postgres.stop();
    }

    @Autowired
    MyRepository myRepository;

    @Test
    void testSomething() {
        // 실제 Postgres DB에서 테스트 수행
    }
}
```

아래와 같이 추상 클래스로 만들어 상속하도록 할 수도 있다.
```java title="AbstractPostgresContainerTest.java"
@Testcontainers
public abstract class AbstractPostgresContainerTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void setupProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }
}
```

```java title="Test Example"
@SpringBootTest
public class MyServiceTest extends AbstractPostgresContainerTest {

    @Autowired
    MyService myService;

    @Test
    void testLogic() {
        // Postgres는 이미 공유된 컨테이너로 실행됨
    }
}
```

### Redis
```java title="AbstractRedisContainerTest"
@Testcontainers
public abstract class AbstractRedisContainerTest {

    @Container
    static final GenericContainer<?> redis = new GenericContainer<>("redis:6.2")
        .withExposedPorts(6379);

    @DynamicPropertySource
    static void redisProps(DynamicPropertyRegistry registry) {
        registry.add("spring.redis.host", redis::getHost);
        registry.add("spring.redis.port", () -> redis.getMappedPort(6379));
    }
}
```

### Kafka
```java title="AbstractKafkaContainerTest"
@Testcontainers
public abstract class AbstractKafkaContainerTest {

    @Container
    static final KafkaContainer kafka = new KafkaContainer("confluentinc/cp-kafka:7.2.1");

    @DynamicPropertySource
    static void kafkaProps(DynamicPropertyRegistry registry) {
        kafka.start(); // 명시적으로 한 번만 실행
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
    }
}
```

```java title="AbstractKafkaContainerTest"
@SpringBootTest
public class KafkaServiceTest extends AbstractKafkaContainerTest {

    @Autowired
    KafkaTemplate<String, String> kafkaTemplate;

    @Test
    void testKafkaSendReceive() {
        kafkaTemplate.send("test-topic", "message");
        // 메시지 수신 테스트도 가능
    }
}
```

### MiniO
```java title="AbstractMinioContainerTest"
@Testcontainers
public abstract class AbstractMinioContainerTest {

    @Container
    static final GenericContainer<?> minio = new GenericContainer<>("minio/minio")
        .withEnv("MINIO_ACCESS_KEY", "minioadmin")
        .withEnv("MINIO_SECRET_KEY", "minioadmin")
        .withCommand("server /data")
        .withExposedPorts(9000);

    @DynamicPropertySource
    static void minioProps(DynamicPropertyRegistry registry) {
        minio.start();
        String endpoint = String.format("http://%s:%d",
                minio.getHost(), minio.getMappedPort(9000));
        registry.add("minio.url", () -> endpoint);
        registry.add("minio.access-key", () -> "minioadmin");
        registry.add("minio.secret-key", () -> "minioadmin");
    }
}
```

- Docker Compose 기반 컨테이너 하나로 여러 서비스 묶기
- Spring Cloud Stream + Kafka 통합 테스트
- `TestExecutionListener` 기반 자동 컨테이너 구성


## 병렬 테스트

```properties title="junit-platform.properties"
# 병렬 실행 활성화  
junit.jupiter.execution.parallel.enabled=true  
# 클래스/메서드 병렬 실행  
junit.jupiter.execution.parallel.mode.default=concurrent  
junit.jupiter.execution.parallel.mode.classes.default=concurrent  
# 동적 병렬 전략 사용 (기본값은 CPU 코어 수)  
junit.jupiter.execution.parallel.config.strategy=dynamic  
# 최대 병렬 실행 수 제한(소숫점은 코어수를 곱한것만큼 병렬 fork)junit.jupiter.execution.parallel.config.dynamic.factor=0.5
```

```properties title=".testcontainers.properties"
testcontainers.reuse.enable=true
```

```java title="SharedPostgresTestConfig.java"
@TestConfiguration
public class SharedPostgresTestConfig {

    private static final PostgreSQLContainer<?> sharedPostgres = new PostgreSQLContainer<>("postgres:16")
            .withUsername("test")
            .withPassword("test")
            .withReuse(true); // 속도 최적화

    static {
        sharedPostgres.start();
    }

    public static PostgreSQLContainer<?> getContainer() {
        return sharedPostgres;
    }

    public static void createDatabase(String dbName) {
        try (Connection conn = DriverManager.getConnection(
                sharedPostgres.getJdbcUrl().replace("/test", "/postgres"),
                sharedPostgres.getUsername(),
                sharedPostgres.getPassword()
        )) {
            conn.createStatement().execute("CREATE DATABASE " + dbName);
        } catch (SQLException e) {
            throw new RuntimeException("DB 생성 실패: " + dbName, e);
        }
    }

    public static void dropDatabase(String dbName) {
        try (Connection conn = DriverManager.getConnection(
                sharedPostgres.getJdbcUrl().replace("/test", "/postgres"),
                sharedPostgres.getUsername(),
                sharedPostgres.getPassword()
        )) {
            conn.createStatement().execute("DROP DATABASE IF EXISTS " + dbName);
        } catch (SQLException e) {
            System.err.println("DB 삭제 실패: " + dbName);
        }
    }
}
```

```java title="IsolatedDatabaseTest"
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public abstract class IsolatedDatabaseTest {

    protected String dbName;

    @BeforeAll
    void setUpDatabase() {
        dbName = "testdb_" + UUID.randomUUID().toString().replace("-", "_");
        SharedPostgresTestConfig.createDatabase(dbName);
    }

    @AfterAll
    void tearDownDatabase() {
        SharedPostgresTestConfig.dropDatabase(dbName);
    }

    @DynamicPropertySource
    static void registerProps(DynamicPropertyRegistry registry) {
        var container = SharedPostgresTestConfig.getContainer();

        // 실제 연결은 DB 이름이 설정된 상태에서 다시 구성
        registry.add("spring.datasource.username", container::getUsername);
        registry.add("spring.datasource.password", container::getPassword);
    }

    @DynamicPropertySource
    void dbNameProp(DynamicPropertyRegistry registry) {
        String jdbcUrl = SharedPostgresTestConfig.getContainer().getJdbcUrl()
                .replace("/test", "/" + dbName);
        registry.add("spring.datasource.url", () -> jdbcUrl);
    }
}
```

```java title="UserServiceTest Example"
@SpringBootTest
public class UserServiceTest extends IsolatedDatabaseTest {

    @Autowired
    UserRepository userRepository;

    @Test
    void testUserSave() {
        userRepository.save(new User("hello"));
        assertEquals(1, userRepository.count());
    }
}
```

### Redis
```java title="SharedRedisContainerConfig.java"
@TestConfiguration
public class SharedRedisContainerConfig {

    private static final GenericContainer<?> redisContainer = new GenericContainer<>("redis:6.2")
            .withExposedPorts(6379)
            .withReuse(true); // 성능 최적화

    static {
        redisContainer.start();
    }

    public static String getHost() {
        return redisContainer.getHost();
    }

    public static Integer getPort() {
        return redisContainer.getMappedPort(6379);
    }
}
```

```java title="IsolatedRedisTest.java"
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public abstract class IsolatedRedisTest {

    private static final AtomicInteger NEXT_REDIS_DB = new AtomicInteger(0); // 0~15까지 사용

    protected int redisDbIndex;

    @BeforeAll
    void allocateRedisDb() {
        redisDbIndex = NEXT_REDIS_DB.getAndIncrement();
        if (redisDbIndex > 15) {
            throw new IllegalStateException("Redis DB 번호 초과 (최대 16개까지 병렬 가능)");
        }
    }

    @DynamicPropertySource
    void registerRedisProps(DynamicPropertyRegistry registry) {
        registry.add("spring.redis.host", SharedRedisContainerConfig::getHost);
        registry.add("spring.redis.port", SharedRedisContainerConfig::getPort);
        registry.add("spring.redis.database", () -> redisDbIndex);
    }
}
```

```java title="RedisServiceTest.java"
@SpringBootTest
public class RedisServiceTest extends IsolatedRedisTest {

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Test
    void testIsolatedRedisDb() {
        redisTemplate.opsForValue().set("key", "value");
        assertEquals("value", redisTemplate.opsForValue().get("key"));
    }
}
```

### Kafka
```java title="SharedKafkaContainerConfig.java"
@TestConfiguration
public class SharedKafkaContainerConfig {

    private static final KafkaContainer kafkaContainer =
        new KafkaContainer("confluentinc/cp-kafka:7.2.1")
            .withReuse(true); // 성능 최적화

    static {
        kafkaContainer.start();
    }

    public static String getBootstrapServers() {
        return kafkaContainer.getBootstrapServers();
    }
}
```

```java title="IsolatedKafkaTest.java"
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public abstract class IsolatedKafkaTest {

    protected String topicName;

    @BeforeAll
    void init() {
        topicName = "test_topic_" + UUID.randomUUID().toString().replace("-", "");
    }

    @DynamicPropertySource
    void registerKafkaProps(DynamicPropertyRegistry registry) {
        registry.add("spring.kafka.bootstrap-servers", SharedKafkaContainerConfig::getBootstrapServers);
    }

    public String getTopicName() {
        return topicName;
    }
}
```

```java title="KafkaServiceTest.java"
@SpringBootTest
public class KafkaServiceTest extends IsolatedKafkaTest {

    @Autowired
    KafkaTemplate<String, String> kafkaTemplate;

    @Test
    void testSendToUniqueTopic() throws Exception {
        kafkaTemplate.send(getTopicName(), "hello kafka");

        // 필요한 경우 consumer로 수신 테스트도 가능
    }
}
```

토픽 이름을 명시적으로 만들고 싶다면
```java title="createTopic method"
public void createTopic(String topicName, int partitions, short replicationFactor) {
    try (AdminClient admin = AdminClient.create(Map.of("bootstrap.servers", SharedKafkaContainerConfig.getBootstrapServers()))) {
        NewTopic newTopic = new NewTopic(topicName, partitions, replicationFactor);
        admin.createTopics(List.of(newTopic)).all().get(5, TimeUnit.SECONDS);
    } catch (Exception e) {
        throw new RuntimeException("Kafka 토픽 생성 실패", e);
    }
}
```
위 메소드를 abstract class에 구현하고 `@beforeAll`에서 명시적으로 호출하면 된다.

### MiniO
```java title="SharedMinioContainerConfig.java"
@TestConfiguration
public class SharedMinioContainerConfig {

    private static final GenericContainer<?> minioContainer = new GenericContainer<>("minio/minio")
            .withEnv("MINIO_ACCESS_KEY", "minioadmin")
            .withEnv("MINIO_SECRET_KEY", "minioadmin")
            .withCommand("server /data")
            .withExposedPorts(9000)
            .withReuse(true); // 성능 최적화

    static {
        minioContainer.start();
    }

    public static String getEndpoint() {
        return String.format("http://%s:%d",
                minioContainer.getHost(),
                minioContainer.getMappedPort(9000));
    }

    public static String getAccessKey() {
        return "minioadmin";
    }

    public static String getSecretKey() {
        return "minioadmin";
    }
}
```

```java title="IsolatedMinioTest.java"
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public abstract class IsolatedMinioTest {

    protected String bucketName;

    @BeforeAll
    void initBucket() {
        bucketName = "test-bucket-" + UUID.randomUUID().toString().replace("-", "");
    }

    @DynamicPropertySource
    void minioProps(DynamicPropertyRegistry registry) {
        registry.add("minio.url", SharedMinioContainerConfig::getEndpoint);
        registry.add("minio.access-key", SharedMinioContainerConfig::getAccessKey);
        registry.add("minio.secret-key", SharedMinioContainerConfig::getSecretKey);
    }

    public String getBucketName() {
        return bucketName;
    }
}
```

```java title="MinioServiceTest.java"
@SpringBootTest
public class MinioServiceTest extends IsolatedMinioTest {

    @Autowired
    private MinioClient minioClient;

    @Test
    void testUploadToUniqueBucket() throws Exception {
        // 버킷 생성
        boolean exists = minioClient.bucketExists(BucketExistsArgs.builder().bucket(bucketName).build());
        if (!exists) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucketName).build());
        }

        // 파일 업로드
        minioClient.putObject(
            PutObjectArgs.builder()
                .bucket(bucketName)
                .object("test.txt")
                .stream(new ByteArrayInputStream("hello".getBytes()), "hello".length(), -1)
                .build()
        );

        // 다운로드 또는 검증 로직
    }
}
```

```java title="전부 합친 인테그레이션 테스트도 가능하다"
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
public abstract class FullStackIntegrationTest
        extends AbstractPostgresTest
        implements RedisSupport, KafkaSupport, MinioSupport {

    protected final String redisDb = allocateRedisDb();
    protected final String kafkaTopic = allocateKafkaTopic();
    protected final String minioBucket = allocateMinioBucket();

    @DynamicPropertySource
    static void dynamicProps(DynamicPropertyRegistry registry) {
        configurePostgres(registry);
        configureRedis(registry);
        configureKafka(registry);
        configureMinio(registry);
    }
}
```

## 테스트 파일트리 구성
```css
test/
├── support/
│   ├── container/
│   │   ├── SharedPostgresContainer.java
│   │   ├── SharedRedisContainer.java
│   │   ├── SharedKafkaContainer.java
│   │   └── SharedMinioContainer.java
│   └── base/
│       ├── AbstractPostgresTest.java
│       ├── AbstractRedisTest.java
│       ├── AbstractKafkaTest.java
│       └── AbstractMinioTest.java
└── YourServiceTest.java
```

```json title="JenkinsFile"
pipeline {
    agent {
        docker {
            image 'openjdk:17'
            args '-v /var/run/docker.sock:/var/run/docker.sock'  // Docker 접근 허용
        }
    }

    environment {
        TESTCONTAINERS_RYUK_DISABLED = 'true'
        TESTCONTAINERS_CHECKS_DISABLE = 'true'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build and Test') {
            steps {
                sh './gradlew clean test --info'
            }
        }
    }
}

```


# Reference
[GPT 히스토리](https://chatgpt.com/share/6827448e-3718-800a-9b35-765254339f7e)