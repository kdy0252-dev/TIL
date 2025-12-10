---
id: Java Spring AOP
started: 2025-05-13
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# Java Spring AOP
## Java Spring AOP란?
Spring AOP(Aspect Oriented Programming)는 관점 지향 프로그래밍이라고 불린다.
어떤 로직에 대해서 핵심적인 관점, 부가적인 관점으로 나누어서 보고 그 관점을 기준으로 각각 모듈화 하겠다는 것이다.

말은 어렵게 했지만 결국 핵심 로직을 실행하기 이전과 이후에 이때 소스코드상에서 다른 부분에서 계속 반복되는 공통 로직을 실행시키고 싶거나 핵심 로직과는 관계없는 로직을 AOP를 통해서 실행시킴으로써 핵심 로직(비즈니스 로직)을 분리하고 싶다는 소리이다.

예를 들면, 메소드에 진입하거나 나가거나 하는 Trace Log를 찍거나 DB에 접근하기 이전에 Distribution Lock을 얻거나 릴리즈하거나와 같은 로직들을 AOP를 통해서 손쉽게 적용 시킬 수 있다.
[[Distribution Lock 예시]]

> [!Info] AOP는 Spring Bean으로 등록된 객체에 대해서만 수행 할 수 있다.
> AOP는 Bean의 프록시 객체에 적용되는 것이므로 Spring Bean에만 적용이 가능하다.
> 또한 모든 AOP 기능을 제공하는 것이 아니라 중복코드, 프록시 클래스 작성의 번거로움, 객체들 간 관계 복잡도 증가 등의 해결책을 지원하는 것이 목적이다.
## AOP의 주요 개념
### Aspect 
흩어진 관심사를 모듈화 한 것이 Aspect이다. 즉 핵심 로직에 붙힐 로직 자체를 Aspect라고 한다.
### Target
Aspect를 적용시킬 핵심 로직을 Target이라고하며 Class 전체가 될 수도 있고 특정 Method가 될 수도 있다.
### Advice
실질적으로 어떤 일을 해야할 지에 대한 것을 Advice라고 한다. 흩어진 관심사의 실질적인 로직이 여기에 해당한다.
### JoinPoint
advice가 적용될 위치, 끼어들 수 있는 지점이다.
예를들어 메소드 진입 지점, 생성자 호출 지점, 필드의 값을 Get할때 Set할때 등등 다양한 시점에 적용 시킬 수 있는데 이 진입 시점을 JoinPoint라고 한다.
### PointCut
JoinPoint의 상세한 스펙을 정의한 것. JoinPoint는 적용되는 메소드에 해당되는 것이고 PointCut은 Aspect가 적용될 구체적인 지점이다. 즉 Advice가 실행될 지점을 PointCut으로 정할 수 있다.

## AOP를 사용하는 방법
### 의존성 추가
build.gradle.kts 파일에 아래와 같이 의존성을 추가한다.
```java title="AOP의존성을 build.gradle.kts에 적용하는 예시"
implementation("org.springframework.boot:spring-boot-starter-aop")
```
### Aspect 작성
```Java title="Aspect 예시"
@Aspect  
@Component  
public class PerfAspect {  
	@Around("execution(* com.dykim..*.EventService.*(..))")  
	public Object logPerf(ProceedingJoinPoint pjp) throws Throwable{  
		long begin = System.currentTimeMillis();  
		Object retVal = pjp.proceed(); // 메서드 호출 자체를 감쌈  
		System.out.println(System.currentTimeMillis() - begin);  
		return retVal;  
	}  
}
```

**@Around** 어노테이션은 타겟 Method를 감싸서 Aspect를 실행시키겠다는 의미이다.
Around 어노테이션의 Parameter인 execution(\* com.dykim..\*.EventService.\*(..))의 의미는 com.dykim 패키지 하위의 경로의 EventService 객체의 모든 메소드에 Aspect를 적용시키겠다는 의미이다.

위와 같이 특정 객체를 타겟으로 할 수도 있지만 어노테이션을 타겟으로 사용 할 수도 있다.
```java title="Around로 어노테이션을 타겟"
@Around("@annotation(PerLogging)")
```

