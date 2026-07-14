---
id: Postman Newman WireMock 테스트 전략
started: 2026-06-07
tags:
  - ✅DONE
  - Testing
  - API
group:
  - "[[Java Spring]]"
---
# Postman, Newman, WireMock을 이용한 API 테스트 전략

## 1. 개요 (Overview)
API 시스템은 단위 테스트만으로 HTTP 계약, 인증, 서비스 간 흐름과 외부 API 장애를 충분히 검증하기 어렵습니다. **WireMock**은 외부 HTTP 의존성을 격리하고, **Postman Collection**은 실제 API 시나리오를 정의하며, **Newman**은 Collection을 CI에서 실행합니다.

---

## 2. 테스트 피라미드에서의 역할

| 도구 | 범위 | 검증 대상 |
|---|---|---|
| JUnit·Mockito | 클래스·Use Case | 분기와 도메인 규칙 |
| WireMock | 외부 HTTP Adapter | 요청 형식, Timeout, 오류 변환 |
| Testcontainers | DB·Redis 통합 | Query, Migration, Transaction |
| Postman·Newman | 배포된 API 흐름 | Routing, Security, JSON 계약, E2E |

각 도구는 대체 관계가 아니라 서로 다른 실패 지점을 검증합니다.

---

## 3. WireMock

```java
stubFor(get(urlPathEqualTo("/maps/directions"))
        .withQueryParam("origin", equalTo("37.1,127.1"))
        .willReturn(okJson("""
                {"distance": 1200, "duration": 300}
                """)));
```

성공 응답뿐 아니라 지연, 연결 종료, 4xx·5xx, 잘못된 JSON도 검증해야 Adapter의 Resilience 정책을 확인할 수 있습니다.

---

## 4. Postman Collection과 Newman

```sh
newman run collection.json \
  --environment environment.json \
  --reporters cli,json \
  --reporter-json-export build/newman/result.json
```

Collection은 다음 구조를 권장합니다.

1. Setup: Tenant, 사용자, 기준 데이터 생성
2. Scenario: 실제 업무 흐름 실행
3. Assertion: Status, Schema, 업무 결과 검증
4. Teardown: 생성 데이터 정리

환경 파일에 Secret을 Commit하지 않고 CI Credential에서 주입합니다.

---

## 5. 실무 사례 적용 관점
이 사례는 Docker Compose로 PostgreSQL, Redis, Core Application, Gateway, Metrics를 기동하고 Health Check가 통과한 뒤 Newman Suite를 실행합니다. 관리자·배차·운행·결제 흐름을 단계별 Collection으로 나누고 JSON Report를 CI Artifact로 보관합니다.

병렬 실행 시 공유 Environment File을 동시에 수정하지 않도록 Scenario별 복사본을 사용해야 합니다. Setup에서 발급된 동적 ID와 Token의 소유 범위도 명확히 해야 합니다.

---

## 6. 안정적인 E2E 원칙
- 고정 Sleep 대신 Polling과 명시적 Timeout을 사용합니다.
- 테스트 순서 의존성을 최소화합니다.
- 실패 시 요청·응답과 Container Log를 함께 보관합니다.
- 외부 운영 API는 WireMock으로 대체하고 별도의 External API Test로 분리합니다.
- E2E는 핵심 사용자 여정에 집중하고 모든 분기를 넣지 않습니다.

---

## 7. WireMock Request Matching
Stub가 너무 느슨하면 잘못된 요청도 성공하고, 너무 구체적이면 중요하지 않은 Header 변경에 Test가 깨집니다.

```java
stubFor(post(urlEqualTo("/sms/v1/messages"))
        .withHeader("Authorization", matching("HMAC .*"))
        .withRequestBody(matchingJsonPath("$.recipient"))
        .willReturn(okJson("{\"messageId\":\"m-1\"}")));
```

업무 계약에 중요한 Method, Path, 인증, 핵심 Payload만 검증합니다. 호출 횟수와 중복 방지도 `verify(1, ...)`로 확인합니다.

## 8. Fault Injection

