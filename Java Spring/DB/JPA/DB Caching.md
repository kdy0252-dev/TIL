---
id: DB Caching
started: 2025-05-16
tags:
  - ✅DONE
group:
  - "[[Java Spring JPA]]"
---
# DB Caching
## DB Caching이란?
DB Caching은 데이터베이스의 데이터를 애플리케이션 레벨에서 캐싱하여 데이터베이스 접근 횟수를 줄이고 성능을 향상시키는 기술이다. 자주 사용되는 데이터를 캐시에 저장해두면, 데이터베이스에 직접 접근하지 않고 캐시에서 데이터를 빠르게 가져올 수 있다.
### DB Caching은 왜 사용할까?
DB Caching은 다음과 같은 장점을 제공한다.
*   **성능 향상**: 데이터베이스 접근 횟수를 줄여 응답 시간을 단축하고, 전체적인 애플리케이션 성능을 향상시킨다.
*   **데이터베이스 부하 감소**: 데이터베이스에 대한 부하를 줄여 데이터베이스 서버의 안정성을 높인다.
*   **확장성 향상**: 캐시를 통해 데이터베이스 부하를 분산시켜 애플리케이션의 확장성을 향상시킨다.
### DB Caching의 종류
DB Caching은 크게 다음과 같은 종류로 나눌 수 있다.
1.  **1차 캐시 (First-Level Cache)**: JPA EntityManagerFactory 단위로 관리되는 캐시이다. 영속성 컨텍스트 내에서만 유효하며, 트랜잭션이 종료되면 캐시가 소멸된다.
2.  **2차 캐시 (Second-Level Cache)**: EntityManagerFactory 단위로 관리되는 캐시이다. 여러 영속성 컨텍스트에서 공유되며, 애플리케이션 전체에서 유효하다.
3.  **애플리케이션 레벨 캐시 (Application-Level Cache)**: Ehcache, Redis, Hazelcast 등 외부 캐시 시스템을 사용하여 애플리케이션 레벨에서 캐싱한다.
## Java Spring에서의 DB Caching
Java Spring에서는 다음과 같은 방법으로 DB Caching을 구현할 수 있다.
1.  **JPA 1차 캐시**: JPA EntityManagerFactory에서 자동으로 관리되는 캐시이다. 별도의 설정 없이 사용할 수 있다.
2.  **JPA 2차 캐시**: JPA 2차 캐시를 사용하려면 설정이 필요하다. Ehcache, Hazelcast 등 다양한 캐시 프로바이더를 사용할 수 있다.
3.  **Spring Cache Abstraction**: Spring 프레임워크에서 제공하는 캐시 추상화 기능을 사용하여 Ehcache, Redis, Hazelcast 등 다양한 캐시 시스템을 통합할 수 있다.
### 1. JPA 1차 캐싱
JPA 1차 캐시는 EntityManagerFactory 단위로 관리되며, 영속성 컨텍스트 내에서만 유효하다.
```java
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    public User getUser(Long id) {
        // 1. 데이터베이스에서 User 조회
        User user = userRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("User not found"));

        // 2. 동일한 ID로 User 조회 (캐시에서 조회)
        User cachedUser = userRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("User not found"));

        // 3. user == cachedUser (true)
        System.out.println(user == cachedUser);

        return user;
    }
}
```
*   `userRepository.findById(id)`를 처음 호출할 때 데이터베이스에서 User를 조회하고, 영속성 컨텍스트에 저장한다.
*   두 번째 호출할 때에는 데이터베이스에 접근하지 않고 영속성 컨텍스트에서 User를 가져온다.
### 2. JPA 2차 캐싱
JPA 2차 캐시를 사용하려면 다음과 같은 설정을 해야 한다.
1.  **캐시 프로바이더 설정**: Ehcache, Hazelcast 등 캐시 프로바이더를 선택하고 설정한다.
2.  **JPA 설정**: `persistence.xml` 또는 Spring Boot 설정을 통해 2차 캐시를 활성화하고, 캐시 프로바이더를 지정한다.
3.  **엔티티 설정**: `@Cacheable` 어노테이션을 사용하여 캐시할 엔티티를 지정한다.
#### Spring Boot 설정으로 2차 캐시 활성화
`application.yml` 파일에 다음 설정을 추가하여 2차 캐시를 활성화할 수 있다.
```css title="application.yml"
spring:
  jpa:
    properties:
      hibernate:
        cache:
          use_second_level_cache: true
          use_query_cache: true
          region:
            factory_class: org.hibernate.cache.ehcache.EhCacheRegionFactory
        ehcache:
          config: classpath:ehcache.xml
```
- `spring.jpa.properties.hibernate.cache.use_second_level_cache`: 2차 캐시를 활성화한다.
- `spring.jpa.properties.hibernate.cache.use_query_cache`: 쿼리 캐시를 활성화한다.
- `spring.jpa.properties.hibernate.cache.region.factory_class`: 캐시 프로바이더를 Ehcache로 지정한다.
- `spring.jpa.properties.hibernate.ehcache.config`: Ehcache 설정 파일의 위치를 지정한다.
```java title="2차캐시 사용 예시"
@Entity
@Cacheable
public class User {
    @Id
    private Long id;

    private String name;
}
```
*   `persistence.xml`에서 2차 캐시를 활성화하고, Ehcache를 캐시 프로바이더로 지정한다.
*   `ehcache.xml`에서 Ehcache의 설정을 정의한다.
*   `@Cacheable` 어노테이션을 사용하여 User 엔티티를 캐시하도록 지정한다.
### 3. Spring Cache Abstraction
Spring Cache Abstraction은 Spring 프레임워크에서 제공하는 캐시 추상화 기능으로, Ehcache, Redis, Hazelcast 등 다양한 캐시 시스템을 통합할 수 있다.
#### 현업에서의 선호도
현업에서는 Redis를 가장 많이 사용하며, Hazelcast도 분산 캐싱 환경에서 많이 사용된다. Ehcache는 상대적으로 사용 빈도가 낮다.
*   **Redis**: 단순한 Key-Value 형태의 데이터 캐싱에 적합하며, 다양한 데이터 구조를 지원하고 성능이 뛰어나다. 또한, Spring Data Redis를 통해 Spring Framework와 쉽게 통합할 수 있다.
*   **Hazelcast**: 분산 캐싱 및 데이터 그리드 플랫폼으로, 클러스터링 환경에서 높은 성능과 확장성을 제공한다.
*   **Ehcache**: Java 기반의 경량 캐시 라이브러리로, 설정이 간단하고 사용하기 쉽다.
#### Redis, Hazelcast, Ehcache 비교