모든 스프링 Bean에도 적용 시킬 수 있다.
```Java title="모든 Spring bean에 적용"
@Around("bean(simpleEventService)")  
```
#### Around 이외에 Aspect 실행 시점을 지정 할 수 있는 어노테이션
**@Before** (이전) : 어드바이스 타겟 메소드가 호출되기 전에 어드바이스 기능을 수행
**@After** (이후) : 타겟 메소드의 결과에 관계없이(즉 성공, 예외 관계없이) 타겟 메소드가 완료 되면 어드바이스 기능을 수행
**@AfterReturning** (정상적 반환 이후)타겟 메소드가 성공적으로 결과값을 반환 후에 어드바이스 기능을 수행
**@AfterThrowing** (예외 발생 이후) : 타겟 메소드가 수행 중 예외를 던지게 되면 어드바이스 기능을 수행
**@Around** (메소드 실행 전후) : 어드바이스가 타겟 메소드를 감싸서 타겟 메소드 호출전과 후에 어드바이스 기능을 수행
### PointCut 표현식
```java title="PointCut 예시"
@Pointcut("execution(* transfer(..))") // 포인트컷 표현식
private void anyOldTransfer() {} // 포인트컷 서명
```

```java title="pointCut 지시자를 And, or, not(&&, ||, !)를 사용한 결합 예시"
// (1)
@Pointcut("execution(public * *(..))")
private void anyPublicOperation() {} // (1)

// (2)
@Pointcut("within(com.xyz.myapp.trading..*)")
private void inTrading() {} // (2)

// (3)
@Pointcut("anyPublicOperation() && inTrading()")
private void tradingOperation() {} // (3)
```
#### 포인트컷 지시자 종류
**execution** : 메서드 실행 조인 포인트를 매칭 한다. 스프링 AOP에서 가장 많이 사용하며, 기능도 복잡하다.
**within** : 특정 타입 내의 조인 포인트를 매칭한다.
**args** : 인자가 주어진 타입의 인스턴스인 조인 포인트
**this** : 스프링 빈 객체(스프링 AOP 프록시)를 대상으로 하는 조인 포인트
**target** : Target 객체(스프링 AOP 프록시가 가리키는 실제 대상)를 대상으로 하는 조인 포인트
**@target** : 실행 객체의 클래스에 주어진 타입의 어노테이션이 있는 조인 포인트
**@within** : 주어진 어노테이션이 있는 타입 내 조인 포인트
**@annotation** : 메서드가 주어진 어노테이션을 가지고 있는 조인 포인트를 매칭
**@args** : 전달된 실제 인수의 런타임 타입이 주어진 타입의 어노테이션을 갖는 조인 포인트
**bean** : 스프링 전용 포인트컷 지시자로 빈의 이름으로 포인트컷을 지정한다.

```java title="표현식 예시"
// 모든 공개 메서드 실행
execution(public * *(..))
// set 다음 이름으로 시작하는 모든 메서드 실행
execution(* set*(..))
// AccountService 인터페이스에 의해 정의된 모든 메서드의 실행
execution(* com.xyz.service.AccountService.*(..))
// service 패키지에 정의된 메서드 실행
execution(* com.xyz.service.*.*(..))
// 서비스 패키지 또는 해당 하위 패키지 중 하나에 정의된 메서드 실행
execution(* com.xyz.service..*.*(..))
// 서비스 패키지 내의 모든 조인 포인트
within(com.xyz.service.*)
// 서비스 패키지 또는 하위 패키지 중 하나 내의 모든 조인 포인트
within(com.xyz.service..*)
// AccountService 프록시가 인터페이스를 구현하는 모든 조인 포인트
this(com.xyz.service.AccountService)
// AccountService 대상 객체가 인터페이스를 구현하는 모든 조인 포인트
target(com.xyz.service.AccountService)
// 단일 매개변수를 사용하고 런타임에 전달된 인수가 Serializable과 같은 모든 조인 포인트
args(java.io.Serializable)
// 대상 객체에 @Transactional 애너테이션이 있는 모든 조인 포인트
@target(org.springframework.transaction.annotation.Transactional)
// 실행 메서드에 @Transactional 애너테이션이 있는 조인 포인트
@annotation(org.springframework.transaction.annotation.Transactional)
// 단일 매개 변수를 사용하고 전달된 인수의 런타임 유형이 @Classified 애너테이션을 갖는 조인 포인트
@args(com.xyz.security.Classified)
// tradeService 라는 이름을 가진 스프링 빈의 모든 조인 포인트
bean(tradeService)
// 와일드 표현식 *Service 라는 이름을 가진 스프링 빈의 모든 조인 포인트
bean(*Service)
```

# Reference
[Spring AOP](https://engkimbs.tistory.com/entry/%EC%8A%A4%ED%94%84%EB%A7%81AOP)
[Spring AOP PointCut 표현식](https://ittrue.tistory.com/233)