```java
stubFor(get("/maps")
        .willReturn(aResponse()
                .withFixedDelay(5_000)
                .withStatus(200)));
```

Timeout, Connection Reset, Malformed JSON, 429와 5xx를 주입하여 Retry·Circuit Breaker·오류 변환을 검증합니다. Test Timeout은 Production 정책보다 충분히 짧게 조정하되 동작 의미는 같아야 합니다.

## 9. Postman Environment 관리
변수는 Scope를 구분합니다.

- Collection: API 기본 규칙
- Environment: Host, 환경 이름
- Local·CI Secret: Token, Password
- Runtime: Setup에서 생성한 ID

Script가 Environment를 과도하게 변경하면 Scenario 간 숨은 의존성이 생깁니다. Runtime Context를 Scenario별 파일로 격리합니다.

## 10. Assertion 품질
Status 200만 확인하지 않습니다.

```javascript
pm.test("created booking contract", () => {
  pm.response.to.have.status(201);
  const body = pm.response.json();
  pm.expect(body.id).to.be.a("number");
  pm.expect(body.status).to.eql("CREATED");
});
```

오류 Response의 Code, Field Validation, Pagination Metadata와 Side Effect를 후속 조회로 검증합니다.

## 11. E2E 데이터 전략
- 매 실행 고유 Prefix로 충돌을 피합니다.
- Clock 의존 Scenario는 기준 시각을 명시합니다.
- Setup 실패 시 Scenario를 계속 실행하지 않습니다.
- Teardown이 실패해도 다음 실행이 복구 가능해야 합니다.
- Production Data와 Credential을 사용하지 않습니다.

## 12. Flaky Test 진단
실패를 무조건 Retry하면 실제 Race Condition을 숨깁니다. 첫 실패의 Request·Response·Service Log와 DB 상태를 보존하고, 재시도 결과를 별도로 표시합니다.

비동기 결과는 고정 Sleep 대신 최대 시간 안에서 조건을 반복 조회합니다. Poll 간격과 전체 Deadline을 기록합니다.

## 13. CI 병렬화
독립 Suite만 병렬 실행합니다. 공통 Tenant·사용자·차량을 수정하는 Suite는 Data를 분리하거나 순차 실행합니다. 병렬화로 단축한 시간보다 충돌 진단 비용이 커지지 않게 합니다.

## 14. 계약 변경
API Schema 변경 시 OpenAPI Diff와 E2E를 함께 사용합니다. Consumer가 의존하는 필드 삭제·타입 변경·Enum 축소는 Breaking Change입니다.

## 15. 결과 보고
Newman JSON과 JUnit Reporter, 실패한 요청 이름, 환경, Git Commit, Image Digest를 연결합니다. 실패 Response에 개인정보가 있으면 Artifact 접근과 보관 기간을 제한합니다.

---

## 16. 실무 사례 적용 진단과 개선 과제

Postman Collection, Newman, WireMock과 Testcontainers가 있어 통합 검증 범위는 넓습니다. 다만 Collection이 커질수록 중복 Fixture와 순서 의존, 실제 환경 Credential 의존, 실패 재현성이 위험해집니다.

Collection을 독립 Scenario로 만들고 실행마다 고유 Tenant·Data Prefix를 사용합니다. 외부 Provider 정상·Timeout·5xx·Malformed Response는 WireMock으로 결정적으로 재현하고, Production 계약 변화는 별도 Contract Test로 감지합니다. 재실행으로 통과한 Test를 성공으로 숨기지 말고 Flaky 비율을 지표화합니다.

완료 기준은 병렬 실행과 임의 순서에서도 같은 결과가 나오고, 실패 시 Request/Response·Container Log·DB 상태가 Artifact로 남으며, 외부 Credential 없이 CI 핵심 Suite가 통과하는 상태입니다.

---

# Reference
- [Postman Collections](https://learning.postman.com/docs/collections/collections-overview/)
- [Newman](https://learning.postman.com/docs/collections/using-newman-cli/command-line-integration-with-newman/)
- [WireMock](https://wiremock.org/docs/)
- [[Testcontainer와 TmpFS를 사용한 테스트]]
