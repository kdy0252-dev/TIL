---
id: xxd 사용법
started: 2025-04-03
tags:
  - ✅DONE
group: "[[Linux]]"
---
# xxd 사용법

## 헥사값만 출력하고 싶을때
```shell title="hex 값만 출력하고 싶을때."
xxd -p <File Path> | tr -d '\n'
혹은
xxd -p -c 9999999999999 <File Path>
```

# Reference