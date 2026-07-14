---
id: Apache POI 대용량 Excel 처리
started: 2026-05-11
tags:
  - ✅DONE
  - Java
  - Excel
group:
  - "[[Java Third-Party]]"
---
# Apache POI를 이용한 대용량 Excel 처리

## 1. 개요 (Overview)
**Apache POI**는 Java에서 Excel의 `.xls`와 `.xlsx` 파일을 읽고 쓰는 라이브러리입니다. 관리자가 회원이나 기사 데이터를 일괄 등록하는 기능에서는 파일 형식 검증, 메모리 사용량, 행별 오류 수집과 트랜잭션 범위를 함께 설계해야 합니다.

---

## 2. 처리 방식 선택

| 방식 | 특징 | 적합한 경우 |
|---|---|---|
| `HSSFWorkbook` | `.xls` 전체 Workbook을 메모리에 적재 | 작은 구형 Excel |
| `XSSFWorkbook` | `.xlsx` 전체 Workbook을 메모리에 적재 | 작은 파일, 편리한 API 필요 |
| SAX Event Model | XML을 순차적으로 읽음 | 대용량 `.xlsx` 입력 |
| `SXSSFWorkbook` | 일정 Row만 메모리에 두고 임시 파일 사용 | 대용량 `.xlsx` 출력 |

대용량 입력을 `XSSFWorkbook`으로 처리하면 압축된 파일보다 훨씬 큰 객체 그래프가 만들어져 Heap이 고갈될 수 있습니다.

---

## 3. 처리 파이프라인

```text
Multipart File
  -> 확장자·MIME·크기 검증
  -> Header Schema 검증
  -> Streaming Row Parsing
  -> Cell Normalization
  -> Row Validation
  -> Command 변환
  -> Chunk 단위 저장
  -> 오류 보고서
```

Parsing, Validation, Persistence를 분리하면 Excel 셀 주소와 비즈니스 오류를 함께 보고하면서 Domain 규칙은 재사용할 수 있습니다.

---

## 4. 셀 값 처리
Excel은 화면에 보이는 값과 내부 타입이 다를 수 있습니다. 날짜 Serial, Formula, 숫자로 저장된 전화번호, 빈 문자열과 Blank Cell을 구분해야 합니다.

```java
DataFormatter formatter = new DataFormatter(Locale.KOREA);
String value = formatter.formatCellValue(cell, formulaEvaluator).trim();
```

- 전화번호와 식별자는 숫자가 아니라 문자열로 취급합니다.
- 날짜는 허용 Format을 명시하고 Time Zone을 고정합니다.
- Formula 실행이 필요 없다면 허용하지 않거나 계산된 값만 사용합니다.
- Header 이름과 순서를 Schema Version으로 관리합니다.

---

## 5. 실무 사례 적용 관점
이 사례는 회원·기사 Excel Parser와 공통 Streaming Parser를 분리합니다. 공통 계층은 Workbook·Cell의 기술 처리를 담당하고, Slice 내부 Parser는 행을 업무 입력 모델로 변환합니다.

Batch Size를 제한하여 한 번에 저장되는 Entity 수와 Persistence Context 크기를 통제합니다. 전체 파일을 하나의 트랜잭션으로 묶을지 Chunk별로 커밋할지는 부분 성공 허용 여부에 따라 결정합니다.

---

## 6. 보안과 운영
- Zip Bomb 방어 설정과 최대 압축 비율을 확인합니다.
- 업로드 크기, Sheet 수, Row 수, Cell 길이에 상한을 둡니다.
- Formula Injection을 방지하기 위해 출력 문자열의 `=`, `+`, `-`, `@` 시작을 처리합니다.
- 실패한 행 번호와 필드 오류를 사용자에게 제공하되 원본 개인정보를 로그에 남기지 않습니다.
- 임시 파일과 Stream은 반드시 종료합니다.

---

## 7. Streaming Reader 내부 동작
`.xlsx`는 ZIP 안에 XML 파일을 가진 OOXML 형식입니다. SAX 방식은 Sheet XML을 순차 Event로 읽어 전체 Workbook 객체를 만들지 않습니다.

```text
.xlsx ZIP
  ├─ sharedStrings.xml
  ├─ styles.xml
  └─ worksheets/sheet1.xml
         -> SAX startElement/endElement
         -> Cell Value 변환
         -> Row Consumer
```

Shared String Table과 Style 정보도 Memory를 사용할 수 있습니다. 문자열 중복이 적고 고유 값이 매우 많은 파일은 Shared String Memory가 커질 수 있습니다.

## 8. Row 모델과 검증 단계

```java
public record MemberExcelRow(
        int rowNumber,
        String name,
        String mobileNumber,
        String birthDateText
) {
}
```

