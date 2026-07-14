---
id: JFR와 async-profiler JVM 성능 진단
started: 2026-06-08
tags:
  - ✅DONE
  - Java
  - JFR
  - Profiling
group:
  - "[[Java]]"
---
# JFR와 async-profiler JVM 성능 진단

## 1. 개요

k6가 “어떤 API가 느린가”를 알려준다면 JDK Flight Recorder(JFR)와 async-profiler는 “JVM과 Native Stack의 어디서 CPU·Memory·대기 시간을 소비하는가”를 찾습니다.

```text
k6 / SLO
  -> 느린 시간 구간 식별
  -> JFR로 JVM Event와 Timeline 분석
  -> async-profiler로 Hot Stack 정밀 분석
  -> 변경
  -> 동일 부하·조건으로 재측정
```

Profile 없이 추측으로 JVM Flag나 Thread Pool을 바꾸지 않습니다.

---

## 2. JFR이 수집하는 것

JFR은 JVM에 내장된 Event Recording Framework입니다.

- CPU Sample과 Thread State
- Allocation과 Object 생존
- GC Pause와 Heap 상태
- Java Monitor·Park·Socket·File I/O
- Class Loading, JIT Compilation, Safepoint
- Virtual Thread Pinning 등 Runtime Event
- 사용자 정의 업무 Event

Event는 Timestamp를 가지므로 k6, Prometheus, Log와 시간축으로 연결할 수 있습니다.

---

## 3. Continuous와 Profile Recording

`default` 설정은 낮은 Overhead로 상시 Recording에 적합하고 `profile`은 짧은 정밀 분석에 적합합니다.

```text
Continuous: 최근 2~6시간 Ring Buffer, 장애 뒤 Dump
Profile:    재현 가능한 짧은 부하 동안 상세 Event 수집
```

상세 Event를 무기한 켜면 Disk와 CPU 비용이 증가합니다. 목적에 맞는 Threshold, Stack Trace와 보존 시간을 선택합니다.

---

## 4. 실행 예시

Application 시작부터 최근 Event를 보존할 수 있습니다.

```bash
java -XX:StartFlightRecording=disk=true,maxage=2h,settings=default \
     -XX:FlightRecorderOptions=repository=/tmp/jfr \
     -jar app.jar
```

실행 중인 JVM에는 `jcmd`를 사용합니다.

```bash
jcmd <pid> JFR.start name=load-test settings=profile duration=5m filename=/tmp/load-test.jfr
jcmd <pid> JFR.check
jcmd <pid> JFR.dump name=load-test filename=/tmp/incident.jfr
```

Container의 `/tmp` 크기와 파일 회수 경로를 사전에 정합니다.

---

## 5. 분석 순서

1. JVM·Host CPU와 부하 시간을 맞춥니다.
2. GC Pause와 Heap Pressure를 봅니다.
3. Hot Method와 Thread State를 확인합니다.
4. Lock·Park·Socket·File I/O 대기를 분리합니다.
5. Allocation Hotspot과 Object 생존을 봅니다.
6. JIT·Safepoint·Class Loading 이상을 확인합니다.
7. 관련 Stack과 Source를 검증합니다.

CPU가 낮으면서 느리면 I/O, Lock, Pool Queue 또는 Downstream 대기를 먼저 의심합니다.

---

## 6. CPU Time과 Wall-clock

CPU Profile은 실제 Core에서 실행한 Stack을 찾습니다. Wall-clock Profile은 CPU 실행뿐 아니라 Sleep, Lock, I/O 대기까지 시간 비율로 보여줍니다.

```text
CPU 높음 + Latency 높음  -> 계산, 직렬화, GC, Spin
CPU 낮음 + Latency 높음  -> I/O, Lock, Queue, Connection Pool
```

두 Profile을 함께 봐야 “느리지만 CPU를 쓰지 않는” 병목을 놓치지 않습니다.

---

## 7. async-profiler

async-profiler는 Safepoint Bias를 줄인 Sampling Profiler로 Java, Native와 Kernel Frame을 함께 볼 수 있습니다.

주요 Event:

- `cpu`: CPU Hotspot
- `wall`: 실행·대기 전체 시간
- `alloc`: Allocation Hotspot
- `lock`: Contended Lock
- Native Allocation과 Cache Miss 등 환경별 Event

