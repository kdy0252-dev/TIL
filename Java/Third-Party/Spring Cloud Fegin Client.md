---
id: Spring Cloud Fegin Client
started: 2025-05-08
tags:
  - ✅DONE
group:
  - "[[Java Third-Party]]"
---
# Spring Cloud Feign Client
## Feign Client란 무엇인가?
Feign Client는 Netflix에서 개발한 선언적 HTTP 클라이언트로, RESTful API를 더 쉽고 간단하게 호출할 수 있도록 해줍니다. Spring Cloud는 Feign을 통합하여 Spring Boot 애플리케이션에서 Feign을 쉽게 사용할 수 있도록 지원합니다. Feign을 사용하면 인터페이스를 정의하고 어노테이션을 통해 HTTP 요청을 설정할 수 있습니다.
### Feign의 장점
- 간결한 코드: HTTP 클라이언트 코드를 직접 작성할 필요 없이 인터페이스를 통해 API를 호출할 수 있습니다.
- 선언적 방식: 어노테이션을 사용하여 HTTP 요청을 정의하므로 코드가 더 읽기 쉽고 유지보수하기 쉽습니다.
- Spring Cloud 통합: Spring Cloud 생태계와 잘 통합되어 있어 Spring Boot 애플리케이션에서 쉽게 사용할 수 있습니다.
## Feign Client 설정 방법
### 의존성 추가 (Kotlin DSL)
build.gradle.kts 파일에 다음 의존성을 추가합니다.
```kotlin
dependencies {
    implementation("org.springframework.cloud:spring-cloud-starter-openfeign")
}

dependencyManagement {
    imports {
        mavenBom("org.springframework.cloud:spring-cloud-dependencies:${property("springCloudVersion")}")
    }
}
```
### Spring Boot 설정 (application.yml)
application.yml 파일에 다음 설정을 추가합니다.
```yaml
spring:
  application:
    name: your-application-name
  cloud:
    openfeign:
      enabled: true
```
### Feign Client 인터페이스 정의
API를 호출할 인터페이스를 정의합니다. `@FeignClient` 어노테이션을 사용하여 Feign Client를 설정하고, `@GetMapping`, `@PostMapping` 등의 어노테이션을 사용하여 HTTP 요청을 정의합니다.

```kotlin
import org.springframework.cloud.openfeign.FeignClient
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable

@FeignClient(name = "user-api", url = "\${user.api.url}")
interface UserApiClient {

    @GetMapping("/users/{userId}")
    fun getUser(@PathVariable userId: Long): User
}
```
이 예제에서는 `UserApiClient` 인터페이스를 정의하고, `user-api`라는 이름으로 Feign Client를 설정했습니다. `url` 속성을 사용하여 API의 기본 URL을 설정하고, `@GetMapping` 어노테이션을 사용하여 `/users/{userId}` 엔드포인트를 호출하도록 설정했습니다.
### Feign Client 사용 방법
Spring Bean으로 등록된 Feign Client를 주입받아 사용합니다.

```kotlin
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

@Service
class UserService {

    @Autowired
    lateinit var userApiClient: UserApiClient

    fun getUser(userId: Long): User {
        return userApiClient.getUser(userId)
    }
}
```

이 예제에서는 `UserService` 클래스에서 `UserApiClient`를 주입받아 `getUser` 메서드를 통해 API를 호출합니다.
## Feign Client 예제
### User API Client
```kotlin
import org.springframework.cloud.openfeign.FeignClient
import org.springframework.web.bind.annotation.*

@FeignClient(name = "user-api", url = "\${user.api.url}")
interface UserApiClient {

    @GetMapping("/users/{userId}")
    fun getUser(@PathVariable userId: Long): User

    @PostMapping("/users")
    fun createUser(@RequestBody user: CreateUserRequest): User

    @PutMapping("/users/{userId}")
    fun updateUser(@PathVariable userId: Long, @RequestBody user: UpdateUserRequest): User

    @DeleteMapping("/users/{userId}")
    fun deleteUser(@PathVariable userId: Long)
}
```
이 예제에서는 `UserApiClient` 인터페이스를 정의하고, `getUser`, `createUser`, `updateUser`, `deleteUser` 메서드를 통해 다양한 HTTP 요청을 처리하도록 설정했습니다.
### User API DTO
```kotlin
data class User(
    val id: Long,
    val name: String,
    val email: String
)

data class CreateUserRequest(
    val name: String,
    val email: String
)

data class UpdateUserRequest(
    val name: String,
    val email: String
)
```
이 예제에서는 `User`, `CreateUserRequest`, `UpdateUserRequest` 데이터 클래스를 정의하여 API 요청 및 응답에 사용합니다.
### User Service
```kotlin
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Service

@Service
class UserService {

    @Autowired
    lateinit var userApiClient: UserApiClient

    fun getUser(userId: Long): User {
        return userApiClient.getUser(userId)
    }

    fun createUser(name: String, email: String): User {
        val createUserRequest = CreateUserRequest(name, email)
        return userApiClient.createUser(createUserRequest)
    }

    fun updateUser(userId: Long, name: String, email: String): User {
        val updateUserRequest = UpdateUserRequest(name, email)
        return userApiClient.updateUser(userId, updateUserRequest)
    }

    fun deleteUser(userId: Long) {
        userApiClient.deleteUser(userId)
    }
}
```
이 예제에서는 `UserService` 클래스에서 `UserApiClient`를 주입받아 API를 호출하고, 비즈니스 로직을 처리합니다.

이러한 방식으로 Feign Client를 사용하면 코드를 간결하게 유지하고, API 호출을 더 쉽게 관리할 수 있습니다.

# Reference