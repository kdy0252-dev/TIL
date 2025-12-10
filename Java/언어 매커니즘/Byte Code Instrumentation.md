---
id: Byte Code Instrumentation
started: 2025-07-09
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Byte Code Instrumentation (BCI)

## 1. 개요 (Overview)
**Byte Code Instrumentation (BCI)**은 Java 프로그램이 실행되는 동안(Runtime) 또는 클래스가 로딩되는 시점(Load-time)에 **바이트코드(.class)를 동적으로 수정**하여 애플리케이션의 동작을 변경하거나 모니터링 코드를 삽입하는 기술입니다.

소스 코드를 수정하지 않고도 로그를 찍거나, 성능을 측정하거나, 보안 검사를 수행할 수 있어 **APM (Application Performance Monitoring - 예: Jennifer, Scouter, New Relic, Pinpoint)** 도구와 **프로파일러**, **Spring AOP (Load-time weaving)** 등의 핵심 기반 기술로 사용됩니다.

---

## 2. 핵심 메커니즘 (Java Agent)

Java에서는 `java.lang.instrument` 패키지를 통해 BCI를 위한 표준 방법을 제공하며, 이를 **Java Agent**라고 합니다.

### 2.1 동작 시점
1.  **정적 로딩 (Static Load - `-javaagent`)**:
    - JVM 시작 시점에 에이전트를 함께 로딩합니다.
    - `premain()` 메서드가 `main()` 메서드보다 먼저 실행됩니다.
    - 주로 클래스 로딩 시점에 바이트코드를 변조(Transform)할 때 사용합니다.
2.  **동적 로딩 (Dynamic Load - Attach API)**:
    - 이미 실행 중인 JVM에 에이전트를 침투(Attach)시킵니다.
    - `agentmain()` 메서드가 실행됩니다.
    - 실행 중인 클래스를 재정의(Redefine)하거나 재변환(Retransform)할 수 있습니다.

### 2.2 ClassFileTransformer
에이전트는 `ClassFileTransformer` 인터페이스를 구현하여 리지스터에 등록합니다. JVM은 클래스를 로딩할 때마다 등록된 변환기(Transformer)에게 바이트코드 배열(`byte[]`)을 던져주고, 변환기는 이를 입맛에 맞게 수정한 뒤 다시 JVM에게 돌려줍니다.

---

## 3. 바이트코드 조작 라이브러리
raw 바이트코드(Opcode)를 직접 수정하는 것은 어셈블리어를 짜는 것만큼 어렵기 때문에, 이를 추상화한 라이브러리를 사용합니다.

1.  **ASM**: 가장 로우 레벨이고 가장 빠릅니다. Spring, Hibernate, JDK 내부 등에서 널리 쓰입니다. Visitor 패턴 기반이라 배우기 어렵습니다.
2.  **Javassist**: 소스 코드 레벨의 문자열(예: `"System.out.println(...)"`)을 바이트코드로 컴파일해줍니다. 쉽지만 최신 Java 문법 지원이 느립니다.
3.  **Byte Buddy**: 현재 가장 인기 있는 라이브러리입니다. (Mockito, Hibernate, Pinpoint 등 사용). 유려한 API(Fluent API)를 제공하며 성능과 편의성 모두 잡았습니다.

---

## 4. 구현 예제: 메서드 실행 시간 측정 에이전트 (with Byte Buddy)

소스 코드 수정 없이, 특정 메서드가 얼마나 걸리는지 측정하는 Java Agent를 만들어보겠습니다.

### 4.1 의존성 (Gradle)
```groovy
dependencies {
    implementation 'net.bytebuddy:byte-buddy:1.14.0'
}
jar {
    manifest {
        attributes(
            'Premain-Class': 'com.example.agent.MyAgent',
            'Can-Redefine-Classes': 'true',
            'Can-Retransform-Classes': 'true'
        )
    }
}
```

### 4.2 Agent Entry Point (`premain`)
```java
package com.example.agent;

import net.bytebuddy.agent.builder.AgentBuilder;
import net.bytebuddy.implementation.MethodDelegation;
import net.bytebuddy.matcher.ElementMatchers;

import java.lang.instrument.Instrumentation;

public class MyAgent {
    public static void premain(String agentArgs, Instrumentation inst) {
        System.out.println("[MyAgent] Agent started!");

        new AgentBuilder.Default()
            // 1. 대상 선정: com.example.app 패키지 하위의 모든 클래스
            .type(ElementMatchers.nameStartsWith("com.example.app")) 
            .transform((builder, typeDescription, classLoader, module, protectionDomain) -> 
                builder.method(ElementMatchers.any()) // 모든 메서드에 대해
                       .intercept(MethodDelegation.to(TimingInterceptor.class)) // 인터셉터 위임
            )
            .installOn(inst);
    }
}
```

### 4.3 Interceptor (Advice)
실제 바이트코드에 삽입될 로직입니다.

```java
import net.bytebuddy.implementation.bind.annotation.Origin;
import net.bytebuddy.implementation.bind.annotation.RuntimeType;
import net.bytebuddy.implementation.bind.annotation.SuperCall;

import java.lang.reflect.Method;
import java.util.concurrent.Callable;

public class TimingInterceptor {
    @RuntimeType
    public static Object intercept(@Origin Method method, @SuperCall Callable<?> callable) throws Exception {
        long start = System.currentTimeMillis();
        try {
            return callable.call(); // 원본 메서드 실행
        } finally {
            System.out.println(method.getName() + " took " + (System.currentTimeMillis() - start) + "ms");
        }
    }
}
```

4. **실행 (VM Option)**
```bash
java -javaagent:my-agent.jar -jar my-app.jar
```

## 5. 주의사항 (Considerations)
- **성능 오버헤드**: 모든 메서드에 인터셉터를 걸면 성능 저하가 심각하므로, 특정 패키지나 클래스로 범위를 제한해야 합니다.
- **디버깅 어려움**: 코드가 런타임에 변하므로 스택 트레이스와 소스 코드가 일치하지 않을 수 있습니다.
- **클래스 로더 문제**: 에이전트가 사용하는 라이브러리와 애플리케이션 라이브러리 버전 충돌에 주의해야 합니다.

# Reference
https://d2.naver.com/helloworld/1113548