---
id: JDK Install
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Java Configration]]"
---
# JDK Install
### Homebrew 설치 및 업데이트  
`brew update`
### cask를 설치  
`brew install cask`
### 설치 가능한 JDK 확인  
`brew search jdk`
### 원하는 버전 설치  
`brew install --cask temurin@21`
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
export JAVA_HOME_21=$(/usr/libexec/java_home -v 21.0.3)
# Java 21
export JAVA_HOME=$JAVA_HOME_21
# Java 14
# 14버전을 사용하고자 하는 경우 아래 주석(#)을 해제하고 위에 11버전을 주석처리 하면된다.
# export JAVA_HOME=$JAVA_HOME_14
```
### 변경사항 반영  
zsh: `source ~/.zshrc`  
bash: `source ~/.bash_profile`

# Reference