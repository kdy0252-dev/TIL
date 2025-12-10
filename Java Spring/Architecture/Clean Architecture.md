---
id: Clean Architecture
started: 2025-04-25
tags:
  - ✅DONE
group:
  - "[[Java Spring Architecture]]"
---
# Clean Architecture
클린 아키텍처(Clean Architecture)는 소프트웨어 시스템을 독립적이고 유지보수 가능하며 테스트하기 쉽게 만들기 위한 소프트웨어 디자인 철학이다. 로버트 C. 마틴(Robert C. Martin)이 제안한 이 아키텍처는 시스템을 여러 개의 동심원으로 분리하여, 외부의 변화에 영향을 받지 않도록 핵심 비즈니스 로직을 보호하는 것을 목표로 한다.
## 핵심 원리
클린 아키텍처의 핵심 원리는 **관심사의 분리(Separation of Concerns)**와 **의존성 역전(Dependency Inversion)**이다. 이를 통해 시스템의 각 부분을 독립적으로 유지하고, 변화에 유연하게 대응할 수 있도록 한다.
- **관심사의 분리**: 각 모듈은 하나의 책임만 가져야 하며, 다른 모듈의 구현 세부 사항에 의존하지 않아야 한다.
- **의존성 역전**: 고수준 모듈은 저수준 모듈의 구현에 의존하지 않고, 추상화된 인터페이스에 의존해야 한다.
## 레이어 구조
클린 아키텍처는 일반적으로 다음과 같은 레이어로 구성된다. 중심에서 바깥쪽으로 갈수록 의존성이 낮아진다.
```
+-----------------------------------------------------------------------+
|                               Entities(중심)                           |
+-----------------------------------------------------------------------+
|                               Use Cases                               |
+-----------------------------------------------------------------------+
|                         Interface Adapters                            |
+-----------------------------------------------------------------------+
|                           Frameworks & Drivers                        |
+-----------------------------------------------------------------------+
```
1.  **Entities (엔티티)**:
    - 가장 안쪽에 위치한 레이어로, 핵심 비즈니스 규칙을 캡슐화한다.
    - 엔티티는 애플리케이션 전체에서 사용되는 기본적인 데이터 구조와 비즈니스 로직을 포함한다.
    - 이 레이어는 어떤 외부 요소에도 의존하지 않으며, 가장 안정적이다.
2.  **Use Cases (유스케이스)**:
    - 엔티티 바로 바깥쪽 레이어로, 애플리케이션의 특정 사용 사례(Use Case)를 구현한다.
    - 유스케이스는 엔티티를 사용하여 비즈니스 로직을 수행하고, 애플리케이션의 흐름을 정의한다.
    - 이 레이어는 엔티티에는 의존하지만, 외부 프레임워크나 드라이버에는 의존하지 않는다.
3.  **Interface Adapters (인터페이스 어댑터)**:
    - 유스케이스 바깥쪽 레이어로, 유스케이스와 외부 세계 사이의 인터페이스를 담당한다.
    - 이 레이어는 데이터를 유스케이스에 적합한 형태로 변환하고, 유스케이스의 결과를 외부 세계에 적합한 형태로 변환한다.
    - 여기에는 컨트롤러, 프레젠터, 게이트웨이 등이 포함될 수 있다.
4.  **Frameworks & Drivers (프레임워크와 드라이버)**:
    - 가장 바깥쪽 레이어로, UI, 데이터베이스, 외부 API 등 구체적인 기술적인 구현을 포함한다.
    - 이 레이어는 인터페이스 어댑터를 통해 유스케이스와 상호 작용하며, 시스템의 세부적인 동작을 담당한다.
    - 이 레이어는 가장 변화에 민감하며, 내부 레이어에 영향을 주지 않도록 설계되어야 한다.
