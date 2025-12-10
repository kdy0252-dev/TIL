---
id: Gradle 동작 원리
started: 2025-05-08
tags:
  - ✅DONE
group:
  - "[[Java Third-Party]]"
---
# Gradle 동작 원리
## build.gradle은 무엇인가?
build.gradle은 Gradle 프로젝트의 설정 파일입니다. 이 파일은 프로젝트를 어떻게 빌드할지 정의하며, Groovy 또는 Kotlin DSL로 작성됩니다. Gradle은 이 파일을 읽어 프로젝트를 빌드, 테스트, 배포하는 방법을 이해합니다. 처음 Gradle을 접하는 분들을 위해, build.gradle이 어떻게 동작하는지 자세히 설명하겠습니다.

build.gradle은 파일 자체가 Project 객체입니다. 여기서 Project 객체는 프로젝트와 관련된 모든 정보와 작업을 담고 있는 핵심 객체입니다. Project 인터페이스는 다음과 같습니다.
```java
public interface Project extends Comparable<Project>, ExtensionAware, PluginAware {
    
    ..
}
```
build.gradle에 작성하는 수많은 코드는 모두 Project 객체의 프로퍼티와 메서드를 설정하는 것입니다. Project 객체는 프로젝트 이름, 버전, 의존성, 빌드 작업 등 모든 것을 포함하는 슈퍼 객체입니다.
Project 객체는 내부에 수많은 메서드(Methods)와 속성(Properties)을 가지고 있습니다. 메서드 중에 대표적인 것은 모든 java application용 build.gradle이 가진 plugins, repositories, dependencies, application 메서드입니다. 우리가 Gradle Task를 이용해 java application을 빌드하게 되면 build task는 이 메서드들을 수행합니다.

![[Pasted image 20250530154835.png]]

[그림1]의 {}로 감싸여진 부분은 메서드의 인자로 받아지는 Groovy의 클로저(Closure)인데, Groovy의 클로저는 Java나 Kotlin의 람다와 같습니다. 따라서 {} 블록 내부의 메서드들은 [그림2]와 같이 메서드의 인자로 넘겨질 수도 있습니다. 클로저를 사용하면 코드를 더 간결하고 유연하게 만들 수 있습니다.

![[Pasted image 20250530154849.png]]
즉 [그림1]의 코드와 [그림2]의 코드는 같은 코드입니다.
## build.gradle의 프로퍼티
build.gradle에는 Project 객체를 위한 프로퍼티를 정의할 수 있습니다. 프로퍼티는 프로젝트의 다양한 설정을 담고 있습니다.
### 프로퍼티 재정의하기
프로퍼티를 재정의하는 것은 프로젝트 설정을 변경하는 가장 기본적인 방법입니다. 예를 들어, 프로젝트의 버전을 변경하거나, 특정 라이브러리의 버전을 지정할 수 있습니다.
프로퍼티를 정의하는 방법은 간단합니다. 다음 문법을 사용하면 됩니다.
```java
project.[프로퍼티명] = [값]
```

혹은 project를 생략하고 쓸 수도 있습니다.
```java
[프로퍼티명] = [값]
```
예를 들어 Project 객체의 group을 재정의하고 싶다면 다음과 같이 쓰면 됩니다. group으로 쓰든, project.group으로 쓰든 같은 프로퍼티에 접근됩니다.

```java
group = 'com.example'
project.group = "com.kotlinworld"

repositories {
   println group // 출력 com.kotlinworld
   mavenCentral()
}
```
하지만 이렇게 지정하는 것은 Project 객체에 미리 정의된 프로퍼티만 정의하는 것이 가능합니다. 커스텀 프로퍼티를 만들려면 다른 방법을 써야 합니다.
### 커스텀 프로퍼티 만들기
커스텀 프로퍼티를 사용하면 프로젝트에서 필요한 임의의 값을 저장하고 사용할 수 있습니다. 예를 들어, API 키나 빌드 버전을 저장할 수 있습니다.

커스텀 프로퍼티를 만들기 위해서는 project 객체의 extension에 넣는 방식을 사용합니다. project.ext를 통해 extension에 접근합니다.
```java
project.ext.[커스텀 프로퍼티명] = [값]
```

project.ext에 넣어진 변수는 Groovy의 특수한 문법을 사용해 project 객체에서 직접 접근이 가능합니다. 
```java
project.[커스텀 변수명]
```

