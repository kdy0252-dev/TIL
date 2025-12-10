---
id: Join 설정
started: 2025-03-13
tags:
  - ✅DONE
  - Java
  - Spring
  - JPA
  - DB
group: "[[Java Spring JPA]]"
---
# Table Join 설정
## 예시코드
### OneToOne
아래는 연관관계의 주인이되는 테이블이다.
```Java title="OneToOne Example"
@Entity
public class Member {
	@OneToOne
	@JoinColumn(name = "locker_id")
	private Locker locker;
}
```
mappedBy가 있는 컬럼은 연관관계의 주인이 아닌 컬럼이다. 따라서 실제 DB에는 저장되지 않는다.
Locker로 Member를 찾는 경우가 없다면 Locker에는 굳이 Member를 들고 있을 필요가 없다.
```Java title="OneToOne Example"
@Entity
public class Locker {
	@OneToOne(mappedBy = "locker")
	private Member member;
}
```
> [!Warning] mappedBy 사용 시
> mappedBy에는 연관관계 주인의 foreign key 컬럼의 이름을 적어주어야한다.
> Order 테이블에서 Member 테이블을 사용하는 경우 필연적으로 N+1 문제가 생길 수 밖에 없다.
### OneToMany
```Java title="OneToMany Example"
@Entity
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String userName;

    @OneToMany
    @JoinColumn(name = "posts_id")
    private List<Post> posts = new ArrayList<>();
}
```
Posts로 User를 조회하는 경우가 없는 경우 종속관계의 테이블에 mappedBy를 설정하지 않아도 된다.
> [!Warning] 주의사항
> 연관관계의 주인과 반대로 어노테이션을 걸어주어야한다.
```Java title="OneToMany Example"
@Entity
public class Posts {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
	
	@Column
    private String title;

    @ManyToOne
    @JoinColumn(mappedBy = "posts")
    private User user;
}
```
> [!Warning] mappedBy 사용 시
> mappedBy에는 연관관계 주인의 foreign key 컬럼의 이름을 적어주어야한다.
### ManyToOne
```Java title="ManyToOne Example"
@Entity
public class Account {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
	
	@Column
    private String accountName;
	
	@Column
	private int deposit;
	
    @ManyToOne
    @JoinColumn(name = "user_id")
    private User user;
}
```
User로 Account를 조회하는 경우가 없는 경우 종속관계의 테이블에 mappedBy를 설정하지 않아도 된다.
> [!Warning] 주의사항
> 연관관계의 주인과 반대로 어노테이션을 걸어주어야한다.
```Java title="OneToMany Example"
@Entity
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
	
	@Column
    private String userName;

    @ManyToOne
    @JoinColumn(mappedBy = "user")
    private List<Account> accounts = new ArrayList<>();
}
```
> [!Warning] mappedBy 사용 시
> mappedBy에는 연관관계 주인의 foreign key 컬럼의 이름을 적어주어야한다.
> User 테이블에서 Account 테이블을 사용하는 경우 필연적으로 N+1 문제가 생길 수 밖에 없다.

### ManyToMany
> [!Warning] ManyToMany는 되도록 사용하지 않는 것이 좋다.
> ManyToMany를 사용해야만 하는 상황이라면 중간 테이블을 만들어 OneToMany와 ManyToOne의 형태로 만드는 것이 유지보수에 좋다.

---
## Annotation Options
### fetch = FetchType.LAZY or FetchType.EAGER
```Java title="예시 코드"
@Entity
public class Member {
	@OneToOne(fetch = FetchType.LAZY) // FetchType.EAGER
	@JoinColumn(name = "locker_id")
	private Locker locker;
}
```
OneToOne 뿐만 아니라 OneToMany ManyToOne에도 해당 옵션이 있다.
데이터 조회 시 실제 데이터를 사용하기 전에는 연관관계가 설정된 컬럼을 조회하지 않고 기다리는 옵션이다.
>[!Warning] 사용 시 주의사항
>N+1 문제가 발생할 수 있으므로 사용 시 주의가 필요하다.
### @JoinColumn(referencedColumnName = "idx")
실제 참조할 값의 컬럼을 직접 설정 해줄 수 있다. Primary Key가 아닌 것들도 설정할 수 있으나 권장하지 않는다.
```Java title="UserEntity (referencedColumnName 예시코드)"
@Table(name = "user")
@Entity
public class User {
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_info_idx", referencedColumnName = "user_id")
    private UserInfo userInfo;
}
```

```Java title="UserInfoEntity (referencedColumnName 예시코드)"
@Table(name = "user_info")
@Entity
public class UserInfo {
	@Id
	private Long id;

	@Column
	private Long userId;
}

```

### Casecade
case cade 는 두 테이블의 컬럼이 따로 생성되는 것이 아니라 같이 생성되고 관리되어야 하는 경우에 설정한다.

### orphanRemoval
orphanRemoval 옵션을 사용하면 부모 객체와의 연관관계가 끊어진 자식을 자동으로 삭제 할 수 있다.

--- 
## Table Join을 해야하는 이유
1. **객체-관계 불일치 해소**  
    객체 지향 프로그래밍에서는 객체 간의 관계(예: 상속, 연관, 집합 등)를 사용하지만, 관계형 데이터베이스는 테이블 간의 관계(예: 외래키)를 사용합니다. 연관관계 매핑은 이 두 모델 간의 구조적 차이를 연결해 주어, 애플리케이션의 도메인 모델과 데이터베이스 스키마 간의 간극(gap)을 메꿔줍니다.
2. **개발 생산성 및 유지보수 향상**  
    연관관계 매핑을 통해 개발자는 SQL을 직접 작성하지 않고도 객체 간의 관계를 코드 내에서 자연스럽게 다룰 수 있습니다. ORM 프레임워크가 자동으로 필요한 JOIN이나 데이터 조회, 저장 작업을 처리해 주기 때문에 개발 시간이 단축되고, 코드의 유지보수성이 높아집니다.
3. **데이터 무결성 보장**  
    올바르게 매핑된 연관관계는 데이터베이스의 외래키 제약조건과 결합되어 데이터 무결성을 보장합니다. 예를 들어, 부모-자식 관계에서 부모 데이터가 삭제될 때 자식 데이터에 미치는 영향 등을 매핑 설정을 통해 관리할 수 있습니다.
4. **추상화와 캡슐화**  
    데이터베이스의 복잡한 구조나 JOIN 연산 등은 매핑 계층에서 추상화되어, 개발자는 객체 모델에 집중할 수 있습니다. 이는 도메인 로직을 간결하게 유지하고, 비즈니스 로직과 데이터 접근 로직의 분리를 명확하게 합니다.
5. **확장성과 유연성**  
    도메인 모델이 변경되거나 새로운 기능이 추가될 때, 연관관계 매핑을 통해 데이터베이스와 애플리케이션 간의 연동을 보다 쉽게 관리할 수 있습니다. 즉, 변화에 대응하기 용이한 구조를 만들 수 있습니다.

---
## 주의사항
#### ManyToMany 사용을 피한다.

#### MappedBy는 연관관계의 주인이 아니기때문에 실제 데이터베이스에는 값이 저장되지 않는다.

#### Join된 테이블의 컬럼을 조회할때 **N+1** 문제를 항상 생각하여야한다.
#### 컬렉션이나 캐시를 사용하는 경우, 엔티티의 equals와 hashCode를 올바르게 구현하지 않으면 예상치 못한 동작이 발생할 수 있으므로 주의 해야한다.

# Reference