---
id: ULID Primary Key
started: 2025-05-16
tags:
  - ✅DONE
group:
  - "[[Java Spring DB]]"
---
# TSID Primary Key

## 의존성 추가
hibernate 버전 6이상만 사용 가능하다.
```bash
implementation 'io.hypersistence:hypersistence-utils-hibernate-60:3.5.1'
```

## 사용법
```java
import io.hypersistence.utils.hibernate.id.Tsid;
import jakarta.persistence.Id;

public class Member {

    @Id @Tsid
    private Long id;
}
```

# Reference
[TSID 사용법](https://way-code.tistory.com/entry/GeneratedValue-IDENTITY%EB%A5%BC-%EB%B2%97%EC%96%B4%EB%82%98-UUIDULID-%EC%A0%84%EB%9E%B5-%EC%82%AC%EC%9A%A9%ED%95%B4%EB%B3%B4%EA%B8%B0)