| 기능      | Redis                                            | Hazelcast                                     | Ehcache          |
| ------- | ------------------------------------------------ | --------------------------------------------- | ---------------- |
| 데이터 구조  | Key-Value, String, List, Set, Hash 등 다양한 자료구조 지원 | Key-Value, Map, Queue, List, Set 등 분산 자료구조 지원 | Key-Value        |
| 확장성     | Scale-out 용이                                     | 클러스터링을 통한 Scale-out                           | Scale-up         |
| 분산 환경   | Master-Slave, Redis Cluster                      | 클러스터링 지원                                      | 분산 환경 지원 미흡      |
| 트랜잭션 지원 | 지원                                               | 지원                                            | 지원               |
| 사용 사례   | 세션 관리, 캐싱, Pub/Sub, 실시간 분석                       | 분산 캐싱, 분산 데이터 그리드, 인메모리 데이터베이스                | 로컬 캐싱, 2차 캐시     |
| 특징      | In-Memory Data Structure Store, 다양한 기능 제공        | 분산 환경에 최적화, In-Memory Data Grid               | Java 기반, 설정 간편   |
| 사용 시점   | 높은 성능과 다양한 기능이 필요할 때                             | 분산 환경에서 데이터 공유 및 관리가 필요할 때                    | 간단한 로컬 캐싱이 필요할 때 |
#### Redis 예시
1.  **의존성 추가**: Spring Boot 프로젝트에 Redis 의존성을 추가해야 한다.
```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-cache")
    implementation("org.springframework.boot:spring-boot-starter-data-redis") // Redis
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
2.  **설정 추가**: Spring Boot 설정 파일 (`application.yml` 또는 `application.properties`)에 Redis 설정을 추가한다.
```yaml title="application.yml"
spring:
  redis:
    host: localhost
    port: 6379
```
3.  **캐시 어노테이션 사용**: `@Cacheable`, `@CachePut`, `@CacheEvict` 어노테이션을 사용하여 캐싱을 적용한다.
```java
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Cacheable(value = "users", key = "#id")
    public User getUser(Long id) {
        System.out.println("Fetching user from database");
        return userRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("User not found"));
    }
}
```
#### Hazelcast 예시
1.  **의존성 추가**: Spring Boot 프로젝트에 Hazelcast 의존성을 추가해야 한다.
```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-cache")
    implementation("com.hazelcast:hazelcast") // Hazelcast
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
2.  **설정 추가**: Hazelcast 설정 파일 (`hazelcast.xml`)을 생성하고, Spring Boot 설정 파일 (`application.yml` 또는 `application.properties`)에 Hazelcast 설정을 추가한다.
```xml title="hazelcast.xml"
<hazelcast xmlns="http://www.hazelcast.com/schema/config"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://www.hazelcast.com/schema/config
           http://www.hazelcast.com/schema/config/hazelcast-config-4.0.xsd">
    <instance-name>my-hazelcast-instance</instance-name>
    <network>
        <port auto-increment="true">5701</port>
        <join>
            <multicast enabled="false"/>
            <tcp-ip enabled="true">
                <member>127.0.0.1:5701</member>
            </tcp-ip>
        </join>
    </network>
    <map name="users">
        <time-to-live-seconds>300</time-to-live-seconds>
        <eviction policy="LRU" max-size-policy="PER_NODE" size="10000"/>
    </map>
</hazelcast>
```

