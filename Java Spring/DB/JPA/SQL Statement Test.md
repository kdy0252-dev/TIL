---
id: SQL StatementTest
started: 2025-05-16
tags:
  - ✅DONE
group:
  - "[[Java Spring JPA]]"
---
# SQL StatementTest
## DataSource Proxy
> [!Warning] 주의사항
> 실 운영 환경에서 DataSource Proxy를 사용하면 성능 저하 문제가 발생하기때문에 사용을 지양한다. 

```kotlin title="build.gradle.kts"
testImplementation("net.ttddyy:datasource-proxy:1.8")
testImplementation("net.ttddyy:datasource-proxy-spring-boot-starter:1.8")
```

```yaml title="application.yml"
spring:
  datasource:
    proxy:
      enabled: true
      query:
        log-level: DEBUG
```

## QueryCountHolder를 사용한 Test 작성
```java title="QueryCountHolder로 SQL Statement 검증"
import net.ttddyy.dsproxy.QueryCount;
import net.ttddyy.dsproxy.QueryCountHolder;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;

@DataJpaTest
class UserRepositoryTest {

    @Autowired
    UserRepository userRepository;

    @BeforeEach
    void clearQueryCount() {
        QueryCountHolder.clear();
    }

    @Test
    void testJpaRepositoryQueryCount() {
        userRepository.findAll();  // 예: 1개의 SELECT 쿼리 발생 예상

        QueryCount count = QueryCountHolder.getGrandTotal();

        System.out.println("SELECT count: " + count.getSelect());
        System.out.println("INSERT count: " + count.getInsert());
        System.out.println("UPDATE count: " + count.getUpdate());
        System.out.println("DELETE count: " + count.getDelete());
        System.out.println("Total queries: " + count.getTotal());

        Assertions.assertEquals(1, count.getSelect()); // 예상 쿼리 수 검증
    }
}
```

> [!Warning] 주의사항
> - `@Transactional`을 테스트에 붙이면 **1차 캐시**에 의해 쿼리 수가 줄어들 수 있다.
> - `fetch join`을 했는지 안 했는지 검증하는 데 유용하다.
> - `@DataJpaTest`는 기본적으로 트랜잭션을 감싸므로, 쿼리 수 측정 시 주의.
> - `QueryCountHolder.getGrandTotal()`은 전체 쿼리 수를 반환한다.
> - 테스트 간 **쿼리 count가 누적될 수 있으므로**, 반드시 `@BeforeEach`에서 `QueryCountHolder.clear()` 해줘야 정확한 측정이 된다.
> - 테스트 DB가 H2인 경우 **Hibernate가 메타데이터 확인을 위해 추가 쿼리**를 날릴 수 있으므로, **주의가 필요**하다.

# Reference
[GPT 히스토리](https://chatgpt.com/share/6827448e-3718-800a-9b35-765254339f7e)
[GPT 히스토리](https://chatgpt.com/c/682744fd-75c8-800a-939f-bd4e519a32a2)