```bash
asprof -d 60 -e cpu -f /tmp/cpu.html <pid>
asprof -d 60 -e wall -f /tmp/wall.html <pid>
asprof -d 60 -e alloc -f /tmp/alloc.html <pid>
```

Linux `perf_event`와 Container 권한 제약을 확인합니다. 편의를 위해 Privileged Pod를 상시 운영하지 않습니다.

---

## 8. Flame Graph 읽기

- 가로 폭은 Sample 비율입니다.
- 위쪽은 호출된 Method, 아래쪽은 Caller입니다.
- 높이는 시간이나 비용을 뜻하지 않습니다.
- 넓은 Plateau의 최상단이 실제 Hot Method 후보입니다.
- Library Frame만 보고 원인을 단정하지 말고 호출한 업무 Stack을 추적합니다.

변경 전후 Differential Flame Graph는 늘어난 Stack과 줄어든 Stack을 비교하는 데 유용합니다.

---

## 9. Allocation과 GC

Heap 사용량 하나보다 Allocation Rate와 생존율이 중요합니다.

- 짧은 DTO·Collection의 과도한 생성
- 큰 JSON·Excel Buffer
- Boxing과 문자열 변환
- Cache의 무제한 Key
- ThreadLocal과 ClassLoader Retention

Allocation Hotspot을 줄여도 코드 복잡도가 크게 늘 수 있습니다. 실제 GC Pause와 CPU가 SLO를 소비하는 경우에만 최적화합니다.

---

## 10. Lock과 Virtual Thread

Virtual Thread가 많아도 DB Connection과 `synchronized` 경합은 사라지지 않습니다. JFR의 Pinning, Java Monitor, Thread Park Event와 Hikari Pending Metric을 함께 봅니다.

긴 `synchronized` 안의 I/O, 전역 Cache Lock, 동일 Row DB Lock을 구분합니다. Java Lock Profile만으로 DB Lock을 볼 수 없으므로 PostgreSQL 지표가 필요합니다.

---

## 11. Kubernetes 운영

- Pod별 JFR Repository 크기와 보존 시간을 제한합니다.
- Dump 파일에는 Class·Method·Path 등 내부 정보가 있으므로 접근을 통제합니다.
- OOMKill 뒤 파일을 회수할 수 있도록 EmptyDir와 Sidecar Upload를 검토합니다.
- CPU Limit Throttling을 JVM 병목으로 오해하지 않습니다.
- Pod Restart와 Image Digest를 Recording Metadata에 남깁니다.

Production Profiling은 승인, 시간 제한과 영향 관측을 전제로 합니다.

---

## 12. 사례의 부족한 점과 개선

기존 문서는 JVM 구조와 Profiling 도구를 소개하지만, k6 Run과 JFR Artifact를 자동 연결하는 표준 절차가 부족합니다.

1. k6 Run ID와 Image Digest를 JFR 파일명·Metadata에 넣습니다.
2. Baseline Profile을 동일 데이터와 Resource로 보관합니다.
3. P99 악화 시 JFR Dump를 자동 수집하는 Runbook을 만듭니다.
4. CPU·Wall·Allocation Profile을 순서대로 비교합니다.
5. 개선 PR에 전후 k6와 Differential Profile을 첨부합니다.

---

## 13. 완료 기준

- [ ] 재현 부하와 Production Incident 모두에서 JFR을 안전하게 회수할 수 있습니다.
- [ ] CPU·Wall-clock·Allocation·Lock 차이를 설명할 수 있습니다.
- [ ] Profile 구간이 k6·Metric·Trace 시간과 일치합니다.
- [ ] 병목 판단에 Stack과 Resource Metric 근거가 있습니다.
- [ ] 변경 전후 같은 조건의 Profile과 SLO를 비교합니다.
- [ ] Profiling 권한·Artifact 보존·민감 정보 정책이 있습니다.

---

# Reference

- [Oracle JDK Flight Recorder](https://docs.oracle.com/en/java/javase/25/jfapi/)
- [Oracle Java Diagnostic Tools](https://docs.oracle.com/en/java/javase/25/troubleshoot/diagnostic-tools.html)
- [async-profiler](https://github.com/async-profiler/async-profiler)
- [[k6 부하 테스트와 성능 검증]]
- [[Virtual Thread와 Spring Boot]]
