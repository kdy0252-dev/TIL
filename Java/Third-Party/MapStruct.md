---
id: MapStruct
started: 2026-05-13
tags:
  - ✅DONE
  - Java
  - Mapping
group:
  - "[[Java Third-Party]]"
---
# MapStruct: 컴파일 타임 객체 매핑

## 1. 개요 (Overview)
**MapStruct**는 Java Annotation Processor를 사용하여 객체 간 매핑 코드를 컴파일 시점에 생성합니다. Reflection 기반 Mapper와 달리 생성된 코드는 일반 메서드 호출이므로 실행 흐름을 추적하기 쉽고, 매핑되지 않은 필드나 타입 불일치를 빌드 단계에서 발견할 수 있습니다.

---

## 2. 적합한 경계
MapStruct는 구조가 비슷한 데이터 객체 사이의 기계적인 변환에 적합합니다.

- JPA Entity ↔ Persistence Data
- 외부 API DTO ↔ Adapter Data
- 반복되는 단순 필드 복사

다음 변환에는 수동 Mapper가 더 명확할 수 있습니다.

- Domain Model 생성 시 비즈니스 검증이 필요합니다.
- 여러 Aggregate를 조회하여 조립해야 합니다.
- 변환 과정에 권한, 상태 전이, 외부 조회가 포함됩니다.
- `create()`, `load()`, `reconstitute()` 같은 의도 있는 Factory를 반드시 호출해야 합니다.

---

## 3. 기본 예제

```java
@Mapper(componentModel = MappingConstants.ComponentModel.SPRING)
public interface CenterPolicyMapper {

    @Mapping(target = "id", source = "entity.id")
    @Mapping(target = "centerId", source = "entity.centerId")
    CenterPolicyData toData(CenterPolicyJpaEntity entity);
}
```

```java
@MapperConfig(
        componentModel = MappingConstants.ComponentModel.SPRING,
        unmappedTargetPolicy = ReportingPolicy.ERROR
)
public interface MappingConfig {
}
```

`unmappedTargetPolicy = ERROR`를 사용하면 대상 필드가 추가됐는데 Mapper가 갱신되지 않은 상황을 컴파일 오류로 발견할 수 있습니다.

---

## 4. Domain Model과의 경계
Persistence Entity를 Domain Model로 자동 매핑할 때는 캡슐화를 우회하지 않아야 합니다.

```java
public CenterPolicy toDomain(CenterPolicyJpaEntity entity) {
    CenterPolicyData data = generatedMapper.toData(entity);
    return CenterPolicy.load(data);
}
```

MapStruct는 `Data` 생성까지만 담당하고, Domain 복원은 Domain Factory가 담당하게 하면 기술적 필드 복사와 비즈니스 불변식 복원을 분리할 수 있습니다.

---

## 5. 주의사항
- 양방향 Mapper를 무조건 만들지 않습니다. 읽기와 쓰기의 모델이 다르면 방향별로 명시합니다.
- Lazy Association을 매핑 중 접근하면 N+1 문제가 발생할 수 있습니다.
- `expression = "java(...)"`가 많아지면 생성 Mapper의 장점이 줄어듭니다.
- Update Mapping은 Domain Setter를 요구하게 만들 수 있으므로 쓰기 Domain에는 신중히 적용합니다.
- 생성 코드는 직접 수정하지 않고 Mapper 선언을 변경합니다.

---

## 6. Annotation Processor 동작
MapStruct는 컴파일 중 Mapper Interface를 읽고 `...Impl` Java Source를 생성한 뒤 함께 컴파일합니다.

```text
Mapper Interface
  -> Annotation Processing
  -> Generated Mapper Source
  -> javac
  -> 일반 Java Bytecode
```

Runtime Reflection이나 Proxy가 없으므로 Debugger로 생성 코드를 따라갈 수 있습니다. IDE의 Annotation Processing 설정이 꺼져 있으면 컴파일 오류처럼 보일 수 있습니다.

## 7. Nested Mapping과 명시성

```java
@Mapping(target = "centerName", source = "center.name")
@Mapping(target = "createdBy", source = "audit.createdBy")
MemberRow toRow(MemberEntity entity);
```

Nested Association 접근은 Lazy Loading을 유발할 수 있습니다. Mapper가 SQL을 발생시키지 않도록 Query 단계에서 Fetch 범위를 명확히 하거나 Projection을 사용합니다.

## 8. Null 처리
Null 전략은 생성과 부분 Update에서 다릅니다.

```java
@BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
void patch(MemberPatch source, @MappingTarget MemberEntity target);
```

`IGNORE`는 Patch에는 유용하지만 "명시적으로 null로 변경"과 "필드 미전달"을 구분하지 못합니다. Optional Field Wrapper나 별도 Command가 필요할 수 있습니다.

Domain Model에 `@MappingTarget`을 적용해 Setter를 열지 않습니다.

## 9. Custom 변환

```java
default PhoneNumber toPhoneNumber(String value) {
    return PhoneNumber.of(value);
}
```

단순 Value Object 변환은 Default Method로 둘 수 있습니다. DB 조회, 권한 판단, 외부 호출이 필요하면 Mapper가 아니라 Application Service·Assembler로 이동합니다.

## 10. Mapping Lifecycle Hook
`@BeforeMapping`, `@AfterMapping`은 공통 정규화에 유용하지만 숨은 업무 로직을 만들 수 있습니다. Hook이 결과의 핵심 의미를 바꾼다면 명시적인 메서드 호출이 더 낫습니다.

## 11. 실무 사례 적용 선택 기준

| 상황 | 선택 |
|---|---|
| Entity와 Data의 반복 필드 복사 | MapStruct |
| Aggregate 복원 | Domain `load/reconstitute` |
| 조회 전용 일부 필드 | JPA·QueryDSL Projection |
| 여러 Source 조립 | Assembler |
| 상태 전이 | Domain Method |

## 12. 테스트
생성 코드 자체의 필드 대입을 모두 테스트하기보다 중요한 Custom 변환, Null 정책과 Domain Factory 연결을 검증합니다. `unmappedTargetPolicy=ERROR`를 켜면 필드 추가 누락은 Compiler가 잡습니다.

- Enum 변환의 미지원 값
- Null과 빈 문자열
- Nested 값 누락
- 시간대·날짜 변환
- Domain 복원 후 불변식

---

## 13. 실무 사례 적용 진단과 개선 과제

MapStruct와 수동 Mapper가 함께 존재해 Mapping 방식이 Slice마다 달라질 수 있습니다. Domain Reconstitution에서 Setter식 Mapping이나 Null 무시가 사용되면 불변식과 부분 업데이트 의미가 흐려질 위험이 있습니다.

단순 DTO·Projection 변환만 MapStruct에 맡기고 Aggregate 생성·상태 전이는 명시적 Factory를 사용합니다. `unmappedTargetPolicy = ERROR`, Null 전략, Enum 미지원 값 처리를 공통 Convention으로 고정하고 Mapper 생성 코드도 Review 대상에 포함합니다.

완료 기준은 필드 추가 시 누락 Mapping이 Compile Error가 되고, Update Mapping의 Null 의미가 Test로 고정되며, Domain 불변식을 우회하는 Mapper가 없는 상태입니다.

---

# Reference
- [MapStruct Reference Guide](https://mapstruct.org/documentation/stable/reference/html/)
- [[Projection과 Hydration]]