예를 들어 blogName이란 커스텀 프로퍼티를 설정한 다음 출력하기 위해서는 다음과 같이 사용할 수 있습니다.
```gradle
project.ext.blogName = 'kotlin world'

repositories {
   println project.blogName // 출력 kotlin world
   mavenCentral()
}
```
## build.gradle의 메서드
build.gradle에는 Project 객체를 위한 메서드를 정의할 수 있습니다. 대표적인 메서드들은 바로 build.gradle의 respositories 메서드와 dependencies 메서드입니다. 
```dts
repositories {
    mavenCentral()
}

dependencies {
    testImplementation "junit:junit:4.13.2"
    implementation "com.google.guava:guava:30.1.1-jre"
}
```
이 메서드들은 build.gradle 속에 메서드로 존재합니다. 이 내부에 들어가는 Closure(Lambda 식)은 프로젝트가 빌드될 때 해당 메서드를 수행하는 task에 의해 수행됩니다.

![](https://blog.kakaocdn.net/dn/0QSer/btrsc1kjRI3/KCJkVDWAyMu90gKdTPd9P0/img.png)
위의 그림3은 repositories와 dependencies를 나타냅니다.
위의 메서드들은 미리 빌드된 메서드들입니다. 커스텀 메서드를 만들기 위해서는 메서드를 별도로 정의해야 합니다.
### 커스텀 메서드 만들기
커스텀 메서드를 사용하면 프로젝트에서 반복적으로 사용되는 작업을 캡슐화할 수 있습니다. 예를 들어, 특정 파일들을 복사하거나, 코드를 생성하는 작업을 자동화할 수 있습니다.
Groovy의 Lambda식인 Closure와 Gradle의 ext를 활용해 커스텀 메서드를 손쉽게 만들 수 있습니다.
```java
ext.[메서드명] = { param1, param2 ->
    [메서드 바디]
}

project.ext.[메서드명] = { param1, param2 ->
    [메서드 바디]
}
```

예를 들어 blogName을 출력하는 커스텀 메서드를 만들고 싶다면 다음과 같이 작성하면 됩니다.
```cmake
project.ext.getBlogName {
    return project.blogName
}
```
## Gradle 빌드 단계 추가하기
Gradle은 build, bootJar와 같은 기본 빌드 단계를 제공하지만, 필요에 따라 커스텀 빌드 단계를 추가할 수 있습니다.
### Task 정의하기
Task를 정의하는 가장 기본적인 방법은 `task` 키워드를 사용하는 것입니다.

```gradle
task [task이름] {
    // task 내용
}
```

예를 들어, "hello"라는 이름의 task를 만들고, 실행 시 "Hello, Gradle!"을 출력하도록 하려면 다음과 같이 작성합니다.
```gradle
task hello {
    doLast {
        println "Hello, Gradle!"
    }
}
```

### Task 실행하기
터미널에서 다음 명령어를 실행하여 task를 실행할 수 있습니다.
```bash
./gradlew hello
```

### Task 의존성 설정하기
Task는 다른 Task에 의존하도록 설정할 수 있습니다. 예를 들어, "hello" task가 "build" task 이후에 실행되도록 하려면 다음과 같이 작성합니다.

```gradle
hello.dependsOn build
```
이제 "hello" task를 실행하면 "build" task가 먼저 실행된 후 "hello" task가 실행됩니다.

### Task 입력 및 출력 정의하기
Task는 입력 및 출력을 정의하여 Task의 실행 결과를 캐싱하고, 빌드 속도를 향상시킬 수 있습니다.

```gradle
task processFile {
    inputs.file 'input.txt'
    outputs.file 'output.txt'
    
    doLast {
        // 파일 처리 로직
    }
}
```

다음은 파일을 복사하는 간단한 커스텀 Task 예제입니다.
```gradle
task copyFile {
    inputs.file 'source.txt'
    outputs.file 'destination.txt'

    doLast {
        copy {
            from inputs.files
            into outputs.files.parentFile
        }
    }
}
```
이 Task는 source.txt 파일을 destination.txt 파일로 복사합니다.

### 특정 조건의 테스트만 실행하는 Task 추가하기
#### 특정 어노테이션이 붙은 테스트만 실행
다음은 `@FastTest` 어노테이션이 붙은 테스트만 실행하는 Task 예제입니다.

```gradle
task fastTest(type: Test) {
    useJUnitPlatform {
        includeTags 'FastTest'
    }
}
```
이 Task는 JUnit Platform을 사용하여 `@FastTest` 태그가 붙은 테스트만 실행합니다.

#### 특정 프로파일의 테스트만 실행
다음은 특정 프로파일 (예: "integration")이 활성화된 경우에만 테스트를 실행하는 Task 예제입니다.

```gradle
task integrationTest(type: Test) {
    systemProperty "spring.profiles.active", "integration"
    include "**/*IntegrationTest.class"
}
```

이 Task는 `spring.profiles.active` 시스템 속성을 "integration"으로 설정하고, `*IntegrationTest.class` 패턴에 맞는 테스트 클래스만 포함합니다.
# Reference
https://kotlinworld.com/321