## 의존성 규칙
클린 아키텍처의 핵심 규칙은 **의존성은 항상 안쪽으로 향해야 한다**는 것이다. 즉, 바깥쪽 레이어는 안쪽 레이어에 의존할 수 있지만, 안쪽 레이어는 바깥쪽 레이어에 의존해서는 안 된다.
- 엔티티는 어떤 레이어에도 의존하지 않는다.
- 유스케이스는 엔티티에만 의존한다.
- 인터페이스 어댑터는 유스케이스와 엔티티에 의존한다.
- 프레임워크와 드라이버는 모든 레이어에 의존할 수 있다.
## 예제
간단한 주문 처리 시스템을 예로 들어 클린 아키텍처를 설명하겠다.
### 1. Entities (엔티티)
```java
// 주문 (Order) 엔티티
public class Order {
    private Long id;
    private Long customerId;
    private List<OrderItem> orderItems;
    private LocalDateTime orderDate;

    public Order(Long id, Long customerId, List<OrderItem> orderItems, LocalDateTime orderDate) {
        this.id = id;
        this.customerId = customerId;
        this.orderItems = orderItems;
        this.orderDate = orderDate;
    }

    public Long getId() { return id; }
    public Long getCustomerId() { return customerId; }
    public List<OrderItem> getOrderItems() { return orderItems; }
    public LocalDateTime getOrderDate() { return orderDate; }

    public double getTotalAmount() {
        return orderItems.stream()
                .mapToDouble(OrderItem::getAmount)
                .sum();
    }
}

// 주문 아이템 (OrderItem) 엔티티
public class OrderItem {
    private Long productId;
    private int quantity;
    private double amount;

    public OrderItem(Long productId, int quantity, double amount) {
        this.productId = productId;
        this.quantity = quantity;
        this.amount = amount;
    }

    public Long getProductId() { return productId; }
    public int getQuantity() { return quantity; }
    public double getAmount() { return amount; }
}
```
### 2. Use Cases (유스케이스)
```java
// 주문 생성 유스케이스 인터페이스
public interface CreateOrderUseCase {
    Order createOrder(Long customerId, List<OrderItem> orderItems);
}

// 주문 생성 유스케이스 구현
public class CreateOrderService implements CreateOrderUseCase {
    private final OrderRepository orderRepository;

    public CreateOrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @Override
    public Order createOrder(Long customerId, List<OrderItem> orderItems) {
        Order order = new Order(null, customerId, orderItems, LocalDateTime.now());
        return orderRepository.save(order);
    }
}

// 주문 저장 리포지토리 인터페이스
public interface OrderRepository {
    Order save(Order order);
}
```
### 3. Interface Adapters (인터페이스 어댑터)
```java
// 주문 컨트롤러
@RestController
public class OrderController {
    private final CreateOrderUseCase createOrderUseCase;

    public OrderController(CreateOrderUseCase createOrderUseCase) {
        this.createOrderUseCase = createOrderUseCase;
    }

    @PostMapping("/orders")
    public ResponseEntity<Order> createOrder(@RequestBody CreateOrderRequest request) {
        Order order = createOrderUseCase.createOrder(request.getCustomerId(), request.getOrderItems());
        return ResponseEntity.ok(order);
    }
}

// 주문 요청 DTO
public class CreateOrderRequest {
    private Long customerId;
    private List<OrderItem> orderItems;

    public Long getCustomerId() { return customerId; }
    public void setCustomerId(Long customerId) { this.customerId = customerId; }
    public List<OrderItem> getOrderItems() { return orderItems; }
    public void setOrderItems(List<OrderItem> orderItems) { this.orderItems = orderItems; }
}

// 주문 응답 DTO
public class OrderResponse {
    private Long id;
    private Long customerId;
    private List<OrderItem> orderItems;
    private LocalDateTime orderDate;
    private double totalAmount;

    public OrderResponse(Order order) {
        this.id = order.getId();
        this.customerId = order.getCustomerId();
        this.orderItems = order.getOrderItems();
        this.orderDate = order.getOrderDate();
        this.totalAmount = order.getTotalAmount();
    }

    public Long getId() { return id; }
    public Long getCustomerId() { return customerId; }
    public List<OrderItem> getOrderItems() { return orderItems; }
    public LocalDateTime getOrderDate() { return orderDate; }
    public double getTotalAmount() { return totalAmount; }
}
```
### 4. Frameworks & Drivers (프레임워크와 드라이버)
```java
// JPA 주문 리포지토리
@Repository
public class JpaOrderRepository implements OrderRepository {
    private final JpaOrderEntityRepository jpaOrderEntityRepository;

    public JpaOrderRepository(JpaOrderEntityRepository jpaOrderEntityRepository) {
        this.jpaOrderEntityRepository = jpaOrderEntityRepository;
    }

    @Override
    public Order save(Order order) {
        OrderEntity orderEntity = new OrderEntity();
        orderEntity.setCustomerId(order.getCustomerId());
        orderEntity.setOrderDate(order.getOrderDate());
        OrderEntity savedOrderEntity = jpaOrderEntityRepository.save(orderEntity);

        for (OrderItem orderItem : order.getOrderItems()) {
            OrderItemEntity orderItemEntity = new OrderItemEntity();
            orderItemEntity.setOrderId(savedOrderEntity.getId());
            orderItemEntity.setProductId(orderItem.getProductId());
            orderItemEntity.setQuantity(orderItem.getQuantity());
            orderItemEntity.setAmount(orderItem.getAmount());
            // jpaOrderItemEntityRepository.save(orderItemEntity);
        }

        return new Order(savedOrderEntity.getId(), savedOrderEntity.getCustomerId(), order.getOrderItems(), savedOrderEntity.getOrderDate());
    }
}

// Spring Data JPA 엔티티
@Entity(name = "orders")
public class OrderEntity {
    @Id
    @GeneratedValue
    private Long id;
    private Long customerId;
    private LocalDateTime orderDate;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getCustomerId() { return customerId; }
    public void setCustomerId(Long customerId) { this.customerId = customerId; }
    public LocalDateTime getOrderDate() { return orderDate; }
    public void setOrderDate(LocalDateTime orderDate) { this.orderDate = orderDate; }
}

@Entity(name = "order_items")
class OrderItemEntity {
    @Id
    @GeneratedValue
    private Long id;
    private Long orderId;
    private Long productId;
    private int quantity;
    private double amount;

    public Long getId() { return id; }

    public void setId(Long id) { this.id = id; }

    public Long getOrderId() { return orderId; }

    public void setOrderId(Long orderId) { this.orderId = orderId; }

    public Long getProductId() { return productId; }

    public void setProductId(Long productId) { this.productId = productId; }

    public int getQuantity() { return quantity; }

    public void setQuantity(int quantity) { this.quantity = quantity; }

    public double getAmount() { return amount; }

    public void setAmount(double amount) { this.amount = amount; }
}

// Spring Data JPA 리포지토리
interface JpaOrderEntityRepository extends JpaRepository<OrderEntity, Long> {
}
```
## 장점
- **유지보수성**: 각 레이어가 독립적이므로 코드 변경이 특정 레이어에 국한되어 유지보수가 용이하다.
- **테스트 용이성**: 각 레이어를 독립적으로 테스트할 수 있다.
- **유연성**: 외부 기술 변경에 대한 영향이 적다. 예를 들어, 데이터베이스를 변경하더라도 핵심 비즈니스 로직은 변경할 필요가 없다.
- **확장성**: 새로운 기능을 추가하거나 기존 기능을 변경할 때 시스템 전체에 미치는 영향을 최소화할 수 있다.
- **관심사 분리**: 각 레이어가 특정 역할에 집중하므로 코드의 가독성이 향상되고, 개발자가 특정 영역에 집중할 수 있다.
## 단점
- **복잡성 증가**: 아키텍처의 복잡성이 증가할 수 있다. 특히, 레이어 간의 인터페이스를 정의하고 구현하는 데 추가적인 노력이 필요하다.
- **초기 개발 비용 증가**: 클린 아키텍처를 적용하기 위해서는 초기 설계 단계에서 더 많은 시간을 투자해야 한다.
- **학습 곡선**: 새로운 아키텍처 스타일에 대한 학습이 필요하다. 특히, 레이어 간의 의존성 규칙을 이해하고 준수하는 데 어려움을 겪을 수 있다.
- **보일러플레이트 코드 증가**: 레이어 간의 데이터 전송을 위해 DTO(Data Transfer Object)를 사용해야 하므로, 보일러플레이트 코드가 증가할 수 있다.
## 고려사항
- **레이어의 Granularity**: 레이어를 너무 세분화하면 클래스 수가 증가하고 코드의 복잡성이 증가할 수 있다. 반대로, 레이어를 너무 크게 정의하면 클린 아키텍처의 장점을 제대로 활용할 수 없다. 레이어의 Granularity는 애플리케이션의 요구사항과 복잡성을 고려하여 신중하게 결정해야 한다.
- **DTO의 사용**: 레이어 간의 데이터 전송을 위해 DTO를 사용하는 것이 일반적이지만, DTO를 과도하게 사용하면 코드의 복잡성이 증가할 수 있다. DTO는 필요한 경우에만 사용하고, 엔티티를 직접 사용하는 것을 고려할 수도 있다.
- **테스트 전략**: 클린 아키텍처에서는 각 레이어를 독립적으로 테스트하는 것이 중요하다. 단위 테스트와 통합 테스트를 적절히 조합하여 시스템의 안정성을 확보해야 한다.
## 결론
클린 아키텍처는 소프트웨어 시스템을 유지보수 가능하고 테스트하기 쉽게 만드는 데 효과적인 아키텍처 스타일이다. 하지만 아키텍처의 복잡성이 증가하고, 초기 개발 비용이 증가할 수 있다는 단점도 존재한다. 따라서, 클린 아키텍처를 적용하기 전에 애플리케이션의 요구사항과 복잡성을 신중하게 고려해야 한다.
# Reference
- Robert C. Martin, "Clean Architecture: A Craftsman's Guide to Software Structure and Design"