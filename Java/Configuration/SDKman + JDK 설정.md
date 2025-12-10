---
id: SDKman + JDK 설정
started: 2025-05-14
tags:
  - ✅DONE
group:
  - "[[Java Configration]]"
---
# SDKman + JDK 설정
## SDKMAN 설치 및 사용 방법
### SDK 설치
[SDKMAN](https://sdkman.io/install "https://sdkman.io/install")을 참조하여 설치를 진행한다.  
`$ curl -s "https://get.sdkman.io" | bash`
### 설치 가능한 JDK 버전 검색
`$ sdk list java`
### JDK 설치
식별자(Identifier) 값을 선택하여 설치 한다.  
`$ sdk install java [Identifier]`
### 설치된 Java 버전 변경
현재 사용하고 있는 버전을 `21.0.3-temurin`으로 변경  
`$ sdk use java 21.0.3-temurin`
### 현재 사용 버전 확인
`$ sdk current`

Java 버전이 `21.0.3-temurin`으로 변경된 것을 확인할 수 있다. 하지만, 이 것은 현재 사용하고 있는 쉘의 Java 버전만 변경 되었는 것이다.  
모든 쉘에 동일한 버전을 적용하고 싶다면 `default` 명령을 사용해야 한다.  
`$ sdk default java 21.0.3-temurin`
### 버전 업그레이드
`$ sdk upgrade java`
### JDK 설치 경로 확인
`$ echo $JAVA_HOME /Users/kim-yuseong/.sdkman/candidates/java/21.0.3-tem`

또한. `21.0.3`, `17.0.11`, `11.0.23` 을 설치 했다면 아래와 같이 파일이 위치하게 된다.

```shell title="jdk 설치 경로 확인"
/Users/{user name}/.sdkman/candidates/java/21.0.3-tem
/Users/{user name}/.sdkman/candidates/java/17.0.11-tem
/Users/{user name}/.sdkman/candidates/java/11.0.23-tem
```
## direnv 설치 및 사용 방법
### direnv 설치
- mac OS  
`$ brew install direnv`  
direnv는 주요 리눅스 배포판의 패키지로도 등록되어 있다.

- Ubuntu, Debian  
`$ apt-get install direnv`

- Fedora  
`$ dnf install direnv`
### 쉘 설정 추가
다음으로 자신이 사용하는 셸에 해당하는 내용을 셸의 설정 파일에 추가한다. direnv는 공식적으로 BASH, ZSH, FISH, TCSH, Elvish를 지원한다.
```shell title="add shell config"

BASH -> ~/.bashrc에 아래 내용 추가
eval "$(direnv hook bash)"

ZSH -> ~/.zshrc에 아래 내용 추가
eval "$(direnv hook zsh)"

FISH -> ~/.config/fish/config.fish에 아래 내용 추가
eval (direnv hook fish)

TCSH -> ~/.cshrc에 아래 내용 추가
eval `direnv hook tcsh`

Elvish -> 아래 내용 실행
$ direnv hook elvish > ~/.elvish/lib/direnv.elv
~/.elvish/rc.elv에 아래 내용 추가
use direnv
```

### 사용 방법
direnv는 쉘 전체에 적용되는 설정 이외에 현재 디렉토리의 특정한 설정을 추가할 수 있도록 도와주는 도구이다.  
direnv를 통해 특정 디렉토리에 적용되는 설정은 `.envrc`파일에 쉘스크립트로 작성한다.  
다음은 direnv 의 기본적인 사용 예시이다.

먼저 direnv를 사용할 디렉토리를 행성한다.

### 테스트 디렉토리 생성
`$ mkdir direnv`  
`$ cd direnv`

### envrc 파일 생성
`$ touch .envrc`

.envrc 파일이 생성되면 direnv는 이를 감지해 경고 메시지를 출력한다.  
`direnv: error .envrc is blocked. Run` direnv allow `to approve its content.`

`direnv`는 특정 디렉토리에 `.envrc` 파일에 대해 명시적으로 사용을 허가하지 않은 경우 이 파일을 읽지 않는다.  
이는 의도하지 않은 쉘스크립트가 실행되는 것을 방지하기 위함이다. 따라서 `.envrc` 파일을 추가하거나 변경하는 경우 명시적으로 사용을 허가해야 이 파일을 읽는다.
### 설정 읽기 허용

```
$ direnv allow
direnv: loading .envrc
```

.envrc가 바로 로드되는 것을 알 수 있다. 하지만 이 파일에는 아무 내용도 없기 때문에 별다른 메시지가 표시되지 않았다.  
다음을 추가해보자.  
`$ echo 'echo "Hello, direnv"' > .envrc`

다시 허가되지 않은 파일이라는 경고 메시지가 출력된다.  
`direnv: error .envrc is blocked. Run` direnv allow `to approve its content.`

변경된 내용을 허가해 준다.
```
$ direnv allow
direnv: loading .envrc
Hello, direnv
```

`.envrc`에 추가한 내용이 정상적으로 출력되는 것을 확인 할 수 있다.
상위 디렉토리로 이동해 보자.

```
$ cd ..
direnv: unloading
```

.envrc의 내용이 언로딩 된다.
다시 direnv 디렉터리로 이동해서 .envrc의 내용이 적용되는 것을 확인해 보자.

```
$ cd direnv
direnv: loading .envrc
Hello, direnv
```

direnv 디렉터리로 이동하니 다시.envrc에 작성한 내용이 실행되는 것을 확인할 수 있다.  
deny 명령어를 사용하면 허가한 내용을 명시적으로 금지하는 것도 가능하다.

```
$ direnv deny
direnv: error .envrc is blocked. Run `direnv allow` to approve its content
```

direnv에서 allow한 정보는 ~/.config/direnv/allow/에서 관리된다.  
이 디렉터리의 파일은 .envrc의 경로와 내용을 조합으로 sha256sum으로 작성된다.
## SDKMAN 과 direnv 를 통해 특정 디렉토리의 Java 버전 설정
다음은 위 내용을 바탕으로 `SDKMAN`과 `direnv`을 활용해 특정 디렉토리에만 원하는 Java 버전이 적용되도록 설정하는 예시이다.
### 전역적으로 설정된 Java Version
```shell title="General Java Version"
$ java -version
openjdk version "21.0.3" 2024-04-16 LTS
OpenJDK Runtime Environment Temurin-21.0.3+9 (build 21.0.3+9-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.3+9 (build 21.0.3+9-LTS, mixed mode)
```
현재 전역적으로 Java 21 버전이 설정되어 있고, direnv 디렉토리에 Java 17을 적용해 보자.
```shell title="write .envrc file"
$ cd direnv
$ vi .envrc
```
### .envrc 작성
```shell
export JAVA_HOME=$HOME/.sdkman/candidates/java/17.0.11-tem
export PATH=$JAVA_HOME/bin:$PATH
```
### 변경 사항 적용
```shell
$ direnv allow
direnv: loading ~/Documents/Autocrypt/direnv/.envrc
direnv: export ~JAVA_HOME ~PATH
# Java 버전 확인
$ java -version
openjdk version "17.0.11" 2024-04-16
OpenJDK Runtime Environment Temurin-17.0.11+9 (build 17.0.11+9)
OpenJDK 64-Bit Server VM Temurin-17.0.11+9 (build 17.0.11+9, mixed mode)
# 상위 디렉토리에서 Java 버전 확인
$ cd ..
direnv: loading ~/.envrc
$ java -version
openjdk version "21.0.3" 2024-04-16 LTS
OpenJDK Runtime Environment Temurin-21.0.3+9 (build 21.0.3+9-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.3+9 (build 21.0.3+9-LTS, mixed mode)
```
## 다양한 JDK 설치와 사용을 편리하게 하는 도구

|                                                                                    |                      |                                       |
| ---------------------------------------------------------------------------------- | -------------------- | ------------------------------------- |
| **이름**                                                                             | **기능**               | **사용 가능한 OS**                         |
| YUM/APT                                                                            | 범용 패키지 관리 도구         | Linux                                 |
| update-alternatives/alternatives                                                   | 범용 패키지 버전 선택 도구      | Linux                                 |
| Homebrew                                                                           | 범용 패키지 관리 도구         | macOS                                 |
| [Chocolatey](https://chocolatey.org/ "https://chocolatey.org/")                    | 범용 패키지 관리 도구         | Windows                               |
| [SDKMAN](https://sdkman.io/ "https://sdkman.io/")                                  | 범용 패키지 관리 도구         | Linux macOS Windows(Cygwin, Git Bash) |
| [jabba](https://github.com/Jabba-Team/jabba "https://github.com/Jabba-Team/jabba") | JDK 설치 특화 도구         | Linux macOS Windows                   |
| [jEnv](https://www.jenv.be/ "https://www.jenv.be/")                                | JDK 버전 선택 특화 도구      | Linux macOS                           |
| [direnv](https://direnv.net/ "https://direnv.net/")                                | 범용 디렉토리별 환경 변수 관리 도구 | Linux macOS Windows                   |
### SDKMAN  
`SDKMAN`은 JVM에 관련한 다양한 개발 도구를 설치할 수 있는 범용 패키지 관리 도구이다. JDK 외에도 Maven, Gradle, Ant 등의 도구를 설치할 수 있다.  
가장 큰 장점은 다양한 버전을 관리하며, 사용할 버전을 명령어 한 줄로 변경할 수 있다는 점이 있다.  
`Apdot Open JDK`, `Amazone Corretto`, `GraalVM`, `Zulu` 등의 주요 배포판을 거의 모두 포함하고 있는 것이 장점이다.
또한 명령행에서 디폴트로 사용할 JDK 버전은 `~/.sdkman/candidates/java/current`에서 심볼릭 링크로 관리되고, 이 링크가 환경 변수에서 `$PATH`와 `$JAVA_HOME`에 추가된다.
실제 JDK 디렉토리는 `~/.sdkman/candidates/java`에서 관리 되기 때문에 JDK의 경로를 한 곳에서 관리할 수 있는 장점이 있다.
### direnv  
`SDKMAN`은 특정 디렉토리에서 특정 JDK버전을 사용하는 기능을 지원하지 않는다. 해당 기능을 이용하기 위해서 `direnv`라는 디렉토리별 환경 변수 지정 도구를 `SDKMAN`과 병행하여 사용하는 것을 추천한다.  
(`direnv`는 JDK 관리 도구는 아니고 디렉토리별 환경 변수 지정 도구이다. 따라서 JDK 가 아닌 다른 환경 변수도 적용이 가능하다.)

|        |        |              |                |
| ------ | ------ | ------------ | -------------- |
| 이름     | JDK 설치 | 디폴트 버전 지정 기능 | 디렉토리별 버전 지정 기능 |
| SDKMAN | O      | O            | X              |
| jabba  | O      | X            | △              |
| jEnv   | X      | O            | O              |
| direnv | X      | X            | O              |

`jabba`는 디폴트 버전 지정 기능이 존재하지 않는 JDK의 설치와 버전 관리 전용 도구이다.  
디렉토리별 버전 지정 기능을 제공하지만, 해당 디렉토리에서 `$ jabba use` 명령어를 사용해야 환경 변수를 변경해 준다. `jEnv`와 `direnv`는 해당 디렉토리에 접근할 때 자동적으로 환경 변수를 바꿔 준다.
`SDKMAN`과 `jEnv`를 함께 사용하는 것은 적합하지 않다. `$PATH` 환경 변수의 경로 순서에 따라서 JDK 디폴트 버전 지정 결과가 의도한 것과 다르게 변경될 수 있기 떄문이다.
결국 모든 기능을 충돌없이 사용하기 위해서 `SDKMAN`과 `direnv`의 조합을 선택할 수 있다.

# Reference