1. **구문 검증**: 필수 Cell 존재, 날짜·숫자 형식
2. **행 내부 검증**: 시작일 ≤ 종료일 같은 필드 관계
3. **파일 내부 검증**: 중복 전화번호·ID
4. **업무 검증**: DB 중복, 권한, 상태 정책

모든 검증을 Parser에 넣지 않고 각 단계의 오류를 `rowNumber`, `column`, `code`, `message`로 표준화합니다.

## 9. Transaction 전략

### All-or-nothing
한 행이라도 실패하면 전체를 저장하지 않습니다. 사용자 기대는 단순하지만 대용량 파일의 긴 Transaction과 Lock이 문제가 될 수 있습니다.

### Chunk Commit
일정 행씩 Commit합니다. 대용량에 유리하지만 부분 성공 상태와 재실행 정책이 필요합니다.

### Validation 후 Apply
먼저 전체 파일을 검증하고 임시 Staging에 저장한 뒤, 검증 성공 시 Chunk로 반영합니다. 정확성과 운영성을 높이지만 구현이 복잡합니다.

이 사례의 업무 중요도와 파일 크기에 따라 선택하고 API Response에 처리 방식을 명확히 알립니다.

## 10. 중복과 재실행
Upload가 Timeout된 뒤 사용자가 같은 파일을 다시 올릴 수 있습니다. File Hash, 업무 Key와 Import Job ID를 사용해 중복 실행을 식별합니다.

```text
Upload
  -> SHA-256 + Tenant + Import Type
  -> 기존 Job 확인
  -> 같은 Payload면 기존 결과 반환 또는 명시적 재실행
```

Database Unique Constraint가 최종 중복 방어선이어야 합니다.

## 11. Excel 출력
대량 Export는 `SXSSFWorkbook`의 Row Window를 제한합니다.

```java
try (SXSSFWorkbook workbook = new SXSSFWorkbook(100)) {
    workbook.setCompressTempFiles(true);
    // Row를 순차 기록
} finally {
    workbook.dispose();
}
```

`dispose()`를 호출하지 않으면 Temporary File이 남을 수 있습니다. HTTP Streaming 중 Client 연결이 끊긴 경우에도 정리되어야 합니다.

## 12. Formula와 보안
외부 Excel의 Formula를 Server에서 계산하면 예상치 못한 참조와 높은 CPU 비용이 발생할 수 있습니다. 입력 Template에서는 Formula를 금지하거나 계산 결과만 읽습니다.

Export 문자열이 `=cmd|...`처럼 시작하면 사용자가 파일을 열 때 Spreadsheet Formula로 해석될 수 있습니다. 신뢰할 수 없는 값 앞에 `'`를 붙이는 등 정책을 적용합니다.

## 13. 성능 측정
- 파일 크기보다 Row 수·Cell 수·고유 문자열 수를 기록합니다.
- Parse, Validation, DB Write 시간을 분리합니다.
- Peak Heap과 Temporary Disk를 측정합니다.
- Batch Size별 Throughput과 Transaction 시간을 비교합니다.
- 최대 허용 파일을 실제 Container Memory Limit 안에서 테스트합니다.

## 14. 테스트 케이스
- 빈 파일, Header 누락·중복·순서 변경
- `.xls` 확장자로 위장한 다른 형식
- 날짜·숫자·Formula·Blank Cell
- 매우 긴 문자열과 최대 Row
- 파일 내 중복과 DB 중복
- 중간 Chunk 실패와 동일 파일 재실행
- Zip Bomb 제한 초과

---

## 15. 실무 사례 적용 진단과 개선 과제

Excel Import/Export 기능은 존재하지만 데이터가 커질 때 Workbook 전체 Hydration, 한 Transaction 처리, 실패 Row의 재실행이 운영 위험입니다. Formula, Zip Bomb, 비정상 Cell Type도 신뢰할 수 없는 입력으로 다뤄야 합니다.

Import는 SAX Streaming, 파일·Row·Cell 길이 제한, Formula 미실행, Chunk Transaction과 Row별 오류 보고를 적용합니다. Export는 SXSSF Temp File 정리와 비동기 Job을 사용하고 동일 파일 재처리에 Import Job Idempotency Key를 둡니다.

완료 기준은 최대 허용 크기 파일에서 Heap 상한을 지키고 중간 실패 후 안전하게 재개하며, 악성 Formula·압축 파일·형식 오류 Test가 통과하고 Temp File이 항상 삭제되는 상태입니다.

---

# Reference
- [Apache POI](https://poi.apache.org/)
- [Apache POI Spreadsheet How-To](https://poi.apache.org/components/spreadsheet/how-to.html)
