---
id: Table Indexing
started: 2025-03-13
tags:
  - ✅DONE
  - Java
  - JPA
  - DB
  - Spring
group: "[[Java Spring JPA]]"
---
# Table Indexing
## 인덱싱 예시코드
### 가장 기본적인 형태의 예시코드
```Java title="table indexing example"
@Entity
@NoArgsConstructor  
@AllArgsConstructor
@Table(
	name = "entity", 
	indexes = @Index(
		name = "idx_entity",
		columnList = "indexed_column"
	)
)
public class Entity {
	@Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

	@Column(name = "indexed_column")
	private String indexedColumn;
}
```
### 아래와 같이 인덱스 테이블또한 유니크 설정을 걸 수 있다.
```Java title="table indexing example"
@Entity
@NoArgsConstructor  
@AllArgsConstructor
@Table(
	name = "entity", 
	indexes = @Index(
		name = "idx_entity",
		columnList = "indexed_column",
		unique = true
	)
)
public class Entity {
	@Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

	@Column(name = "indexed_column")
	private String indexedColumn;
}
``` 
### 두개의 컬럼으로 하나의 인덱스 테이블을 설정 할 수 있다.
```Java title="table indexing example"
@Entity
@NoArgsConstructor  
@AllArgsConstructor
@Table(
	name = "entity", 
	indexes = @Index(
		name = "idx_entity",
		columnList = "indexed_column, indexed_column_2",
		unique = true
	)
)
public class Entity {
	@Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

	@Column(name = "indexed_column")
	private String indexedColumn;
	
	@Column(name = "indexed_column_2")
	private String indexedColumnTwo;
}
``` 
### 각각의 컬럼을 2개 이상 인덱스 테이블을 설정하는 방법
```Java title="table indexing example"
@Entity
@NoArgsConstructor  
@AllArgsConstructor
@Table(
    name = "MY_ENTITY",
    indexes = {
        @Index(name = "idx_field1", columnList = "field1"),
        @Index(name = "idx_field2", columnList = "field2")
    }
)
public class MyEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "field1")
    private String field1;
    
    @Column(name = "field2")
    private String field2;
}
``` 
## 인덱싱을 해야하는 이유
key 값이 아닌 일반 컬럼에 대해서 탐색을 수행해야 하는 경우 커서가 처음 컬럼부터 돌면서 탐색하도록 되어있다. 따라서 A라는 컬럼이 일반 컬럼이고 A가 50인 값을 DB에서 찾으려고 할때 모든 컬럼을 일일히 순회하면서 찾아야 한다.
이러한 과정을 Full Scanning이라고 하며 Index 테이블을 따로 만드는 이유는 Full Scanning은 매우 큰 비용이 소모되기 때문에 탐색의 효율을 높히기 위해 사용된다.
### B+ Tree
![[Pasted image 20250313131746.png]]
![[Pasted image 20250313131924.png]]
B-Tree는 자식 노드가 2개 이상인 탐색 트리이다. 각 key의 왼쪽 자신은 항상 key 보다 작은 값을, 오른쪽 자식은 큰 값을 가진다. B-Tree는 항상 key를 기준으로 오름차순 정렬되어 저장된다. 따라서, 부등호 연산에 대해 해시 테이블보다 효율적인 데이터 탐색이 가능하다

하지만, 테이블에 데이터가 갱신(Insert, Update, Delete)가 많이 발생하면 트리의 균형이 깨져버려(B+트리는 균형이 깨지면 균형을 맞추기 위해 데이터를 다시 정렬한다.) 성능이 악화된다. 추가로, 순차검색을 해야 할 경우 중위 순회를 하기 때문에 검색 효율이 좋지 않다.

이러한 이유 때문에 MySQL 엔진인 InnoDB는 B-Tree를 확장/개선한 B+Tree를 인덱스의 자료 구조로 사용한다.
#### Hash Table을 사용하지 않는 이유는 데이터가 정렬되어 저장되지 않기때문에 부등호 연산에 부적합하기 때문이다.

## 인덱스 테이블 설정 시 주의사항
### 카디널리티가 높게 설정하여야 한다.
> [!Note] 카디널리티란?
> 데이터의 중복이 많을수록 카디널리티가 낮다라고 표현한다. 반대로
> 데이터의 중복이 적을수록 카디널리티가 높다고 표현한다.
- 중복되는 값이 많은 테이블은 인덱싱 하는 것이 비효율적이다.
- 탐색을 하지 않는 컬럼은 인덱싱 할 필요가 없다.
- 인덱스 테이블도 별도의 데이터베이스 테이블로 생성되므로 중복된 이름을 피해야한다.

## 개발 중 발생한 문제점
# Reference