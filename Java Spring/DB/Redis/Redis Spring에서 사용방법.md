---
id: Redis
started: 2025-02-20
last modified: 2025-02-21
tags:
  - ✅DONE
  - Java
group: "[[Java Spring Redis]]"
---
# Redis
## 1.Add dependencies for Redis

**build.gradle.kts**
```java
implementation 'org.springframework.boot:spring-boot-starter-data-redis'
```

**application.yaml**
```yaml
spring:
  redis:
	host: localhost
    port: 6379
```

> [!INFO] TIP
>  Spring boot 2.0부터 RedisTemplate와 StringTemplate를 자동으로 빈을 만들어서 등록한다.

## 2. RedisRepository
### Redis Entity
```Java
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@RedisHash(value = "refresh_token")
public class RefreshToken {
	
    @Id
    private String authId;
	
    @Indexed
    private String token;
	
    private String role;
	
    @TimeToLive
    private long ttl;
	
    public RefreshToken update(String token, long ttl) {
        this.token = token;
        this.ttl = ttl;
        return this;
    }
}
```
- **@Id** - **키**(key) 값 **auto-increment** 된다.
- **@RedisHash -** Redis Entity **key의 prefix**로 사용한다. (Redis는 테이블이 없으므로 필요하다.)
- **@Indexed** - 인덱스 테이블을 설정한다.
- **@TimeToLive** - 만료시간(**초** 단위)
### RedisRepository
```Java
public interface RefreshTokenRepository 
extends CrudRepository<RefreshToken, String> {
    Optional<RefreshToken> findByToken(String token);
    Optional<RefreshToken> findByAuthId(String authId);
}
```
JpaRepository를 사용하는 것 처럼, **CrudRepository** 인터페이스를 상속받는다. **@Id** 또는 **@Indexed** 어노테이션을 적용한 프로퍼티들만 CrudRepository가 제공하는 **findBy~** 구문을 사용할 수 있다.
## 3. Redis Template
### 3.1. Redis Template
```Java
@Service
public class RedisUtils {
	
    private final RedisTemplate<String, Object> redisTemplate;
	
    public RedisUtils(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }
    
    public void setData(String key, String value,Long expiredTime){
        redisTemplate.opsForValue().set(key, value, expiredTime, TimeUnit.MILLISECONDS);
    }
    
    public String getData(String key){
        return (String) redisTemplate.opsForValue().get(key);
    }
    
    public void deleteData(String key){
        redisTemplate.delete(key);
    }
}
```
Redis Template는 Value의 타입마다 제공하는 메소드가 다르다.
![[Pasted image 20250221155431.png]]
## 4. Redis Cache
### @EnableCaching
Redis Caching을 사용하려면 Main Class에 어노테이션을 붙여주어야 함.
```Java
@SpringBootApplication
@EnableCaching
public class SpringBootRedisSimpleStarterApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootRedisSimpleStarterApplication.class, args);
    }
}
```

Spring application.yaml에 다음과 같이 redis를 캐시로 사용하겠다고 설정하여야 함.
```yaml
spring:
  cache:
    type: redis
```


Redis를 Spring boot Configuration으로 설정이 가능하다.
```Java
@Configuration
@EnableCaching
public class RedisCacheConfig {

    @Bean
    public CacheManager rcm(RedisConnectionFactory cf) {
        RedisCacheConfiguration redisCacheConfiguration = RedisCacheConfiguration.defaultCacheConfig()
                .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()))
                .entryTtl(Duration.ofMinutes(3L));

        return RedisCacheManager
                .RedisCacheManagerBuilder
                .fromConnectionFactory(cf)
                .cacheDefaults(redisCacheConfiguration)
                .build();
    }
}
```

### @Cacheable
- 리턴 값을 기준으로 데이터가 캐시에 있으면 그대로 반환, 없으면 저장 후 반환한다.
- 보통 조회와 같은 API에 많이 사용됨
![[Pasted image 20250221155739.png]]
### @CachePut
- 캐시에 데이터를 저장할 때만 사용한다.
- **@Cacheable**과 다르게 캐시에 저장된 데이터를 사용하지 않는다.
- 보통 수정과 같은 API에 많이 사용됨
![[Pasted image 20250221160234.png]]
### @CacheEvict
- 메서드가 호출될 때 캐시에 있는 데이터가 삭제된다.
- 보통 삭제와 같은 API에 많이 사용됨
![[Pasted image 20250221160252.png]]

## 7. API에 캐싱 적용하기 - Example

```Java
@RequestMapping("/log")
@RestController
@RequiredArgsConstructor
public class LogController {

    private final LogService logService;

    @GetMapping
    public ResponseEntity<List<LogResponse>> getAll() {
        List<LogResponse> logs = logService.searchAll();
        return ResponseEntity.ok(logs);
    }

    @DeleteMapping
    public void deleteAll() {
        logService.removeAll();
    }
}
```

```Java
@Cacheable(cacheNames = "searchAll", key = "#root.target + #root.methodName", sync = true, cacheManager = "rcm")
public List<LogResponse> searchAll() {
    return logFacade.findAllOrderByDateAtDesc()
            .stream()
            .map(LogResponse::new)
            .collect(Collectors.toList());
}

@CacheEvict(cacheNames = "searchAll", allEntries = true, beforeInvocation = true, cacheManager = "rcm")
@Transactional
public void removeAll() {
    logFacade.removeAll();
}
```




# Reference
[Spring Boot + Redis 제대로 활용하기](https://developer-nyong.tistory.com/21)
[Spring boot Redis 사용하기](https://westmino.tistory.com/157)
[Spring Boot - Redis 사용하기](https://velog.io/@yoojkim/Spring-Boot-Redis-%EC%82%AC%EC%9A%A9%ED%95%98%EA%B8%B0)
[Jedis 보다 Lettuce 를 쓰자](https://jojoldu.tistory.com/418)
[Spring Cache, 제대로 사용하기](https://gngsn.tistory.com/157)
[Spring boot에서 Redis Cache 사용하기](https://deveric.tistory.com/98)
[SpringBoot에서 Redis 캐시를 사용하기](https://www.wool-dev.com/backend-engineering/spring/springboot-redis-cache#%EC%82%AC%EC%9A%A9-%ED%95%A0-redis-%EA%B0%84%EB%8B%A8-%EC%84%A4%EB%AA%86)
[JAVA Spring Boot - Rest API + 레디스 캐시 (Redis Cache) 적용 및 샘플 예제](https://kim-oriental.tistory.com/28)