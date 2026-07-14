---
id: BFF 란?
started: 2025-05-02
tags:
  - ✅DONE
  - Architecture
  - BFF
group:
  - "[[설계]]"
---

# BFF: 화면의 요구사항을 위한 Backend

Web, Mobile과 외부 Partner 화면은 같은 업무 데이터를 사용해도 필요한 형태가 다르다. 하나의 범용 API가 모든 Client를 만족시키려 하면 응답이 지나치게 커지거나 Client가 여러 API를 직접 조합하게 된다. **Backend for Frontend(BFF)** 는 특정 Frontend의 사용 경험에 맞춘 Server-side 경계다.

## 먼저 이해할 문제

주문 상세 화면에 주문, 결제, 배송과 회원 정보가 필요하다고 가정한다. Browser가 네 Service를 직접 호출하면 다음 문제가 생긴다.

- Mobile Network에서는 왕복 호출 수만큼 Latency가 누적된다.
- 일부 호출만 실패했을 때 화면의 복구 정책이 Frontend에 퍼진다.
- Backend API 변경이 여러 Client Release와 결합된다.
- Browser에 노출하면 안 되는 Credential과 내부 Endpoint가 필요할 수 있다.

BFF는 화면 단위 API를 제공하고 내부 호출을 조정한다.

```text
Web Client -> Web BFF -> Order / Payment / Delivery
Mobile App -> Mobile BFF -> Order / Notification / Location
```

![[BFF 란? - 01.png]]

## API Gateway와 무엇이 다른가

API Gateway는 인증, Routing, Rate Limit, TLS 종료처럼 여러 API에 공통인 Network 정책을 담당한다. BFF는 화면에 필요한 데이터 조합과 Client별 표현을 담당한다.

```text
Gateway: 이 요청을 어느 Service로 보낼까?
BFF: 이 화면에 어떤 데이터와 실패 정책이 필요할까?
```

둘을 같은 Process로 구현할 수는 있지만 책임은 구분해야 한다. Gateway에 화면 조립 Logic이 계속 쌓이면 모든 Client가 하나의 중앙 병목에 결합된다.

## Aggregation 구현

서로 독립적인 호출은 병렬로 실행해 전체 시간을 줄일 수 있다.

```java
record OrderPage(Order order, Payment payment, Delivery delivery) {}

CompletableFuture<Order> order = supplyAsync(() -> orderClient.get(orderId));
CompletableFuture<Payment> payment = supplyAsync(() -> paymentClient.get(orderId));
CompletableFuture<Delivery> delivery = supplyAsync(() -> deliveryClient.get(orderId));

return CompletableFuture.allOf(order, payment, delivery)
    .thenApply(ignored -> new OrderPage(order.join(), payment.join(), delivery.join()));
```

병렬 호출의 전체 Latency는 대략 가장 느린 의존성에 의해 결정되지만, 실패 가능성은 의존성 수만큼 늘어난다. 각 호출에 Timeout을 두고 화면에서 없어도 되는 정보는 부분 응답이나 기본값으로 처리한다.

## BFF가 소유해야 하는 Logic

BFF에 적합한 책임은 Client 관점의 조립과 변환이다.

- 여러 Backend 응답을 화면 DTO로 조합
- Mobile과 Web의 Payload 크기 차이 처리
- Client Version 호환과 Field 이름 변환
- 화면에 불필요하거나 민감한 Field 제거
- UI에 필요한 Pagination과 Partial Failure 표현

가격 계산, 주문 취소 가능 여부와 재고 차감 같은 업무 규칙은 Domain Service가 소유해야 한다. BFF가 업무 규칙을 복제하면 다른 Client와 결과가 달라진다.

## 실패와 Timeout Budget

Client의 전체 Deadline이 1초라면 내부 호출마다 1초를 줄 수 없다. BFF 처리와 Network 여유를 남긴 작은 Budget을 배분한다.

```text
Client deadline 1000 ms
- Gateway/BFF overhead 100 ms
- Response margin 100 ms
= 내부 호출 budget 최대 800 ms
```

Retry는 요청 시간을 더 소비하고 하위 Service 장애를 키울 수 있다. 멱등하고 일시적인 실패에만 제한적으로 사용하며, Circuit Breaker와 Bulkhead로 한 의존성의 지연이 BFF 전체 Thread를 고갈시키지 않게 한다.

## 보안 경계

BFF는 Server Credential을 사용할 수 있지만 이것이 Frontend 인증을 대체하지는 않는다. 사용자 Token을 검증하고 요청한 Resource에 대한 권한을 확인해야 한다. 내부 응답을 그대로 전달하면 개인정보와 운영 Field가 노출될 수 있어 명시적인 Response DTO가 필요하다.

결제 Secret처럼 Client에 절대 전달하면 안 되는 값은 BFF 또는 더 안쪽의 Domain Service에서만 사용한다. Log와 Trace에도 민감 값이 남지 않게 한다.

## BFF가 적합하지 않은 경우

Client가 하나이고 Backend API가 이미 화면 요구에 잘 맞는다면 별도 BFF는 Network Hop과 운영 대상만 늘린다. 단순 Reverse Proxy를 BFF라고 부를 필요도 없다.

BFF가 많아지면 공통 인증, 관측성과 Error Format이 중복될 수 있다. 공통 Platform 기능은 Library나 Gateway로 제공하되 화면 조립까지 다시 하나의 범용 BFF로 합치지 않는 균형이 필요하다.

## 운영에서 확인할 지표

- 화면 API의 P50·P95·P99 Latency
- 하위 Service별 Timeout과 오류율
- 부분 응답 발생률
- Fan-out 호출 수와 Payload 크기
- Client Version별 Traffic과 Error
- Cache Hit와 Stale Data 허용 범위

Trace 하나에서 BFF와 모든 하위 호출이 연결돼야 어느 의존성이 화면을 늦추는지 알 수 있다.

## 기억할 점

BFF는 Frontend 대신 모든 일을 하는 Server가 아니다. 여러 Backend의 안정적인 업무 계약을 **특정 사용자 경험에 필요한 API로 번역하는 Adapter**다. 화면 Logic은 가까이 두고 핵심 업무 규칙은 Domain에 남기는 경계가 가장 중요하다.

# Reference

- [Sam Newman - Backends For Frontends](https://samnewman.io/patterns/architectural/bff/)
