---
id: JPA Statement Logging
started: 2025-05-16
tags:
  - ✅DONE
group:
  - "[[Java Spring JPA]]"
---
# JPA Statement Logging
## DataSource Proxy란?
DataSource Proxy는 실제 DataSource를 감싸는 프록시 객체로, 데이터베이스 쿼리 실행 시 다양한 부가 기능을 제공할 수 있다. 쿼리 실행 시간 측정, 쿼리 로깅, Statement 갯수 검증 등 테스트 환경에서 유용하게 사용할 수 있다.
### DataSource Proxy는 왜 사용할까?
JPA 기반 애플리케이션을 테스트할 때, 실제 데이터베이스에 접근하는 쿼리를 로깅하고 검증하는 것은 매우 중요하다. DataSource Proxy를 사용하면 다음과 같은 장점이 있다.
- **쿼리 로깅**: 실행되는 모든 쿼리를 로깅하여 쿼리 성능 분석 및 디버깅에 활용할 수 있다.
- **Statement 갯수 검증**: 예상되는 Statement 갯수를 검증하여 N+1 문제와 같은 성능 문제를 사전에 발견할 수 있다.
- **테스트 격리**: 실제 데이터베이스 대신 메모리 데이터베이스를 사용하여 테스트를 격리할 수 있다.
### DataSource Proxy 종류
- **Log4jdbc**: JDBC 드라이버를 래핑하여 쿼리를 로깅하는 방식이다. 설정이 간단하지만, 모든 JDBC 드라이버를 지원하지 않을 수 있다.
- **Datasource-proxy**: DataSource를 래핑하여 쿼리를 로깅하고, Statement 갯수를 검증하는 기능을 제공한다. Spring Boot와 통합이 용이하며, 다양한 기능을 제공한다.
## Spring Boot에서 Datasource-proxy를 이용한 쿼리 로깅 및 Statement 갯수 테스트
### 1. 의존성 추가
Spring Boot 프로젝트에 `datasource-proxy` 의존성을 추가한다.
```kotlin title="build.gradle"
dependencies {
    testImplementation 'net.ttddyy.datasource-proxy:datasource-proxy-spring-boot-starter:1.8.2'
}
```
### 2. 설정 추가
`application.properties` 또는 `application.yml` 파일에 다음 설정을 추가한다.

