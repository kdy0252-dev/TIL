---
id: Redis for Parallel Test
started: 2025-05-26
tags:
  - ✅DONE
group:
  - "[[TestContainer]]"
---
# Redis for Parallel Test
## Test Container Config File
```java title="IsolatedRedisTest"
import com.dykim.study.support.config.TestRedisConfig;  
import java.util.UUID;  
import lombok.extern.slf4j.Slf4j;  
import org.jetbrains.annotations.NotNull;  
import org.junit.jupiter.api.TestInstance;  
import org.springframework.context.annotation.Import;  
import org.springframework.test.annotation.DirtiesContext;  
import org.springframework.test.context.DynamicPropertyRegistry;  
import org.testcontainers.containers.GenericContainer;  
import org.testcontainers.junit.jupiter.Container;  
import org.testcontainers.junit.jupiter.Testcontainers;  
import org.testcontainers.utility.DockerImageName;  
  
@Slf4j  
@Import(TestRedisConfig.class)  
@Testcontainers  
@TestInstance(TestInstance.Lifecycle.PER_CLASS)  
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)  
public abstract class IsolatedRedisTest {  
  
    @Container  
    static final GenericContainer<?> REDIS_CONTAINER =  
        new GenericContainer<>(DockerImageName.parse("redis:7.0.5"))  
            .withExposedPorts(6379)  
            .withReuse(true);  
  
    static {  
        REDIS_CONTAINER.start();  
    }  
  
    /** 하위 테스트 클래스에서 이 메서드를 한 줄만 호출하세요 */  
    protected static void initRedis(@NotNull DynamicPropertyRegistry registry) {  
        String host = REDIS_CONTAINER.getHost();  
        int port = REDIS_CONTAINER.getMappedPort(6379);  
        // UUID 기반으로 각 테스트 클래스(또는 컨텍스트)에 고유한 프리픽스 생성  
        String prefix = UUID.randomUUID().toString().substring(0, 8);  
  
        registry.add("spring.redis.host", () -> host);  
        registry.add("spring.redis.port", () -> port);  
        registry.add("test.redis.prefix", () -> prefix);  
  
        log.info("IsolatedRedisTest: Redis properties set for a test context. Host: {}, Port: {}, Prefix: {}",  
            host, port, prefix);  
    }  
}
```
## Test마다 다른 Prefix를 적용시키기위한 Serializer
```java title="PrefixStringRedisSerializer.java"
import org.springframework.data.redis.serializer.RedisSerializer;  
import org.springframework.data.redis.serializer.SerializationException;  
import org.springframework.data.redis.serializer.StringRedisSerializer;  
  
/**  
 * 키 직렬화 시점에 "{prefix}:{key}" 를 붙이고,  
 * 역직렬화 시에는 ":{prefix}" 부분을 떼어냅니다.  
 */public class PrefixStringRedisSerializer implements RedisSerializer<String> {  
  
    private final String prefix;  
    private final StringRedisSerializer delegate = new StringRedisSerializer();  
  
    public PrefixStringRedisSerializer(String prefix) {  
        this.prefix = prefix.endsWith(":") ? prefix : prefix + ":";  
    }  
  
    @Override  
    public byte[] serialize(String s) throws SerializationException {  
        return delegate.serialize(prefix + s);  
    }  
  
    @Override  
    public String deserialize(byte[] bytes) throws SerializationException {  
        String full = delegate.deserialize(bytes);  
        if (full != null && full.startsWith(prefix)) {  
            return full.substring(prefix.length());  
        }  
        return full;  
    }  
}
```
## Redis Connection을 위한 Spring Bean 등록
```java title="TestRedisConfig.java"
import java.util.Objects;  
import org.springframework.boot.test.context.TestConfiguration;  
import org.springframework.context.annotation.Bean;  
import org.springframework.core.env.Environment;  
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;  
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;  
import org.springframework.data.redis.core.StringRedisTemplate;  
  
@TestConfiguration  
public class TestRedisConfig {  
    @Bean  
    public LettuceConnectionFactory redisConnectionFactory(Environment env) {  
        String host = env.getProperty("spring.redis.host");  
        int port = Integer.parseInt(Objects.requireNonNull(env.getProperty("spring.redis.port")));  
        assert host != null;  
        RedisStandaloneConfiguration conf = new RedisStandaloneConfiguration(host, port);  
        return new LettuceConnectionFactory(conf);  
    }  
  
    @Bean  
    public StringRedisTemplate stringRedisTemplate(  
        LettuceConnectionFactory cf, Environment env) {  
  
        String prefix = env.getProperty("test.redis.prefix", "");  
        PrefixStringRedisSerializer keySer = new PrefixStringRedisSerializer(prefix);  
  
        StringRedisTemplate tpl = new StringRedisTemplate(cf);  
        tpl.setKeySerializer(keySer);  
        tpl.setHashKeySerializer(keySer);  
        tpl.afterPropertiesSet();  
        return tpl;  
    }  
}
```
## Test Code
```java title="IsolatedRedisExampleTest.java"
import static org.assertj.core.api.AssertionsForClassTypes.assertThat;  
  
import com.dykim.study.support.base.IsolatedRedisTest;  
import lombok.extern.slf4j.Slf4j;  
import org.junit.jupiter.api.Test;  
import org.springframework.beans.factory.annotation.Autowired;  
import org.springframework.boot.test.context.SpringBootTest;  
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;  
import org.springframework.data.redis.core.StringRedisTemplate;  
import org.springframework.test.context.DynamicPropertyRegistry;  
import org.springframework.test.context.DynamicPropertySource;  
  
  
@Slf4j  
@SpringBootTest  
public class IsolatedRedisExampleTest extends IsolatedRedisTest {  
    // LettuceConnectionFactory를 직접 주입받아서 설정값을 조회  
    @Autowired  
    LettuceConnectionFactory connectionFactory;  
    @Autowired  
    private StringRedisTemplate redisTemplate;  
  
    @DynamicPropertySource  
    static void overrideProps(DynamicPropertyRegistry r) {  
        initRedis(r);  // 한 줄로 init 호출  
    }  
  
    @Test  
    void printDBInfo() {  
        // 사용 중인 Redis 정보 출력  
        log.info(  
            "▶ Redis 연결 정보: host={}, port={}, dbIndex={}",  
            connectionFactory.getHostName(),  
            connectionFactory.getPort(),  
            connectionFactory.getDatabase()  
        );  
    }  
  
    @Test  
    void testIsolatedRedisDb() {  
        redisTemplate.opsForValue().set("foo", "bar");  
        assertThat(redisTemplate.opsForValue().get("foo")).isEqualTo("bar");  
    }  
}
```

# Reference