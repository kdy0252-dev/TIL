---
id: SQL StatementTest
started: 2025-05-16
tags:
  - ✅DONE
group:
  - "[[Java Spring JPA]]"
---
# JPA가 실행한 SQL 개수를 테스트하는 방법

JPA Repository Method가 올바른 결과를 반환해도 성능 문제가 숨어 있을 수 있다. 회원 100명을 조회한 뒤 각 회원의 주문을 Lazy Loading하면 처음 회원 조회 1회와 주문 조회 100회가 실행된다. 기능 테스트는 통과하지만 데이터가 많아질수록 느려지는 전형적인 N+1 문제다.

SQL 개수 테스트는 “이 Method가 몇 번 Database와 통신해야 하는가”를 실행 가능한 규칙으로 남긴다. 실행 계획과 응답 시간을 대신하지는 않지만, Fetch 전략이 바뀌어 Query가 갑자기 늘어나는 회귀를 빠르게 잡는 데 효과적이다.

## 무엇을 세는가?

SQL Statement는 크게 다음 유형으로 나눌 수 있다.

- `SELECT`: 조회와 Lazy Loading
- `INSERT`: 새 Entity 저장
- `UPDATE`: Dirty Checking과 명시적 수정
- `DELETE`: 삭제와 Cascade

Query 수가 적다고 항상 빠른 것은 아니다. 거대한 Join 한 번이 작은 Query 두 번보다 느릴 수도 있다. 따라서 개수 테스트는 다음 질문에 답할 때 사용한다.

- 예상하지 못한 N+1 Query가 생겼는가?
- Batch Insert/Update가 실제로 묶이는가?
- 불필요한 중복 조회가 추가되었는가?
- 읽기 Use Case에서 쓰기 Query가 발생하는가?

## DataSource Proxy의 동작 원리

`datasource-proxy`는 Application과 실제 JDBC `DataSource` 사이에 Proxy를 둔다. JPA와 Hibernate가 최종적으로 JDBC Statement를 실행할 때 이를 관찰하여 SQL, Parameter, 실행 시간과 Query 유형을 기록한다.

```text
Repository → JPA/Hibernate → Proxy DataSource → 실제 DataSource → Database
                              └─ Query Count 기록
```

JPA API 호출 횟수가 아니라 실제 JDBC 경계에서 세기 때문에 Lazy Loading으로 나중에 실행된 Query도 확인할 수 있다. 반면 Database 내부 Trigger가 추가로 실행하는 SQL처럼 JDBC 밖에서 일어나는 작업은 이 Count에 나타나지 않는다.

> [!Warning] 적용 범위
> 모든 SQL과 Parameter를 기록하면 Logging, 문자열 조립과 Listener 실행 비용이 생긴다. Query 개수 검증용 Proxy와 상세 Logging은 Test Profile에서만 활성화하는 편이 안전하다. 운영에서는 필요성과 Overhead를 측정하고 제한적으로 사용한다.

## Test Dependency와 설정

Version은 Project의 Spring Boot Version과 Starter 호환성을 확인해 고정한다. 아래 값은 구조를 보여 주는 예시이며 최신 Version을 의미하지 않는다.

```kotlin title="build.gradle.kts"
testImplementation("net.ttddyy:datasource-proxy:1.8")
testImplementation("net.ttddyy:datasource-proxy-spring-boot-starter:1.8")
```

```yaml title="application-test.yml"
spring:
  datasource:
    proxy:
      enabled: true
      query:
        log-level: DEBUG
```

실제 Starter에 따라 Property Prefix가 다를 수 있다. Dependency를 추가한 뒤 Test Log나 Spring Context에서 원본 DataSource가 Proxy로 감싸졌는지 먼저 확인한다.

## QueryCountHolder로 개수 검증하기

다음 예시는 회원과 주문을 한 번의 Fetch Join으로 조회한다는 계약을 검증한다. 핵심은 **Count 초기화 → 테스트 데이터 준비 결과 제거 → 대상 Method 실행 → 필요한 연관 관계 접근 → Count 검증** 순서다.

```java title="QueryCountHolder로 SQL Statement 검증"
import net.ttddyy.dsproxy.QueryCount;
import net.ttddyy.dsproxy.QueryCountHolder;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
class UserRepositoryTest {

    @Autowired
    UserRepository userRepository;

    @BeforeEach
    void clearQueryCount() {
        QueryCountHolder.clear();
    }

    @Test
    void findAllWithOrders_executesOneSelect() {
        QueryCountHolder.clear();

        var users = userRepository.findAllWithOrders();
        users.forEach(user -> user.getOrders().size());

        QueryCount count = QueryCountHolder.getGrandTotal();

        assertThat(count.getSelect()).isEqualTo(1);
        assertThat(count.getInsert()).isZero();
        assertThat(count.getUpdate()).isZero();
        assertThat(count.getDelete()).isZero();
    }
}
```