```css title="application.properties"
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# Datasource Proxy 설정
spring.datasource.proxy.enabled=true
spring.datasource.proxy.data-source-proxy-name=testDataSourceProxy
spring.datasource.proxy.listener.query.enable-logging=true
```
- `spring.datasource.url`: 테스트에 사용할 H2 메모리 데이터베이스 URL을 설정한다.
- `spring.datasource.driver-class-name`: H2 드라이버 클래스 이름을 설정한다.
- `spring.datasource.username`: 데이터베이스 사용자 이름을 설정한다.
- `spring.datasource.password`: 데이터베이스 비밀번호를 설정한다.
- `spring.datasource.proxy.enabled`: DataSource Proxy를 활성화한다.
- `spring.datasource.proxy.data-source-proxy-name`: DataSource Proxy 이름을 설정한다.
- `spring.datasource.proxy.listener.query.enable-logging`: 쿼리 로깅을 활성화한다.
### 3. 테스트 코드 작성
```java title="UserRepositoryTest.java"
import lombok.extern.slf4j.Slf4j;
import net.ttddyy.dsproxy.QueryCountHolder;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Slf4j
public class UserRepositoryTest {

    @Autowired
    private UserRepository userRepository;

    @AfterEach
    void tearDown() {
        QueryCountHolder.clear(); // Statement 갯수 초기화
    }

    @Test
    @Transactional
    void NPlusOneTest() {
        //given
        User user1 = new User("user1");
        User user2 = new User("user2");

        userRepository.save(user1);
        userRepository.save(user2);

        //when
        userRepository.findAll().forEach(user -> {
            log.info("user : " + user.getName());
            user.getOrders().forEach(order -> {
                log.info("order : " + order.getName());
            });
        });

        //then
        assertThat(QueryCountHolder.getGrandTotal()).isEqualTo(3); // 쿼리 3번 실행되어야 함
    }
}
```
- `@SpringBootTest`: Spring Boot 테스트 환경을 설정한다.
- `@Autowired`: UserRepository를 주입받는다.
- `@AfterEach`: 각 테스트 메서드 실행 후에 QueryCountHolder를 초기화한다.
- `QueryCountHolder.getGrandTotal()`: 총 실행된 Statement 갯수를 가져온다.
- `assertThat(QueryCountHolder.getGrandTotal()).isEqualTo(3)`: 실행된 Statement 갯수가 3개인지 검증한다.
- `@Transactional`: 트랜잭션 안에서 쿼리가 실행되도록 설정한다.
### 4. 결과 확인
테스트를 실행하면 다음과 같은 로그를 확인할 수 있다.
```log
[INFO] - user : user1
[INFO] - order : order1
[INFO] - user : user2
[INFO] - order : order2
```
또한, `QueryCountHolder.getGrandTotal()`을 통해 실행된 Statement 갯수를 확인할 수 있다.
## Log4jdbc를 이용한 쿼리 로깅
### 1. 의존성 추가
```gradle title="build.gradle"
dependencies {
    implementation 'org.bgee.log4jdbc-log4j2:log4jdbc-log4j2-jdbc4.1:1.16'
}
```
### 2. DataSource 설정 변경
```java
spring.datasource.url=jdbc:log4jdbc:h2:mem:testdb
spring.datasource.driver-class-name=net.sf.log4jdbc.sql.jdbcapi.DriverSpy
```
### 3. Log 설정
```xml title="log4jdbc.log4j2.properties"
log4jdbc.spylog.include=T,C,R,Q
log4jdbc.sqltiming.warn.threshold=0
log4jdbc.dump.sql.maxlinelength=0
log4jdbc.statement.warn=true
log4jdbc.auto.load.popular.drivers=false
log4jdbc.log4j2.properties.file=classpath:log4j2.xml
```
### Log4jdbc 설정 설명
- `log4jdbc.spylog.include=T,C,R,Q`
    *   T : Date & Time
    *   C : Connection ID
    *   R : Result
    *   Q : SQL
- `log4jdbc.sqltiming.warn.threshold=0`
    *   쿼리 수행 시간이 지정된 Threshold를 넘기면 경고 발생
- `log4jdbc.dump.sql.maxlinelength=0`
    *   SQL을 한 줄로 표시
- `log4jdbc.statement.warn=true`
    *   Statement를 실행할 때마다 Warn 레벨로 로그를 남김
- `log4jdbc.auto.load.popular.drivers=false`
    *   기본 드라이버 로딩 비활성화
- `log4jdbc.log4j2.properties.file=classpath:log4j2.xml`
    *   Log4jdbc 설정을 Log4j2 설정과 연결
## 사용 시 주의사항
- DataSource Proxy는 테스트 환경에서만 사용해야 한다. 운영 환경에서는 DataSource Proxy를 사용하지 않도록 설정해야 한다.
- Statement 갯수 검증은 예상되는 쿼리 갯수를 정확하게 파악하고 있어야 한다.
- Log4jdbc를 사용할 경우, JDBC 드라이버를 래핑하므로 성능에 영향을 줄 수 있다.

DataSource Proxy를 사용하면 JPA 기반 애플리케이션의 테스트를 더욱 효과적으로 수행할 수 있다. 쿼리 로깅 및 Statement 갯수 검증을 통해 성능 문제를 사전에 발견하고, 애플리케이션의 안정성을 높일 수 있다.

# Reference
[Datasource-proxy](https://github.com/gavlyukovskiy/datasource-proxy)
[Log4jdbc](https://github.com/simonxsl/log4jdbc-log4j2)