---
id: Spring Cloud Contract
started: 2025-09-27
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Contract

## 1. 개요 (Overview)
**Spring Cloud Contract**는 마이크로서비스 환경에서 **소비자 주도 계약(Consumer-Driven Contract, CDC)** 테스트를 구현하기 위한 프레임워크입니다.
서비스 간의 통신 약속(API 스펙)을 "계약(Contract)"이라는 코드로 정의하고, 이를 기반으로 **Provider(서버)** 와 **Consumer(클라이언트)** 양쪽에서 자동으로 테스트를 수행하여 호환성을 보장합니다.

MSA에서 흔히 발생하는 "Prod 환경에 배포했더니 API 스펙이 안 맞아서 죽는 문제"를 빌드 타임에 미리 잡아내는 것이 목표입니다.

---

## 2. CDC (Consumer-Driven Contracts) 개념

### 2.1 기존 통합 테스트의 문제점
- **E2E 테스트**: 실제 서버들을 모두 띄워야 하므로 느리고 비용이 비쌉니다. 깨지기도 쉽습니다(Flaky).
- **Mock 테스트**: Client가 Server를 Mocking해서 테스트하지만, 실제 Server가 변경되었을 때 Mock이 업데이트되지 않으면 테스트는 통과하지만 배포 시 장애가 발생합니다 (False Positive).

### 2.2 CDC 해결책
1.  **계약 정의**: API 요청/응답 형식을 Groovy나 YAML로 정의합니다.
2.  **Provider 검증**: 계약 파일로부터 자동으로 생성된 테스트가 Provider 코드에 대해 실행됩니다. 즉, 서버가 약속을 어기면 빌드가 실패합니다.
3.  **Consumer 검증**: Provider가 테스트에 성공하면 **Stub JAR**가 생성됩니다. Consumer는 이 Stub을 다운로드 받아 로컬에서 실제 서버처럼 띄워놓고 테스트합니다.

---

## 3. 작동 원리 (Workflow)

1.  **Contract 작성**: `src/test/resources/contracts`에 Groovy 파일 생성.
2.  **Provider 빌드**:
    - Maven/Gradle 플러그인이 계약 파일을 읽어 `Test` 클래스를 자동 생성 (`java-test-compile` 단계).
    - Provider의 Controller를 띄우고(MockMvc 또는 RestAssured MockMvc) 요청을 보내 응답이 계약과 일치하는지 확인.
    - 성공 시, WireMock 호환 JSON 스텁들이 포함된 `stubs-jar` 생성.
3.  **Consumer 테스트**:
    - `@AutoConfigureStubRunner`를 사용하여 Maven Repo(Local or Remote)에서 `stubs-jar`를 다운로드.
    - WireMock 서버를 랜덤 포트로 띄우고 스텁을 로딩.
    - Consumer는 `127.0.0.1:randomPort`로 요청을 보내 테스트 수행.

---

## 4. 구현 및 설정 예제

### 4.1 Provider (Server) 설정

**build.gradle**
```groovy
plugins {
    id 'org.springframework.cloud.contract' version '4.0.0'
}

contracts {
    baseClassForTests = 'com.example.provider.BaseTestClass' // 공통 테스트 부모 클래스
}
```

**BaseTestClass.java** (MockMvc 설정용)
```java
@SpringBootTest
public class BaseTestClass {
    @Autowired UserController userController;

    @BeforeEach
    public void setup() {
        RestAssuredMockMvc.standaloneSetup(userController);
    }
}
```

**Contract 정의 (shouldReturnUser.groovy)**
```groovy
import org.springframework.cloud.contract.spec.Contract

Contract.make {
    description "ID로 사용자 조회 성공 케이스"
    request {
        method GET()
        url "/users/1"
    }
    response {
        status OK()
        body([
            id: 1,
            name: "Dykim",
            role: "ADMIN"
        ])
        headers {
            contentType applicationJson()
        }
    }
}
```

### 4.2 Consumer (Client) 설정

**의존성**
```groovy
testImplementation 'org.springframework.cloud:spring-cloud-starter-contract-stub-runner'
```

**테스트 코드**
```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
@AutoConfigureStubRunner(
    ids = {"com.example:user-service:+:stubs:8080"}, // GroupId:ArtifactId:Version:Classifier:Port
    stubsMode = StubRunnerProperties.StubsMode.LOCAL
)
public class UserServiceConsumerTest {

    @Test
    public void testGetUser() {
        RestTemplate restTemplate = new RestTemplate();
        // Stub Runner가 8080 포트에 WireMock 서버 실행 중
        String result = restTemplate.getForObject("http://localhost:8080/users/1", String.class);
        
        assertThat(result).contains("Dykim");
    }
}
```

---

## 5. 고급 기능 및 운영 고려사항

### 5.1 Dynamic Fields (Regex)
계약에서 정확한 값 대신 패턴(Regex)을 사용할 수 있습니다.
- **Consumer 측**: "이메일 형식(aaa@bbb.com)이기만 하면 돼".
- **Provider 측**: "응답값이 꼭 'alice@test.com'일 필요는 없고 이메일 형식이면 통과".

```groovy
body([
    email: $(consumer(regex(email())), provider('alice@test.com')),
    timestamp: $(consumer(regex(iso8601WithOffset())), provider('2025-01-01T00:00:00Z'))
])
```

### 5.2 Stub Storage (Remote)
실무에서는 `stubsMode = REMOTE`로 설정하여 Nexus, Artifactory 같은 중앙 저장소나, **Spring Cloud Contract Verifier (Git)** 저장소에서 스텁을 가져옵니다. 이를 통해 팀 간에 최신 계약(Stub)을 공유할 수 있습니다.

### 5.3 Messaging (Event)
HTTP API뿐만 아니라, Kafka/RabbitMQ 메시지 발행에 대한 계약도 정의할 수 있습니다.
- "Provider가 `UserCreated` 이벤트를 발행하면 Consumer는 이런 JSON 포맷을 기대한다".

# Reference
- [Spring Cloud Contract Reference](https://docs.spring.io/spring-cloud-contract/docs/current/reference/html/)
- [Consumer Driven Contracts with Spring Cloud Contract](https://spring.io/guides/gs/contract-rest/)
- [WireMock](http://wiremock.org/)