---
id: Spring Modulith
started: 2025-08-21
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Spring Modulith (Modular Monolith Architecture)

## 1. 개요 (Overview)
**Spring Modulith**는 Spring Boot 기반 애플리케이션에서 **모듈러 모놀리스(Modular Monolith)** 아키텍처를 구현, 검증, 문서화하는 것을 돕는 공식 프레임워크입니다. (이전 이름: Moduliths)

마이크로서비스(MSA)는 강력하지만, "분산 시스템의 복잡성"이라는 막대한 비용을 요구합니다. 많은 팀이 섣불리 MSA를 도입했다가 운영 비용 감당에 실패하곤 합니다.
**모듈러 모놀리스**는 "단일 배포 유닛(jar)"이라는 모놀리스의 단순함을 유지하면서도, 내부 코드는 마이크로서비스처럼 엄격하게 격리된 모듈 구조를 가짐으로써 유지보수성과 확장성을 확보하는 실용적인 대안입니다.

---

## 2. 왜 필요한가? (Problem & Solution)

### 2.1 스파게티 코드의 원인
일반적인 Spring 프로젝트는 레이어별 패키징(Controller, Service, Repository)을 주로 사용합니다. 이는 시간이 지나면 서로 다른 도메인(예: 주문, 결제, 배송)의 서비스들이 서로를 무분별하게 참조(`@Autowired`)하게 만들고, 결국 순환 참조와 강결합(Tightly Coupled)된 "거대한 진흙 덩어리(Big Ball of Mud)"가 됩니다.

### 2.2 Spring Modulith의 해결책
- **패키지 기반 모듈 정의**: 도메인별로 패키지를 나누고, 이를 하나의 '논리적 모듈'로 취급합니다.
- **접근 제어**: Java의 접근 제어자(`package-private`)를 활용하거나 아키텍처 테스트를 통해, 모듈의 Public API가 아닌 내부 클래스에 다른 모듈이 접근하는 것을 원천 차단합니다.
- **이벤트 기반 통신**: 모듈 간의 결합을 끊기 위해 직접적인 메서드 호출 대신 Spring Event(`ApplicationEvent`)를 사용하도록 장려합니다.

---

## 3. 핵심 기능 (Key Features)

### 3.1 모듈 구조 검증 (`ApplicationModules`)
`ApplicationModules` 클래스는 애플리케이션의 패키지 구조를 분석하여 모듈 간의 의존성 규칙 위반을 감지합니다.
- **순환 의존성(Cycle) 감지**: 모듈 A -> B -> A 참조 금지.
- **허용되지 않은 접근 감지**: 모듈 A가 모듈 B의 비공개(Internal) 클래스를 사용하려 할 때 테스트 실패.

### 3.2 문서화 자동화 (Integration with ArchUnit)
애플리케이션 코드를 정적 분석하여 C4 Model 다이어그램(PlantUML)을 자동으로 생성해줍니다. 코드가 곧 설계 문서가 되므로 "문서와 코드의 불일치" 문제를 해결합니다.

### 3.3 트랜잭션 아웃박스 패턴 지원 (Event Registry)
모듈 간에 이벤트를 주고받을 때, 수신 측이 실패해도 이벤트가 유실되지 않도록 DB에 잠깐 저장해두었다가 재발행하는 **Event Publication Registry** 기능을 내장하고 있습니다. 이를 통해 Kafka 같은 외부 브로커 없이도 DB 트랜잭션 범위 내에서 안전한 이벤트 통신이 가능합니다.

---

## 4. 예제 코드 (Implementation)

### 4.1 프로젝트 구조
```text
src/main/java/com/example
  ├── inventory    // [Inventory 모듈]
  │   ├── InventoryService.java (internal)
  │   ├── InventoryUpdatedEvent.java (public)
  │   └── package-info.java
  │
  ├── order        // [Order 모듈]
  │   ├── OrderController.java
  │   └── OrderService.java
  │
  └── Application.java
```

### 4.2 의존성 검증 테스트
아래 테스트는 모듈 간의 잘못된 참조가 발생하면 실패합니다. CI/CD 파이프라인에 넣어두면 아키텍처가 무너지는 것을 자동으로 막을 수 있습니다.

