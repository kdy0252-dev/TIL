---
id: Hexagonal Architecture
started: 2025-04-25
tags:
  - ✅DONE
group:
  - "[[Java Spring Architecture]]"
---
# Hexagonal Architecture
헥사고날 아키텍처(Hexagonal Architecture), 또는 포트와 어댑터 아키텍처(Ports and Adapters Architecture)는 소프트웨어 애플리케이션의 핵심 비즈니스 로직을 외부 의존성으로부터 분리하여 유연성, 테스트 용이성, 유지보수성을 높이는 것을 목표로 하는 아키텍처 스타일이다. 이 아키텍처는 애플리케이션을 "육각형"으로 표현하며, 육각형의 각 면은 애플리케이션이 외부와 상호 작용하는 포트를 나타낸다.
## 핵심 원리
헥사고날 아키텍처의 핵심 원리는 애플리케이션의 비즈니스 로직을 외부 세계와 격리하는 것이다. 이를 위해 다음과 같은 개념을 사용한다.
- **애플리케이션 코어(Application Core)**: 핵심 비즈니스 로직을 포함하며, 외부 시스템이나 기술에 대한 의존성이 없어야 한다.
- **포트(Port)**: 애플리케이션이 외부와 상호 작용하는 인터페이스 역할을 한다. 포트는 애플리케이션의 경계를 정의하며, 외부 세계와의 모든 통신은 포트를 통해 이루어진다.
    - **Driving Port (Primary Port, Inbound Port)**: 외부 액터(사용자, 다른 시스템)가 애플리케이션의 기능을 사용하기 위해 호출하는 인터페이스.
    - **Driven Port (Secondary Port, Outbound Port)**: 애플리케이션이 외부 시스템(데이터베이스, 메시지 큐)과 상호 작용하기 위해 사용하는 인터페이스.
- **어댑터(Adapter)**: 포트를 통해 들어오거나 나가는 데이터를 특정 기술에 맞게 변환하는 역할을 한다. 어댑터는 애플리케이션 코어와 외부 시스템 사이의 중재자 역할을 한다.
    - **Driving Adapter (Primary Adapter, Inbound Adapter)**: 외부 액터의 요청을 애플리케이션 코어가 이해할 수 있는 형태로 변환한다. 예를 들어, HTTP 요청을 애플리케이션의 도메인 객체로 변환하는 역할을 한다.
    - **Driven Adapter (Secondary Adapter, Outbound Adapter)**: 애플리케이션 코어의 응답을 외부 시스템이 이해할 수 있는 형태로 변환한다. 예를 들어, 도메인 객체를 데이터베이스에 저장하기 위한 쿼리로 변환하는 역할을 한다.
