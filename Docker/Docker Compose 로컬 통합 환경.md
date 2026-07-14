---
id: Docker Compose 로컬 통합 환경
started: 2026-06-10
tags:
  - ✅DONE
  - Docker
  - Testing
group:
  - "[[Docker]]"
---
# Docker Compose를 이용한 로컬 통합 환경

## 1. 개요 (Overview)
**Docker Compose**는 여러 Container, Network, Volume과 Health Check를 하나의 선언 파일로 관리합니다. 애플리케이션 개발에서는 운영 Kubernetes를 그대로 복제하기보다, 통합 테스트에 필요한 의존성을 빠르고 재현 가능하게 구성하는 데 적합합니다.

---

## 2. 실무 사례의 Compose 구조

```text
compose.yml
  ├─ PostgreSQL
  ├─ Redis
  ├─ core-application
  ├─ Gateway
  └─ Metrics

compose-ci.yml
  └─ Newman과 CI Override

compose-observability.yml
  ├─ Prometheus
  ├─ Tempo
  ├─ Grafana
  └─ cAdvisor
```

기본 파일과 관심사별 Override를 분리하면 로컬 개발, CI, 관측성 환경이 동일한 서비스 정의를 재사용할 수 있습니다.

---

## 3. Health Check와 시작 순서

```yaml
services:
  app:
    depends_on:
      postgres:
        condition: service_healthy
```

`depends_on`은 Application이 업무 요청을 처리할 준비까지 완전히 보장하지 않습니다. CI에서는 Actuator Health를 Polling하여 모든 서비스가 준비된 뒤 E2E Test를 시작합니다.

---

## 4. 이미지 일관성
로컬 Source Mount와 CI Image가 다르면 CI에서만 발생하는 문제가 늘어납니다. 이 사례는 Jib로 만든 실제 Image를 Compose에 주입하고, 동일 Image로 Newman Test를 수행한 뒤 ECR에 Push합니다.

```sh
EU_APP_IMAGE="$APP_IMAGE" docker compose \
  -f compose.yml \
  -f compose-ci.yml \
  up --no-build -d
```

---

## 5. 데이터와 격리
- CI마다 고유 Compose Project Name을 사용합니다.
- Test 종료 시 Volume까지 정리하여 이전 실행의 상태가 남지 않게 합니다.
- Local 개발 데이터가 필요하면 명시적인 Named Volume을 사용합니다.
- Port 충돌을 피하려면 Container Network 내부 이름을 우선 사용합니다.
- Secret은 Compose File에 직접 기록하지 않고 Environment 또는 Secret 기능으로 전달합니다.

---

## 6. Kubernetes와 차이
Compose는 Kubernetes의 Scheduling, Readiness Traffic Gate, Rolling Update, RBAC, NetworkPolicy를 재현하지 않습니다. Compose Test가 성공해도 Helm Template 검증과 EKS Smoke Test가 별도로 필요합니다.

---

## 7. Compose Merge 규칙
여러 `-f` 파일은 뒤의 파일이 앞 설정을 Override하거나 일부 List를 병합합니다. 예상과 다른 최종 설정을 막으려면 Render 결과를 확인합니다.

```sh
docker compose \
  -f compose.yml \
  -f compose-ci.yml \
  config
```

환경별 파일에 서비스 전체를 복사하지 않고 달라지는 Port, Environment, Volume과 Command만 둡니다.

## 8. Network
Compose는 Project별 Default Bridge Network와 Service DNS를 제공합니다.

```text
core-gateway -> http://core-app:8080
core-app     -> postgres:5432
```

Container 내부의 `localhost`는 Host나 다른 Container가 아닙니다. Application 설정은 Container DNS 이름을 사용하고, Host 접근이 필요한 경우 Platform별 Gateway를 명시합니다.

## 9. Volume과 초기화
- Named Volume: 실행 간 데이터 유지
- Anonymous Volume: 소유 추적이 어려움
- Bind Mount: Host 파일을 즉시 반영
- tmpfs: 빠르고 종료 시 삭제되는 테스트 데이터

DB 초기화 Script는 빈 Volume에서만 실행될 수 있습니다. Migration 변경을 검증할 때 기존 Volume과 새 Volume 두 Scenario가 모두 필요합니다.

## 10. Profile과 선택적 서비스
Newman, Observability, Migration처럼 항상 필요하지 않은 서비스는 Profile이나 Override File로 분리합니다. 기본 `up`이 너무 많은 Container를 시작하면 개발 Feedback이 느려집니다.

## 11. Health Check 상세
Process 존재가 아니라 실제 준비 상태를 검사합니다. PostgreSQL은 `pg_isready`, Redis는 `redis-cli ping`, Spring은 Readiness Endpoint를 사용할 수 있습니다.

Health Check 자체가 인증이나 의존성 때문에 실패하지 않도록 목적을 단순화합니다. `start_period`, `interval`, `timeout`, `retries`로 Cold Start와 실패 감지 시간을 계산합니다.

## 12. CI 격리

```text
COMPOSE_PROJECT_NAME=sample-job-123
  -> Network sample-job-123_default
  -> Volume sample-job-123_postgres
  -> Container 이름 격리
```

고정 Host Port는 병렬 Job에서 충돌합니다. 가능하면 Container Network 내부에서 Test Runner를 실행합니다.

## 13. 실패 Artifact
CI 실패 시 Cleanup 전에 다음을 수집합니다.

```sh
docker compose ps
docker compose logs --timestamps --no-color
docker inspect <container>
```

Health 상태, Exit Code와 OOM 여부를 함께 남깁니다.

## 14. 보안
- Docker Socket Mount는 Host Root에 준하는 권한이므로 최소화합니다.
- Environment 출력과 Compose Render 결과에 Secret이 포함될 수 있습니다.
- 운영 Credential을 로컬 기본값으로 두지 않습니다.
- 신뢰하지 않는 Image에 Host Directory를 쓰기 가능 Mount하지 않습니다.

## 15. 검증 체크리스트
- 빈 Volume과 기존 Volume에서 모두 시작합니다.
- 한 Dependency를 중지해 Application 실패·회복을 확인합니다.
- 병렬 Compose Project가 충돌하지 않는지 확인합니다.
- Image 재Build 없이 CI가 검증 대상 Image를 정확히 사용하는지 확인합니다.
- `down -v` 뒤 잔여 Container·Network·Volume을 확인합니다.

---

## 16. 실무 사례 적용 진단과 개선 과제

Compose에 DB, Redis, Kafka 등 통합 의존성과 Health Check가 있지만 여러 Compose File과 고정 Port·Volume이 병렬 CI에서 충돌할 수 있습니다. 로컬 성공이 운영 EKS의 Network·Resource·TLS 조건을 그대로 재현하지도 않습니다.

Project Name과 Ephemeral Volume을 실행별로 분리하고 Health 기반 대기, Seed Idempotency, 종료 시 Log 수집과 `down -v`를 자동화합니다. 운영과 같은 Image Digest를 사용하되 Secret은 `.env` 기본값에 넣지 않습니다.

완료 기준은 두 Suite를 병렬 실행해도 Port·Data가 충돌하지 않고, 실패 후 Container·Network·Volume이 남지 않으며, CI가 외부 설치 없이 동일 명령으로 재현되는 상태입니다.

---

# Reference
- [Docker Compose](https://docs.docker.com/compose/)
- [[Jib와 Gradle 컨테이너 이미지 빌드]]
- [[Postman Newman WireMock 테스트 전략]]
