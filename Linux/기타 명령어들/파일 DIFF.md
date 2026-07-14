---
id: 파일 DIFF
started: 2025-05-02
tags:
  - ✅DONE
  - Linux
group: "[[Linux]]"
---
# 파일 DIFF

Diff는 두 File의 현재 상태만 비교하는 것이 아니라, 설정 변경을 검토하고 Patch를 전달하며 자동화 결과의 회귀를 찾는 기본 도구다. 비교 전에는 줄바꿈, Encoding과 자동 Formatting 차이가 실제 내용 차이를 가리지 않는지 확인한다.

```shell title="Unified Diff 생성"
diff -u old.conf new.conf > config.patch
```

Unified Diff에서 `-`는 이전 File에서 제거된 줄, `+`는 새 File에 추가된 줄이며 `@@`는 변경 위치를 나타낸다. `diff`는 차이가 없으면 종료 코드 0, 차이가 있으면 1, 실행 오류면 2를 반환한다. 따라서 Script에서는 출력 문자열보다 종료 코드를 사용한다.

```shell
if diff -q expected.txt actual.txt >/dev/null; then
  echo 'same'
else
  echo 'different or error'
fi
```

오류와 단순 차이를 구분해야 하는 자동화라면 `$?`를 1과 2로 나누어 처리한다.

## Directory와 공백 차이 비교

```shell
diff -ru old-directory new-directory
diff -u -w old.txt new.txt
```

`-r`은 하위 Directory를 재귀 비교한다. `-w`는 모든 공백 차이를 무시하므로 들여쓰기가 의미 있는 YAML이나 Python에는 함부로 사용하지 않는다. 줄 끝 CRLF 문제는 `file`, `xxd`나 `sed -n l`로 먼저 확인한다.

## Patch 적용 전 검증

```shell
patch --dry-run < config.patch
patch < config.patch
```

항상 작업 Tree가 깨끗한지 확인하고 Dry Run 뒤 적용한다. Git이 관리하는 File이라면 `git diff`, `git apply --check`, `git apply`가 경로와 Index 상태를 다루기 편하다.

## Clipboard로 복사하기

```shell
# macOS
pbcopy < config.patch

# Linux Desktop 환경의 예
xclip -selection clipboard < config.patch
```

Clipboard는 민감한 설정과 Secret을 다른 Application에 노출할 수 있다. Password와 Token이 포함된 Diff는 복사·공유 전에 반드시 제거한다.


# Reference
[GNU diffutils Manual](https://www.gnu.org/software/diffutils/manual/diffutils.html)