## 구조
헥사고날 아키텍처는 일반적으로 다음과 같은 구조를 가진다.
```
+-------------------+      +-------------------+
|  Driving Adapters |----->|   Driving Ports   |
+-------------------+      +-------------------+
     (e.g., UI, API)         (Use Cases)
                              ^        |
                              |        v
+-------------------+      +-------------------+
| Application Core  |<-----|   Domain Logic    |
+-------------------+      +-------------------+
                              ^        |
                              |        v
+-------------------+      +-------------------+
|   Driven Ports    |<-----|  Driven Adapters  |
+-------------------+      +-------------------+
     (Repositories)         (e.g., DB, MQ)
```
- **Driving Adapters**: 사용자 인터페이스, REST API, CLI 등 외부 액터의 요청을 애플리케이션 코어가 이해할 수 있는 형태로 변환한다.
- **Driving Ports**: 외부 액터가 애플리케이션의 기능을 사용하기 위해 호출하는 인터페이스이다. 유스케이스(Use Case)를 정의한다.
- **Application Core**: 핵심 비즈니스 로직을 포함한다. 이 레이어는 외부 시스템에 대한 의존성이 없어야 한다.
- **Domain Logic**: 비즈니스 규칙과 도메인 모델을 포함한다.
- **Driven Ports**: 애플리케이션 코어가 외부 시스템과 상호 작용하기 위해 사용하는 인터페이스이다. 리포지토리(Repository) 인터페이스를 정의한다.
- **Driven Adapters**: 데이터베이스, 메시지 큐 등 외부 시스템과의 통신을 담당한다.
## 예제
간단한 온라인 서점 시스템을 예로 들어 헥사고날 아키텍처를 설명하겠다.
### 1. 도메인 모델 정의
먼저, 도메인 모델을 정의한다.
```java
// 책 (Book) 도메인 모델
public class Book {
    private Long id;
    private String title;
    private String author;
    private double price;

    public Book(Long id, String title, String author, double price) {
        this.id = id;
        this.title = title;
        this.author = author;
        this.price = price;
    }

    public Long getId() { return id; }
    public String getTitle() { return title; }
    public String getAuthor() { return author; }
    public double getPrice() { return price; }
}
```
### 2. 포트 정의
다음으로, 애플리케이션의 입력 및 출력 포트를 정의한다.
```java
// Driving Port: 책 등록 유스케이스
public interface RegisterBookUseCase {
    Book registerBook(String title, String author, double price);
}

// Driving Port: 책 정보 조회 유스케이스
public interface GetBookUseCase {
    Book getBook(Long id);
}

// Driven Port: 책 저장 리포지토리
public interface BookRepository {
    Book save(Book book);
    Book findById(Long id);
}
```
### 3. 어댑터 구현
포트를 구현하는 어댑터를 작성한다.
```java
// Driving Adapter: REST API를 통해 책 등록 요청 처리
@RestController
public class BookController {
    private final RegisterBookUseCase registerBookUseCase;
    private final GetBookUseCase getBookUseCase;

    public BookController(RegisterBookUseCase registerBookUseCase, GetBookUseCase getBookUseCase) {
        this.registerBookUseCase = registerBookUseCase;
        this.getBookUseCase = getBookUseCase;
    }

    @PostMapping("/books")
    public ResponseEntity<Book> registerBook(@RequestBody RegisterBookRequest request) {
        Book book = registerBookUseCase.registerBook(request.getTitle(), request.getAuthor(), request.getPrice());
        return ResponseEntity.ok(book);
    }

    @GetMapping("/books/{id}")
    public ResponseEntity<Book> getBook(@PathVariable Long id) {
        Book book = getBookUseCase.getBook(id);
        if (book == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(book);
    }
}

// Driven Adapter: 데이터베이스에 책 저장
@Repository
public class JpaBookRepository implements BookRepository {
    private final JpaBookEntityRepository jpaBookEntityRepository;

    public JpaBookRepository(JpaBookEntityRepository jpaBookEntityRepository) {
        this.jpaBookEntityRepository = jpaBookEntityRepository;
    }

    @Override
    public Book save(Book book) {
        BookEntity bookEntity = new BookEntity();
        bookEntity.setTitle(book.getTitle());
        bookEntity.setAuthor(book.getAuthor());
        bookEntity.setPrice(book.getPrice());
        BookEntity savedBookEntity = jpaBookEntityRepository.save(bookEntity);
        return new Book(savedBookEntity.getId(), savedBookEntity.getTitle(), savedBookEntity.getAuthor(), savedBookEntity.getPrice());
    }

    @Override
    public Book findById(Long id) {
        BookEntity bookEntity = jpaBookEntityRepository.findById(id).orElse(null);
        if (bookEntity == null) {
            return null;
        }
        return new Book(bookEntity.getId(), bookEntity.getTitle(), bookEntity.getAuthor(), bookEntity.getPrice());
    }
}
```
### 4. 애플리케이션 코어 구현
핵심 비즈니스 로직을 구현한다.
```java
// 책 등록 유스케이스 구현
@Service
public class RegisterBookService implements RegisterBookUseCase {
    private final BookRepository bookRepository;

    public RegisterBookService(BookRepository bookRepository) {
        this.bookRepository = bookRepository;
    }

    @Override
    public Book registerBook(String title, String author, double price) {
        Book book = new Book(null, title, author, price);
        return bookRepository.save(book);
    }
}

// 책 정보 조회 유스케이스 구현
@Service
public class GetBookService implements GetBookUseCase {
    private final BookRepository bookRepository;

    public GetBookService(BookRepository bookRepository) {
        this.bookRepository = bookRepository;
    }

    @Override
    public Book getBook(Long id) {
        return bookRepository.findById(id);
    }
}
```
### 5. Spring Data JPA 엔티티 정의
```java
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;

@Entity(name = "books")
public class BookEntity {
    @Id
    @GeneratedValue
    private Long id;
    private String title;
    private String author;
    private double price;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }
    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
}
```
### 6. Spring Data JPA Repository 정의
```java
import org.springframework.data.jpa.repository.JpaRepository;

public interface JpaBookEntityRepository extends JpaRepository<BookEntity, Long> {
}
```
### 7. DTO 정의
```java
public class RegisterBookRequest {
    private String title;
    private String author;
    private double price;

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }
    public double getPrice() { return price; }
    public void setPrice(double price) { this.price = price; }
}
```
## 장점
- **유연성**: 외부 기술 변경에 대한 영향이 최소화된다. 예를 들어, 데이터베이스를 변경하더라도 애플리케이션 코어는 변경할 필요가 없다.
- **테스트 용이성**: 애플리케이션 코어를 외부 시스템과 독립적으로 테스트할 수 있다. Mock 객체를 사용하여 어댑터를 대체하면, 애플리케이션 코어의 동작을 쉽게 검증할 수 있다.
- **유지보수성**: 코드 변경이 특정 레이어에 국한되므로 유지보수가 용이하다.
- **관심사 분리**: 각 레이어가 특정 역할에 집중하므로 코드의 가독성이 향상되고, 개발자가 특정 영역에 집중할 수 있다.
- **병렬 개발**: 각 포트와 어댑터를 독립적으로 개발할 수 있으므로, 개발팀 간의 협업이 용이해진다.
## 단점
- **복잡성 증가**: 아키텍처의 복잡성이 증가할 수 있다. 특히, 포트와 어댑터를 정의하고 구현하는 데 추가적인 노력이 필요하다.
- **초기 개발 비용 증가**: 헥사고날 아키텍처를 적용하기 위해서는 초기 설계 단계에서 더 많은 시간을 투자해야 한다.
- **학습 곡선**: 새로운 아키텍처 스타일에 대한 학습이 필요하다. 특히, 포트와 어댑터의 개념을 이해하고 적용하는 데 어려움을 겪을 수 있다.
- **과도한 추상화**: 모든 외부 의존성을 포트와 어댑터로 분리하려고 하면, 코드의 복잡성이 불필요하게 증가할 수 있다. 적절한 수준에서 추상화를 적용해야 한다.
## 고려사항
- **포트의 Granularity**: 포트를 너무 작게 분리하면 클래스 수가 증가하고 코드의 복잡성이 증가할 수 있다. 반대로, 포트를 너무 크게 정의하면 헥사고날 아키텍처의 장점을 제대로 활용할 수 없다. 포트의 Granularity는 애플리케이션의 요구사항과 복잡성을 고려하여 신중하게 결정해야 한다.
- **어댑터의 구현 방식**: 어댑터를 구현하는 방식은 다양하다. 예를 들어, 데이터베이스 어댑터는 JPA, JDBC, MyBatis 등 다양한 기술을 사용하여 구현할 수 있다. 어댑터의 구현 방식은 외부 시스템의 특성과 애플리케이션의 요구사항을 고려하여 결정해야 한다.
- **테스트 전략**: 헥사고날 아키텍처에서는 애플리케이션 코어를 외부 시스템과 독립적으로 테스트하는 것이 중요하다. Mock 객체를 사용하여 어댑터를 대체하고, 애플리케이션 코어의 동작을 검증하는 테스트 전략을 수립해야 한다.
## 결론
헥사고날 아키텍처는 애플리케이션의 유연성, 테스트 용이성, 유지보수성을 높이는 데 효과적인 아키텍처 스타일이다. 하지만 아키텍처의 복잡성이 증가하고, 초기 개발 비용이 증가할 수 있다는 단점도 존재한다. 따라서, 헥사고날 아키텍처를 적용하기 전에 애플리케이션의 요구사항과 복잡성을 신중하게 고려해야 한다.
# Reference
- Alistair Cockburn, "Hexagonal Architecture"
- Steve Freeman and Nat Pryce, "Growing Object-Oriented Guided by Tests"