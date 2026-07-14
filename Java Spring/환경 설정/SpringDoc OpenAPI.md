---
id: SpringDoc OpenAPI
started: 2026-06-09
tags:
  - ✅DONE
  - Java-Spring
  - API
  - Documentation
group:
  - "[[Java Spring]]"
---
# SpringDoc OpenAPI: 실행 코드에서 API 계약 생성하기

## 1. 개요 (Overview)
**OpenAPI**는 HTTP API의 경로, 입력, 출력, 오류와 인증 방식을 기계가 읽을 수 있는 명세로 표현합니다. **SpringDoc**은 Spring MVC Controller와 어노테이션을 분석해 OpenAPI 문서를 생성하고 Swagger UI를 제공합니다.

API 문서는 설명 자료가 아니라 클라이언트 생성, 계약 검증, 테스트와 협업의 기준이 되는 **실행 가능한 계약**입니다.

---

## 2. 기본 구성

```gradle
implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui")
```

```yaml
springdoc:
  api-docs:
    enabled: true
  swagger-ui:
    enabled: true
    path: /swagger
```

운영 환경에서 Swagger UI를 외부에 노출할지는 보안 정책에 따라 결정합니다. 명세 Endpoint와 UI의 활성화 정책을 분리할 수 있습니다.

---

## 3. Controller 계약

```java
@Operation(summary = "회원 조회")
@ApiResponses({
    @ApiResponse(responseCode = "200", description = "조회 성공"),
    @ApiResponse(responseCode = "404", description = "회원 없음")
})
@GetMapping("/api/v3/members/{memberId}")
public ResponseEntity<MemberResponse> getMember(
        @Parameter(description = "회원 ID") @PathVariable Long memberId
) {
    return ResponseEntity.ok(MemberResponse.from(getMemberUseCase.get(memberId)));
}
```

다음 요소를 문서화해야 합니다.

- 요청 필드 제약조건과 예제
- 성공 응답뿐 아니라 업무 오류·검증 오류·인증 오류
- Pagination과 Sorting 규칙
- 인증 Scheme과 필요한 Scope
- Deprecated API와 대체 경로

---

## 4. 실무 사례 적용 관점
이 사례는 핵심 업무 애플리케이션, `metrics`에서 공통 SpringDoc 플러그인을 사용하고, Controller·Request·Response에 OpenAPI 어노테이션을 적용합니다. Gateway는 애플리케이션과 Metrics의 API Docs 경로를 각각 라우팅합니다.

```text
Swagger UI / API Client
  -> Gateway
      ├─ /app/v3/api-docs     -> core application
      └─ /metrics/v3/api-docs -> metrics
```

서비스별 명세를 합칠 때 경로 충돌, 동일 Schema 이름, 인증 설정 차이를 확인해야 합니다.

---

## 5. 계약 품질 관리
- 공통 Error Response Schema를 정의합니다.
- Controller Test에서 OpenAPI와 실제 Status·Body의 불일치를 검증합니다.
- 명세 JSON을 CI Artifact로 보관하면 버전 간 Breaking Change를 비교할 수 있습니다.
- Domain Model이나 JPA Entity를 응답 Schema로 직접 노출하지 않습니다.
- 내부 관리 Endpoint와 외부 공개 Endpoint를 Group으로 분리합니다.

---

## 6. Schema 설계
Response Schema는 Java Class 구조를 그대로 노출하기보다 API 계약을 표현해야 합니다.

```java
@Schema(description = "회원 응답")
public record MemberResponse(
        @Schema(example = "100") Long id,
        @Schema(example = "ACTIVE") MemberStatus status
) {
}
```

`oneOf`, `allOf`, Nullable, Enum과 Format을 Client Generator가 어떻게 처리하는지 확인합니다. 상속 구조를 과도하게 쓰면 생성 Client가 복잡해집니다.

## 7. 공통 오류 계약

