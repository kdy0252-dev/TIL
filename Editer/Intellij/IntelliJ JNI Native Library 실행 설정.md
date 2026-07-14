---
id: IntelliJ JNI Native Library 실행 설정
started: 2026-05-11
tags:
  - ✅DONE
  - IntelliJ
  - Java
  - JNI
group:
  - "[[Editer]]"
---
# IntelliJ에서 JNI Native Library 실행 경로 설정하기

## 1. Java가 Native Library를 찾는 과정

JNI 또는 JNA를 사용하는 Java Application은 `.so`, `.dylib`, `.dll` 같은 Native Library를 Process에 Load한다. Java Classpath에 JAR가 있어도 OS Native Library의 위치를 찾지 못하면 다음과 같은 오류가 발생한다.

```text
java.lang.UnsatisfiedLinkError: no <library> in java.library.path
```

`java.library.path`는 JVM이 Native Library를 검색할 Directory 목록이다. Library 파일 자체가 아니라 파일이 들어 있는 Directory를 지정한다.

## 2. IntelliJ Run Configuration

**Run → Edit Configurations**에서 대상 Application을 선택하고 **Modify options → Add VM options**를 활성화한다. VM options에 다음 형식으로 입력한다.

```text
-Djava.library.path=$ProjectFileDir$/native/build/lib
```

![[IntelliJ JNI Native Library 실행 설정 - 01.png]]

`$ProjectFileDir$` Macro를 사용하면 Repository의 절대 경로를 개인 PC마다 다르게 적지 않아도 된다. Path에 공백이 있다면 전체 값을 따옴표로 감싼다.

```text
-Djava.library.path="$ProjectFileDir$/native build/lib"
```

## 3. VM Option과 Program Argument의 차이

`-Djava.library.path=...`는 JVM System Property이므로 Main Class보다 앞에서 JVM에 전달되어야 한다. Program arguments에 넣으면 Application 문자열 인자로 전달될 뿐 Native Library 검색 경로는 바뀌지 않는다.

```text
VM options       : -Djava.library.path=...
Program arguments: --spring.profiles.active=local
Environment      : 운영체제 환경 변수
```

Spring Profile은 IntelliJ의 Active profiles나 `-Dspring.profiles.active=local`로 별도 설정한다.

## 4. 파일 이름 규칙

`System.loadLibrary("crypto")`를 호출하면 OS별 규칙에 따라 실제 파일명을 해석한다.

| OS | 일반적인 파일명 |
|---|---|
| Linux | `libcrypto.so` |
| macOS | `libcrypto.dylib` |
| Windows | `crypto.dll` |

`System.load()`는 절대 파일 경로를 받고 `System.loadLibrary()`는 Library 이름과 검색 경로를 사용한다. 두 API를 혼동하면 경로가 맞아도 Load에 실패할 수 있다.

## 5. Architecture와 의존 Library

파일이 존재하는데 `UnsatisfiedLinkError`가 발생한다면 CPU Architecture와 하위 의존성을 확인한다. ARM64 JVM에서 x86_64 Library를 Load할 수 없으며, 대상 Library가 의존하는 다른 Native Library가 없을 때도 비슷한 오류가 난다.

```shell
# macOS
file libcrypto.dylib
otool -L libcrypto.dylib

# Linux
file libcrypto.so
ldd libcrypto.so
```

JDK Architecture, C/C++ Build Architecture와 Library Architecture가 모두 일치해야 한다.

## 6. Gradle Test와 IntelliJ 실행의 차이

IntelliJ Application Configuration에 설정한 VM Option은 Gradle Test JVM에 자동 전달되지 않는다. Test에도 Native Library가 필요하면 Build Script에서 Test Task의 System Property를 설정한다.

```groovy
test {
    systemProperty "java.library.path", file("native/build/lib").absolutePath
}
```

CI에서도 동일 Directory에 Library를 Build하거나 Artifact로 받아야 한다. IDE에서만 동작하는 설정을 성공 기준으로 삼지 않는다.

## 7. 디버깅 순서

1. `System.getProperty("java.library.path")`로 실제 JVM 값을 확인한다.
2. 대상 Directory와 Library 파일의 존재·권한을 확인한다.
3. `System.loadLibrary()`의 이름과 실제 파일명 규칙을 대조한다.
4. JVM과 Native Library Architecture를 비교한다.
5. 하위 Native Dependency가 모두 해석되는지 확인한다.
6. IntelliJ, Gradle과 CI가 같은 설정을 사용하는지 비교한다.

## 8. 기억할 점

Native Library 오류는 Java Classpath 문제와 별개다. JVM 검색 경로, OS 파일명 규칙, CPU Architecture와 하위 Native Dependency라는 네 경계를 차례로 확인하면 원인을 빠르게 좁힐 수 있다.

# Reference
- [IntelliJ IDEA Run/Debug Configurations](https://www.jetbrains.com/help/idea/run-debug-configuration.html)
- [Java System.loadLibrary](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html#loadLibrary(java.lang.String))
