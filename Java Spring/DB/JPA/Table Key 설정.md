---
id: Key 설정
started: 2025-03-13
tags:
  - Java
  - JPA
  - DB
  - Spring
  - ✅DONE
group: "[[Java Spring JPA]]"
---
# Table Key 설정
## 예시코드
### 2개 이상의 컬럼을 유니크 컬럼으로 설정
```Java title="두개의 컬럼에 대해서 유니크 Key를 설정할 수 있음."
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(
    name = "custom_entity",
    uniqueConstraints = {
        @UniqueConstraint(columnNames = {"custom_id", "custom_id2"})
    })
public class CustomEntity extends CreateTimeField {
    @Id
    @GeneratedValue
    private Long id;
  
    @Column(nullable = false)
    private String customId;
  
    @Column(nullable = false)  
    private String customId2;  
}
```

# Reference