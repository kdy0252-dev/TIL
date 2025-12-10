---
id: Strategy Pattern
started: 2025-05-15
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---
# Strategy Pattern

## Strategy Pattern이란?
전략 패턴은 동일한 계열의 알고리즘들을 캡슐화하여 필요에 따라 교체할 수 있게 하는 디자인 패턴이다. 이를 통해 클라이언트는 구체적인 알고리즘 구현에 의존하지 않고도 다양한 알고리즘을 사용할 수 있다.
## 핵심 아이디어
전략 패턴의 핵심은 알고리즘을 인터페이스로 정의하고, 이를 구현하는 여러 구체적인 전략 클래스를 만드는 것이다. Context는 이 인터페이스를 통해 전략 객체와 상호작용하며, 어떤 전략을 사용할지는 런타임에 결정할 수 있다.
## 코드
```java
// Strategy 인터페이스
interface Payment {
    void pay(int amount);
}
```

```java
// ConcreteStrategy: 신용 카드 결제
class CreditCardPayment implements Payment {
    private String cardNumber;
    private String expiryDate;
    private String cvv;

    public CreditCardPayment(String cardNumber, String expiryDate, String cvv) {
        this.cardNumber = cardNumber;
        this.expiryDate = expiryDate;
        this.cvv = cvv;
    }

    @Override
    public void pay(int amount) {
        System.out.println(amount + " paid with Credit Card ending with " + cardNumber.substring(cardNumber.length() - 4));
    }
}
```

```java
// ConcreteStrategy: PayPal 결제
class PaypalPayment implements Payment {
    private String email;
    private String password;

    public PaypalPayment(String email, String password) {
        this.email = email;
        this.password = password;
    }

    @Override
    public void pay(int amount) {
        System.out.println(amount + " paid using PayPal account " + email);
    }
}
```

```java
// Context
class ShoppingCart {
    private Payment payment;
    private int amount;

    public ShoppingCart(Payment payment, int amount) {
        this.payment = payment;
        this.amount = amount;
    }

    public void setPaymentStrategy(Payment payment) {
        this.payment = payment;
    }

    public void checkout() {
        payment.pay(amount);
    }
}
```

```java
// Main
public class Main {
    public static void main(String[] args) {
        // 신용 카드 결제
        Payment creditCardPayment = new CreditCardPayment("1234-5678-9012-3456", "12/24", "123");
        ShoppingCart cart1 = new ShoppingCart(creditCardPayment, 100);
        cart1.checkout(); // 100 paid with Credit Card ending with 3456

        // PayPal 결제
        Payment paypalPayment = new PaypalPayment("test@example.com", "password");
        ShoppingCart cart2 = new ShoppingCart(paypalPayment, 50);
        cart2.checkout(); // 50 paid using PayPal account test@example.com

        // 결제 방식 변경
        cart2.setPaymentStrategy(creditCardPayment);
        cart2.checkout(); // 50 paid with Credit Card ending with 3456
    }
}
```
## 장점
*   **유연성**: 런타임에 알고리즘을 동적으로 변경할 수 있다.
*   **재사용성**: 여러 Context에서 동일한 알고리즘을 재사용할 수 있다.
*   **유지보수성**: 새로운 알고리즘을 쉽게 추가하거나 기존 알고리즘을 수정할 수 있다.
*   **관심사 분리**: 알고리즘과 Context의 역할을 분리하여 각자의 책임에 집중할 수 있다.
## 단점
*   전략 클래스가 많아질 수 있다.
*   클라이언트가 사용할 전략을 직접 선택해야 하는 경우가 있다.
## 사용 시 주의사항
*   Context가 전략에 너무 의존적이지 않도록 주의해야 한다.
*   전략 객체는 상태를 가지지 않도록 설계하는 것이 좋다.
*   전략 패턴이 불필요하게 복잡성을 증가시키지 않는지 고려해야 한다.
## 실제 활용 사례
*   정렬 알고리즘 선택 (Quick Sort, Merge Sort 등)
*   압축 알고리즘 선택 (ZIP, GZIP 등)
*   캐싱 전략 선택 (LRU, FIFO 등)
## SOLID 원칙과의 연관성
전략 패턴은 SOLID 원칙을 따르는 데 도움이 된다.
*   **단일 책임 원칙 (SRP)**: 각 전략 클래스는 하나의 알고리즘에 대한 책임만 가진다. Context는 알고리즘 선택 로직에 집중하고, 각 전략은 자신의 알고리즘 구현에만 집중한다.
*   **개방-폐쇄 원칙 (OCP)**: 새로운 전략을 추가하더라도 기존 Context 코드를 수정할 필요가 없다. 새로운 전략 클래스를 만들고 Context에서 해당 전략을 선택하도록 설정하면 된다.
*   **리스코프 치환 원칙 (LSP)**: Strategy 인터페이스를 구현하는 모든 ConcreteStrategy는 Context에서 문제없이 사용될 수 있어야 한다.
*   **인터페이스 분리 원칙 (ISP)**: 전략 인터페이스를 작게 유지하여 클라이언트가 필요하지 않은 메서드에 의존하지 않도록 한다.
*   **의존 역전 원칙 (DIP)**: Context는 ConcreteStrategy에 직접 의존하지 않고, Strategy 인터페이스에 의존한다. 이를 통해 Context와 ConcreteStrategy 간의 결합도를 낮출 수 있다.
# Reference