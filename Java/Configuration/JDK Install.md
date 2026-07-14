---
id: JDK Install
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Java Configration]]"
---
# JDK Install

JDK는 Java Compiler, Runtime과 진단 도구를 포함한다. JRE만으로는 `javac`, `jlink`, `jcmd` 같은 개발·운영 도구를 사용할 수 없다. 설치 전 Project의 Toolchain Version, CPU Architecture와 배포 환경 Vendor 정책을 먼저 확인한다.

### Homebrew 설치 및 업데이트  
`brew update`
### 설치 가능한 JDK 확인  
`brew search jdk`
### 원하는 버전 설치  
`brew install --cask temurin@21`

현재 Homebrew에서는 별도로 `brew install cask`를 실행하지 않는다. Cask Package는 `--cask` Option으로 설치한다.
### 설치된 위치 확인  
`/usr/libexec/java_home -V`
### 버전 확인  
`java --version`
### 자바 버전 변경  
여러 버전을 설치한 경우 최신 버전을 기본값으로 하기 때문에 원하는 버전으로 변경하기 위해서는 추가적인 설정이 필요하다.
자신이 사용하고 있는 쉘 종류에 따라 스크립트를 수정해야 한다.
내가 사용중인 쉘이 무엇인지 확인하고 수정하는 과정은 아래와 같다.
### 쉘 확인  
`echo $SHELL`
### 쉘 스트크립트 수정  
zsh : `vi ~/.zshrc`  
bash : `vi ~/.bash_profile`
### java 14, 21 버전을 변수로 만들어두고 21버전을 사용하도록 설정
```shell title="JAVA_HOME Setting"
# Java Paths
export JAVA_HOME_14=$(/usr/libexec/java_home -v14)
export JAVA_HOME_21=$(/usr/libexec/java_home -v 21)
# Java 21
export JAVA_HOME=$JAVA_HOME_21
# Java 14
# 14버전을 사용하려면 아래 줄을 활성화하고 21 설정을 비활성화한다.
# export JAVA_HOME=$JAVA_HOME_14
```
### 변경사항 반영  
zsh: `source ~/.zshrc`  
bash: `source ~/.bash_profile`

`JAVA_HOME`은 JDK Root를 가리키고 실행 File은 `$JAVA_HOME/bin` 아래에 있다. Shell이 다른 Java를 먼저 찾지 않도록 Path를 확인한다.

```shell
export PATH="$JAVA_HOME/bin:$PATH"

which java
java --version
javac --version
echo "$JAVA_HOME"
```

IDE, Gradle Daemon과 Terminal은 서로 다른 JDK를 사용할 수 있다. IntelliJ Project SDK, Gradle JVM, `./gradlew --version`을 함께 확인한다.

## Project별 Version은 Toolchain으로 고정하기

개인 Shell의 기본 Java에만 의존하면 CI와 다른 개발자 환경에서 Build가 달라질 수 있다.

```kotlin title="build.gradle.kts"
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

Gradle Toolchain은 Project가 요구하는 Java Version을 Build 설정에 기록한다. Runtime Image와 CI도 같은 Major Version을 사용하고, Patch Update는 보안 정책에 따라 지속적으로 적용한다.

## 여러 Version 전환

단순한 두 Version은 `/usr/libexec/java_home`으로 충분하다. Project 수가 많다면 SDKMAN이나 asdf 같은 Version Manager를 사용할 수 있지만, 팀에서는 한 가지 방식을 정하고 Shell 설정과 Build Toolchain의 책임을 혼동하지 않는다.

# Reference
[Eclipse Temurin Installation](https://adoptium.net/installation/)
[Gradle - Java Toolchains](https://docs.gradle.org/current/userguide/toolchains.html)
[Homebrew Cask](https://docs.brew.sh/Cask-Cookbook)