```java
import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;
import org.springframework.modulith.docs.Documenter;

class ModulithArchitectureTest {

    // 1. 모듈 구조 분석
    ApplicationModules modules = ApplicationModules.of(Application.class);

    @Test
    void verifyModularity() {
        // modules.verify() 메서드는 다음을 포함한 다양한 아키텍처 규칙을 검증합니다:
        // - 모듈 간의 순환 의존성 (Cyclic Dependencies)이 없는지 확인합니다.
        // - 모듈의 Public API를 통해서만 다른 모듈에 접근하는지 확인합니다.
        // - Spring Modulith가 제공하는 기본 아키텍처 규칙들을 준수하는지 검증합니다.
        // 규칙 위반 시 테스트가 실패하며, 상세한 오류 메시지를 제공합니다.
        modules.verify();

        // 특정 모듈 간의 의존성 규칙을 추가로 정의할 수도 있습니다.
        // 예를 들어, 'order' 모듈은 'inventory' 모듈에 의존할 수 있지만, 그 반대는 안 됩니다.
        // modules.getByName("order").dependsOn("inventory");
        // modules.getByName("inventory").doesNotDependOn("order");
    }

    @Test
    void writeDocumentation() {
        // Documenter는 분석된 모듈 구조를 기반으로 다양한 형식의 아키텍처 문서를 생성합니다.
        // 기본적으로 PlantUML 형식의 C4 Model 다이어그램을 생성하여
        // 'target/modulith-docs' 폴더에 저장합니다.
        // 이 다이어그램은 모듈 간의 의존성 관계를 시각적으로 보여주어 아키텍처를 쉽게 이해할 수 있도록 돕습니다.
        // 코드가 변경되면 문서를 다시 생성하여 항상 최신 상태를 유지할 수 있습니다.
        new Documenter(modules)
            .writeModulesAsPlantUml() // 모듈 간의 의존성 다이어그램
            .writeIndividualModulesAsPlantUml(); // 각 모듈 내부의 컴포넌트 다이어그램
    }
}
```
이러한 테스트는 CI/CD 파이프라인에 통합되어, 개발자가 아키텍처 규칙을 위반하는 코드를 커밋하는 것을 자동으로 방지할 수 있습니다.

### 3.3 이벤트 기반 통신 및 트랜잭션 아웃박스 패턴

모듈 간의 결합도를 낮추는 가장 효과적인 방법 중 하나는 **이벤트 기반 통신**입니다. Spring Modulith는 Spring의 내장 `ApplicationEventPublisher`를 활용하여 모듈 간의 비동기적이고 느슨하게 결합된 통신을 장려합니다.

#### 3.3.1 In-memory Event Bus (`ApplicationEventPublisher` & `@ApplicationModuleListener`)
Spring Modulith는 Spring의 `ApplicationEventPublisher`를 사용하여 모듈 내에서 이벤트를 발행하고, `@ApplicationModuleListener` 어노테이션을 사용하여 다른 모듈에서 이벤트를 수신하도록 합니다. 이는 기본적으로 JVM 내에서 동작하는 In-memory Event Bus 역할을 합니다.

**Order Module (이벤트 발행)**
```java
package com.example.order.service;

import com.example.order.domain.Order;
import com.example.order.domain.OrderRepository;
import com.example.order.event.OrderPlacedEvent; // Public Event

import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final ApplicationEventPublisher events; // Spring의 이벤트 발행자

    @Transactional // 주문 저장과 이벤트 발행이 하나의 트랜잭션으로 묶임
    public Order placeOrder(Order order) {
        Order savedOrder = orderRepository.save(order);
        // 직접 inventoryService.decrease()를 호출하지 않고 이벤트 발행
        // 이 이벤트는 Order 모듈의 Public API로 간주됩니다.
        events.publishEvent(new OrderPlacedEvent(savedOrder.getId(), savedOrder.getProductId(), savedOrder.getQuantity()));
        return savedOrder;
    }
}
```

**Inventory Module (이벤트 수신)**
```java
package com.example.inventory.listener;

import com.example.inventory.service.InventoryService; // Internal Service
import com.example.order.event.OrderPlacedEvent; // 다른 모듈의 Public Event

import lombok.RequiredArgsConstructor;
import org.springframework.modulith.events.ApplicationModuleListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@RequiredArgsConstructor
public class InventoryEventListener {
    private final InventoryService inventoryService;

    // @ApplicationModuleListener는 Spring Modulith가 제공하는 이벤트 리스너 어노테이션입니다.
    // 기본적으로 @Async + @Transactional(propagation = Propagation.REQUIRES_NEW) 처럼 동작합니다.
    // 이는 이벤트 처리 로직이 별도의 트랜잭션에서 비동기적으로 실행됨을 의미합니다.
    // 따라서 재고 처리 중 오류가 발생하더라도 주문 트랜잭션에는 영향을 주지 않습니다.
    // (옵션: @Transactional(propagation = Propagation.MANDATORY)를 사용하여 기존 트랜잭션에 참여시킬 수도 있습니다.)
    @ApplicationModuleListener
    public void on(OrderPlacedEvent event) {
        System.out.println("재고 모듈: 주문 이벤트 수신 - Order ID: " + event.orderId());
        inventoryService.decreaseStock(event.productId(), event.quantity());
        // 재고 감소 로직 (예: DB 업데이트)
    }
}
```