```json
{
  "code": "MEMBER_NOT_FOUND",
  "message": "회원을 찾을 수 없습니다.",
  "traceId": "...",
  "fieldErrors": []
}
```

HTTP Status와 업무 오류 Code의 관계를 문서화합니다. 실제 Controller Advice가 만드는 Response와 문서용 Example이 달라지지 않게 공통 Type을 재사용합니다.

## 8. Security Scheme

```java
@SecurityScheme(
        name = "bearerAuth",
        type = SecuritySchemeType.HTTP,
        scheme = "bearer",
        bearerFormat = "JWT"
)
```

인증이 필요 없는 Endpoint와 필요한 Role·Scope를 구분합니다. Swagger UI의 인증 편의 기능이 운영 Token 노출로 이어지지 않게 환경별 공개 정책을 둡니다.

## 9. Grouped OpenAPI
관리자, Mobile, 내부 API를 Group으로 분리하면 탐색과 공개 정책을 달리할 수 있습니다.

```java
@Bean
GroupedOpenApi adminApi() {
    return GroupedOpenApi.builder()
            .group("admin-v3")
            .pathsToMatch("/api/v3/admin/**")
            .build();
}
```

## 10. Gateway 뒤의 Server URL
Backend가 내부 Host를 기준으로 명세를 생성하면 Swagger UI 요청이 잘못된 주소로 갈 수 있습니다. Forwarded Header 신뢰 설정과 OpenAPI `servers`를 환경에 맞게 구성합니다.

Path Prefix를 Gateway가 제거하는 경우 문서 URL과 실제 외부 URL의 차이를 검증합니다.

## 11. Breaking Change
- Path·Method 삭제
- 필수 Request Field 추가
- Response Field 삭제·타입 변경
- Enum 값 제거
- Status Code 의미 변경

CI에서 이전 OpenAPI Artifact와 새 명세를 Diff하고 Breaking Change를 Release 정책에 연결합니다.

## 12. Code Generation
OpenAPI Generator로 Client를 만들 수 있지만 생성 코드 품질과 Version 호환성을 확인해야 합니다. 명세가 부정확하면 오류도 자동 생성됩니다.

Generated Client를 Consumer Contract Test에 사용하면 문서가 실제 호출 가능한지 검증할 수 있습니다.

## 13. 문서와 실제 동작 검증
- MockMvc Test에서 Status·Schema 확인
- Bean Validation과 Required 표시 일치
- Global Error Handler의 모든 오류 문서화
- Pagination·Sort Parameter 확인
- Gateway를 통한 `/v3/api-docs`와 Swagger UI Smoke Test

## 14. 운영 보안
OpenAPI JSON에는 내부 Endpoint, Model 이름과 오류 정보가 포함될 수 있습니다. 외부 공개 대상과 사내 대상 명세를 분리하고, Actuator·Internal Admin API가 포함되지 않는지 확인합니다.

---

## 15. 실무 사례 적용 진단과 개선 과제

Controller DTO에 `@Schema`와 응답 예제가 적용돼 있으나 대규모 API에서 Error Schema, 인증 요구, Pagination과 Nullability가 누락되기 쉽습니다. 문서 생성 성공만으로 실제 응답과 일치한다고 보장할 수 없습니다.

공통 Error·Page Schema와 Security Scheme를 재사용하고, OpenAPI Snapshot Diff를 CI에 넣어 Breaking Change를 분류합니다. Example에 실제 비밀번호나 Token처럼 오해할 값을 피하고 운영 Swagger UI는 인증·Network 제한을 둡니다.

완료 기준은 모든 Public Operation에 성공·오류 응답과 권한이 명시되고, 생성 Client 또는 Schema Validator로 대표 응답을 검증하며, 호환성 파괴 변경이 승인 없이 Merge되지 않는 상태입니다.

---

# Reference
- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [SpringDoc OpenAPI](https://springdoc.org/)