```yaml title="application.yml"
spring:
  cache:
    cache-names: users
    hazelcast:
      config: classpath:hazelcast.xml
```
3.  **캐시 어노테이션 사용**: `@Cacheable`, `@CachePut`, `@CacheEvict` 어노테이션을 사용하여 캐싱을 적용한다.
```java
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Cacheable(value = "users", key = "#id")
    public User getUser(Long id) {
        System.out.println("Fetching user from database");
        return userRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("User not found"));
    }
}
```
#### Ehcache 예시
```kotlin title="build.gradle.kts"
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-cache")
    implementation("org.ehcache:ehcache") // Ehcache
    // implementation("org.springframework.boot:spring-boot-starter-data-redis") // Redis
    // implementation("com.hazelcast:hazelcast") // Hazelcast
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```
2.  **설정 추가**: Spring Boot 설정 파일 (`application.yml` 또는 `application.properties`)에 캐시 설정을 추가한다.
```yaml title="application.yml"
spring:
  cache:
    ehcache:
      config: classpath:ehcache.xml
```
3.  **캐시 어노테이션 사용**: `@Cacheable`, `@CachePut`, `@CacheEvict` 어노테이션을 사용하여 캐싱을 적용한다.
```java
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @Cacheable(value = "users", key = "#id")
    public User getUser(Long id) {
        System.out.println("Fetching user from database");
        return userRepository.findById(id).orElseThrow(() -> new IllegalArgumentException("User not found"));
    }
}
```
### Spring Cache Abstraction 어노테이션

| 어노테이션   | 설명                                                                                                                                                                                                                                                            |
|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| @Cacheable | 메서드의 결과를 캐시에 저장하고, 캐시에 저장된 값이 있으면 메서드를 실행하지 않고 캐시에서 값을 반환한다.                                                                                                                                                                                            |
| @CachePut  | 메서드의 결과를 캐시에 저장한다. `@Cacheable`과 달리 메서드를 항상 실행하고, 결과를 캐시에 저장한다.                                                                                                                                                                                              |
| @CacheEvict | 캐시에서 데이터를 삭제한다. `key` 속성을 사용하여 특정 키의 데이터를 삭제하거나, `allEntries = true` 속성을 사용하여 캐시 전체를 삭제할 수 있다.                                                                                                                                                                                             |
| @Caching   | 여러 개의 캐시 어노테이션을 함께 사용해야 할 때 사용한다. 예를 들어, `@CacheEvict`와 `@CachePut`을 함께 사용하여 캐시에서 데이터를 삭제하고, 새로운 데이터를 캐시에 저장할 수 있다.                                                                                                                                                                           |
### 사용 시 주의사항
*   **캐시 크기 설정**: 캐시 크기를 적절하게 설정해야 한다. 캐시 크기가 너무 작으면 캐시 효율이 떨어지고, 캐시 크기가 너무 크면 메모리 사용량이 증가할 수 있다.
*   **캐시 만료 시간 설정**: 캐시 만료 시간을 적절하게 설정해야 한다. 캐시 만료 시간이 너무 짧으면 데이터베이스 접근 횟수가 증가하고, 캐시 만료 시간이 너무 길면 데이터의 일관성이 깨질 수 있다.
*   **캐시 전략 선택**: 캐시 전략 (LRU, FIFO 등)을 적절하게 선택해야 한다. 캐시 전략은 캐시에서 데이터를 삭제할 때 어떤 데이터를 먼저 삭제할지 결정하는 알고리즘이다.
*   **데이터 일관성**: 캐시에 저장된 데이터와 데이터베이스의 데이터가 일치하도록 유지해야 한다. 데이터 변경 시 캐시를 갱신하거나, 캐시 만료 시간을 적절하게 설정하여 데이터 일관성을 유지해야 한다.

DB Caching은 데이터베이스 접근 횟수를 줄여 성능을 향상시키는 효과적인 기술이다. Java Spring에서는 JPA 1차 캐시, JPA 2차 캐시, Spring Cache Abstraction 등 다양한 방법으로 DB Caching을 구현할 수 있다. 프로젝트의 요구사항과 상황에 맞는 적절한 캐싱 전략을 선택하여 성능을 최적화해야 한다.

# Reference
[Spring Cache Abstraction](https://docs.spring.io/spring-framework/reference/integration/cache.html)
[Ehcache](http://www.ehcache.org/)