#### 3.3.2 트랜잭션 아웃박스 패턴 (Event Publication Registry)
In-memory Event Bus는 단순하지만, 이벤트 발행과 이벤트 처리 간의 **신뢰성** 문제가 발생할 수 있습니다. 예를 들어, 주문 저장 트랜잭션이 성공한 직후 애플리케이션이 다운되면, 이벤트가 발행되지 않아 재고 감소 로직이 실행되지 않을 수 있습니다.

Spring Modulith는 이러한 문제를 해결하기 위해 **Event Publication Registry** 기능을 내장하고 있습니다. 이는 **트랜잭션 아웃박스 패턴(Transactional Outbox Pattern)**을 구현한 것입니다.
1.  이벤트 발행 시, 이벤트는 즉시 데이터베이스의 `OUTBOX` 테이블에 저장됩니다. 이 저장 작업은 비즈니스 로직(예: 주문 저장)과 **동일한 데이터베이스 트랜잭션** 내에서 이루어집니다.
2.  비즈니스 트랜잭션이 성공적으로 커밋되면, `OUTBOX` 테이블에 저장된 이벤트가 `ApplicationEventPublisher`를 통해 발행됩니다.
3.  만약 이벤트 발행 직후 시스템에 장애가 발생하더라도, `OUTBOX` 테이블에 이벤트가 안전하게 저장되어 있으므로, 애플리케이션 재시작 시 Spring Modulith가 `OUTBOX` 테이블을 스캔하여 미발행된 이벤트를 찾아 다시 발행합니다.

이를 통해 Kafka와 같은 외부 메시지 브로커 없이도 DB 트랜잭션 범위 내에서 **안전하고 신뢰성 있는 이벤트 통신**이 가능해집니다.

#### 3.3.3 In-memory Event Bus vs. External Message Broker
| 특징             | In-memory Event Bus (Spring Modulith)                               | External Message Broker (Kafka, RabbitMQ 등)                               |
| :--------------- | :------------------------------------------------------------------ | :------------------------------------------------------------------------- |
| **배포 단위**    | 단일 모놀리스 애플리케이션 내                                       | 분리된 마이크로서비스 간 또는 모놀리스와 외부 시스템 간                    |
| **복잡성**       | 낮음 (별도 인프라 필요 없음)                                        | 높음 (브로커 설치, 관리, 모니터링 필요)                                    |
| **확장성**       | 단일 애플리케이션의 확장성에 종속                                   | 브로커 및 컨슈머 그룹을 통한 높은 수평 확장성                              |
| **신뢰성**       | Event Publication Registry를 통해 높은 신뢰성 보장 (DB 트랜잭션)  | 브로커의 영속성 및 메시지 전달 보장 메커니즘을 통해 높은 신뢰성 보장     |
| **트랜잭션**     | 발행자와 동일 트랜잭션 내에서 이벤트 저장, 리스너는 별도 트랜잭션 | 발행자와 브로커 간의 트랜잭션 보장 어려움 (2PC 또는 Outbox 패턴 필요)    |
| **사용 사례**    | 모듈러 모놀리스 내부의 도메인 이벤트 통신                           | 분산 시스템 간의 이벤트 통신, 대규모 데이터 스트리밍, 비동기 작업 큐       |
| **장점**         | 설정 및 운영 단순, 개발 초기 비용 절감, 트랜잭션 일관성 확보 용이   | 높은 확장성, 다양한 프로토콜 지원, 이기종 시스템 통합 용이                 |
| **단점**         | 모놀리스 경계를 벗어난 통신 불가, 확장성 제약                       | 높은 운영 비용, 복잡한 설정, 분산 시스템의 고유한 문제 발생                |

**결론**: Spring Modulith의 In-memory Event Bus는 모듈러 모놀리스 내부에서 도메인 이벤트를 안정적으로 처리하기에 매우 적합합니다. 시스템이 마이크로서비스로 진화하거나, 외부 시스템과의 통합이 필요해질 때 비로소 Kafka와 같은 외부 메시지 브로커를 도입하는 것이 합리적입니다. Spring Modulith는 이러한 전환을 용이하게 하는 기반을 제공합니다.

### 3.4 자동 문서화 (Automatic Documentation Generation)

Spring Modulith는 애플리케이션 코드를 정적 분석하여 아키텍처 다이어그램을 자동으로 생성하는 기능을 제공합니다. 이는 `Documenter` 클래스를 통해 이루어지며, 주로 **C4 Model** 기반의 **PlantUML** 다이어그램을 생성합니다.

