---
id: xxd 사용법
started: 2025-04-03
tags:
  - ✅DONE
group: "[[Linux]]"
---
# xxd 사용법

Text Editor는 Byte를 문자 Encoding에 따라 보여 주지만, Binary Protocol·암호화 결과·깨진 Encoding을 분석할 때는 실제 Byte 값을 봐야 한다. `xxd`는 File이나 표준 입력을 16진수로 표시하고, Hex Dump를 다시 Binary로 복원할 수 있는 도구다.

## 기본 Hex Dump 읽기

```shell
xxd sample.bin | head
```

왼쪽은 Byte Offset, 가운데는 16진수 Byte, 오른쪽은 출력 가능한 ASCII 표현이다. 예를 들어 `41`은 ASCII `A`이며 여러 Byte 문자에서는 UTF-8 Encoding 순서를 그대로 확인할 수 있다.

## 헥사값만 출력하고 싶을때
```shell title="hex 값만 출력하고 싶을때."
xxd -p <File Path> | tr -d '\n'

# 한 줄에 출력할 Byte 수를 크게 지정하는 방법
xxd -p -c 9999999999999 <File Path>
```

`-p`는 Offset과 ASCII 영역을 제거한 Plain Hex를 출력한다. 긴 File을 한 줄로 만들면 Terminal과 도구의 입력 한도를 넘을 수 있으므로 Hash나 일부 Header 확인에는 범위를 제한한다.

```shell
# 처음 32Byte만 출력
xxd -l 32 sample.bin

# Offset 128부터 64Byte 출력
xxd -s 128 -l 64 sample.bin

# Byte 단위로 묶어 표시
xxd -g 1 sample.bin
```

## Hex를 다시 Binary로 복원하기

```shell
printf '48656c6c6f0a' | xxd -r -p > hello.txt
```

`-r`은 역변환, `-p`는 Plain Hex 입력을 뜻한다. 복원 후에는 원본과 `sha256sum` 또는 `shasum -a 256` 결과를 비교해 Byte가 동일한지 확인한다.

## 언제 유용한가?

- UTF-8 BOM, CRLF와 보이지 않는 제어 문자 확인
- Image, Archive와 실행 파일의 Magic Number 확인
- Network Packet이나 암호화 Test Vector 비교
- Binary Patch 전후의 정확한 Byte 차이 확인

Password, Token, Private Key를 Hex로 바꾸어도 암호화되는 것은 아니다. Hex Encoding은 표현 방식만 바꾸므로 민감 값이 Terminal History와 Log에 남지 않도록 주의한다.

# Reference
[Vim Help - xxd](https://vimhelp.org/xxd.txt.html)