연관 관계를 실제로 접근하는 줄이 중요하다. Lazy Collection을 전혀 읽지 않으면 N+1을 일으킬 Query가 실행되지 않아 잘못 통과할 수 있다.

## Flush와 Clear로 1차 Cache의 착시 제거하기

`@DataJpaTest`는 기본적으로 각 Test를 Transaction으로 실행한다. 같은 Transaction에서 저장한 Entity를 다시 조회하면 Persistence Context의 1차 Cache가 반환하여 기대한 `SELECT`가 실행되지 않을 수 있다.

```java
@Autowired
EntityManager entityManager;

private void flushAndClear() {
    entityManager.flush();
    entityManager.clear();
    QueryCountHolder.clear();
}
```

Test Fixture를 저장한 뒤 `flush()`로 SQL을 실행하고 `clear()`로 관리 중인 Entity를 분리한다. 그 다음 Query Count를 다시 초기화하면 준비 단계의 `INSERT`와 검증 대상의 SQL이 섞이지 않는다.

```java
userRepository.save(userWithOrders());
flushAndClear();

var result = userRepository.findAllWithOrders();
result.forEach(user -> user.getOrders().size());

assertThat(QueryCountHolder.getGrandTotal().getSelect()).isEqualTo(1);
```

## 정확한 테스트를 방해하는 요소

### Test 간 Count 누적

`QueryCountHolder`는 현재 실행 Context에 Count를 보관한다. 각 Test 시작 전 초기화하고, Fixture 준비 뒤에도 한 번 더 초기화해야 대상 동작만 측정할 수 있다. 병렬 Test를 사용한다면 Holder의 Thread 처리 방식과 비동기 Query가 같은 Context에 집계되는지도 확인한다.

### 자동 Flush

JPA는 Query를 실행하기 전에 변경 내용과 조회 결과가 충돌할 수 있다고 판단하면 자동으로 Flush한다. 조회만 검증한다고 생각했는데 `INSERT`나 `UPDATE`가 포함된다면 준비 단계와 대상 단계가 분리되었는지 확인한다.

### Batch Statement

JDBC Batch는 여러 Row를 한 번의 Batch 실행으로 보낼 수 있지만, “Entity 수”, “SQL 문자열 수”, “JDBC Batch 수”는 같은 값이 아니다. `getInsert()` 숫자 하나만 보고 Network Round Trip이 줄었다고 단정하지 말고 Proxy의 Batch 정보와 Hibernate Batch Log도 함께 본다.

### H2와 운영 Database의 차이

H2는 빠른 Repository Test에 유용하지만 Dialect, 실행 계획, Lock과 일부 SQL 문법이 운영 Database와 다르다. Query 개수 계약은 H2에서 확인할 수 있어도 실제 Index 사용과 성능은 PostgreSQL이나 MySQL Testcontainer 같은 운영 계열 Database에서 검증해야 한다.

### Open Session in View

Web Integration Test에서 OSIV가 켜져 있으면 Controller 이후 JSON 직렬화 시점에 Lazy Loading Query가 실행될 수 있다. Repository Method 직후 Count를 읽으면 이 Query를 놓친다. SQL 경계를 어디까지 볼 것인지 정하고, API 전체 성능을 검증할 때는 Response 직렬화가 끝난 뒤 측정한다.

## 좋은 Query 개수 테스트의 기준

Query 개수는 구현 세부 사항이므로 모든 Repository에 무조건 고정하면 정상적인 최적화도 Test를 깨뜨린다. 다음과 같이 성능상 의미가 있는 경계에 집중한다.

- 목록 크기에 비례해 Query가 증가하면 안 되는 Use Case
- 대량 처리에서 Batch가 반드시 필요한 경로
- 과거에 N+1 회귀가 발생했던 경로
- 호출 빈도와 데이터 규모가 큰 핵심 조회

Test 이름에는 기대하는 성능 계약을 드러낸다.

```text
findAllWithOrders_executesOneSelect
saveAll_executesInJdbcBatches
loadDashboard_doesNotQueryPerMember
```

마지막으로 Query 수, 실행 시간, 실행 계획은 서로 다른 문제를 본다는 점을 기억한다. Query Count Test로 구조적 회귀를 막고, 운영 계열 Database의 `EXPLAIN`, Integration Test와 부하 테스트로 실제 성능을 확인해야 한다.

# Reference
[datasource-proxy User Guide](https://jdbc-observations.github.io/datasource-proxy/docs/current/user-guide/)
[Spring Framework - Testing](https://docs.spring.io/spring-framework/reference/testing.html)