*   **C4 Model**: 소프트웨어 시스템을 컨텍스트(Context), 컨테이너(Container), 컴포넌트(Component), 코드(Code)의 네 가지 추상화 레벨로 나누어 설명하는 모델입니다. Spring Modulith는 주로 컨테이너(모듈) 및 컴포넌트(모듈 내부의 주요 클래스) 레벨의 다이어그램을 생성합니다.
*   **PlantUML**: 텍스트 기반으로 다이어그램을 그릴 수 있게 해주는 도구입니다. 생성된 PlantUML 파일은 IDE 플러그인이나 온라인 렌더러를 통해 시각적인 다이어그램으로 변환할 수 있습니다.

**장점**:
*   **코드와 문서의 일관성**: 코드가 변경되면 문서를 다시 생성하여 항상 최신 상태를 유지할 수 있습니다. "문서와 코드가 불일치하는" 고질적인 문제를 해결합니다.
*   **아키텍처 가시성**: 복잡한 모듈 간의 의존성 관계를 시각적으로 명확하게 보여주어, 새로운 팀원이 시스템을 빠르게 이해하는 데 도움을 줍니다.
*   **설계 검토 용이**: 생성된 다이어그램을 통해 아키텍처 설계가 의도대로 구현되었는지 쉽게 검토할 수 있습니다.

**생성되는 문서 예시**:
*   `modules.puml`: 전체 모듈 간의 의존성 관계를 보여주는 다이어그램 (C4 Container Level)
*   `inventory-components.puml`: `inventory` 모듈 내부의 주요 컴포넌트(서비스, 리포지토리 등) 간의 관계를 보여주는 다이어그램 (C4 Component Level)

## 4. 결론: 언제 Spring Modulith를 도입해야 하는가?

Spring Modulith는 모든 프로젝트에 필요한 만능 해결책은 아닙니다. 하지만 특정 상황에서는 매우 강력한 도구가 될 수 있습니다.

*   **추천하는 경우**:
    *   **MSA로의 점진적 전환 계획**: 현재는 모놀리스로 시작하지만, 미래에 특정 도메인을 마이크로서비스로 분리할 가능성이 있는 경우. Spring Modulith는 이러한 전환을 위한 견고한 기반을 마련해줍니다.
    *   **도메인 복잡도가 높은 모놀리스**: 여러 도메인이 얽혀 스파게티 코드가 되기 쉬운 대규모 모놀리스 프로젝트에서 아키텍처를 구조화하고 유지보수성을 높이고자 할 때.
    *   **팀 규모가 커지는 프로젝트**: 여러 팀이 하나의 코드베이스를 공유할 때, 명확한 모듈 경계는 팀 간의 충돌을 줄이고 독립적인 개발을 가능하게 합니다.
    *   **아키텍처 일관성 유지의 어려움**: 개발자들이 아키텍처 규칙을 쉽게 위반하는 경향이 있어, 자동화된 검증 메커니즘이 필요한 경우.
    *   **문서화 부담 경감**: 아키텍처 문서화에 드는 노력을 줄이고, 항상 최신 상태의 문서를 유지하고 싶은 경우.

*   **비추천하는 경우**:
    *   **아주 단순한 CRUD 애플리케이션**: 도메인 복잡도가 낮고, 모듈화의 이점이 크지 않은 소규모 프로젝트에서는 오버헤드가 될 수 있습니다.
    *   **이미 MSA 환경이 잘 구축된 경우**: 이미 서비스 간의 통신 및 경계가 명확하게 정의된 마이크로서비스 아키텍처에서는 Spring Modulith의 필요성이 낮습니다.
    *   **엄격한 모듈 경계가 필요 없는 경우**: 프로토타이핑이나 실험적인 프로젝트에서는 빠른 개발 속도가 더 중요할 수 있습니다.

Spring Modulith는 모놀리스의 단순함과 마이크로서비스의 구조적 이점을 결합하여, 복잡한 비즈니스 도메인을 가진 애플리케이션을 효과적으로 구축하고 관리할 수 있는 실용적인 대안을 제공합니다. 이는 "모놀리스 우선" 전략을 채택하는 팀에게 강력한 아키텍처 가이드라인과 자동화된 도구를 제공하여, 장기적인 성공을 위한 견고한 기반을 마련해 줄 것입니다.

---

## Reference
*   [Spring Modulith Reference Documentation](https://docs.spring.io/spring-modulith/reference/)
*   [Quick Start Guide](https://spring.io/projects/spring-modulith)
*   [Video: Spring Modulith - Oliver Drotbohm](https://www.youtube.com/watch?v=mYyvXl5O6Kk)
*   [C4 Model for Software Architecture](https://c4model.com/)