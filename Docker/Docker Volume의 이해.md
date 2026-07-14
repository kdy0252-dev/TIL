---
id: Docker Volume의 이해
started: 2025-04-29
tags:
  - ✅DONE
  - Docker
group:
  - "[[Docker]]"
---
# Docker Volume의 이해

컨테이너 안에서 파일을 만들 수 있는데도 별도의 Volume이 필요한 이유는 무엇일까? 핵심은 **컨테이너와 데이터의 수명이 다르기 때문**이다. 컨테이너는 Image로부터 다시 만들 수 있는 실행 단위지만, Database의 데이터나 사용자가 올린 파일은 컨테이너가 교체되어도 남아야 한다.

이 글에서는 Container Layer가 사라지는 이유부터 Volume과 Bind Mount의 차이, 초기화 규칙, Backup과 권한 문제까지 차근차근 살펴본다.

## Image와 Container의 파일 시스템

Docker Image는 여러 개의 읽기 전용 Layer로 구성된다. 예를 들어 Base OS, Package 설치, Application Binary가 각각 Layer가 될 수 있다. 같은 Layer는 여러 Container가 공유할 수 있으므로 저장 공간과 배포 시간을 줄일 수 있다.

Container를 시작하면 Image Layer 위에 해당 Container만 사용하는 쓰기 가능 Layer가 추가된다.

```text
Container writable layer  ← 실행 중 생성·수정한 파일
Application image layer   ← 읽기 전용
Runtime image layer       ← 읽기 전용
Base OS layer             ← 읽기 전용
```

읽기 전용 Layer의 파일을 수정할 때는 원본을 직접 바꾸지 않는다. 파일을 쓰기 가능 Layer로 복사한 뒤 복사본을 변경한다. 이를 **Copy-on-Write**라고 한다. 파일을 삭제해도 아래 Layer의 원본이 물리적으로 지워지는 대신, 위 Layer에 “보이지 않게 됨”을 나타내는 정보가 기록된다.

![[Docker Volume의 이해 - 01.png]]

Container를 삭제하면 이 쓰기 가능 Layer도 함께 삭제된다. 같은 Image로 새 Container를 만들면 Image의 원래 상태에서 다시 시작한다. 따라서 Container Layer에는 Cache나 임시 변환 파일처럼 잃어도 되는 데이터만 두는 편이 안전하다.

> [!Important] 영속성의 의미
> Volume은 “Container 삭제와 데이터 삭제를 분리”한다. 하지만 Disk 고장, 실수로 실행한 `docker volume rm`, 파일 손상까지 막아 주는 Backup 도구는 아니다.

## Mount가 Container Layer를 우회하는 방식

Mount를 사용하면 특정 Container 경로의 읽기와 쓰기가 Container Layer가 아닌 Host의 별도 위치로 향한다. Docker에서 주로 사용하는 방식은 다음과 같다.

| 방식 | 실제 저장 위치의 관리자 | 적합한 용도 |
| --- | --- | --- |
| Named Volume | Docker Engine | Database 데이터, 운영 상태 데이터 |
| Bind Mount | 사용자와 Host OS | 개발 중 Source Code, 설정 파일 공유 |
| tmpfs Mount | Host Memory | 재시작 후 남길 필요가 없는 민감·임시 데이터 |

## 1. Named Volume

![[Docker Volume의 이해 - 02.png]]

Named Volume은 Docker가 생성, 위치 결정, 연결과 삭제를 관리하는 저장 공간이다. Linux Docker Engine에서는 보통 Docker Data Root 아래에 저장되지만, 그 내부 경로를 Application이 직접 사용해서는 안 된다. Docker Desktop은 Linux VM 안에서 Engine을 실행하므로 Host Finder에서 같은 경로를 찾을 수 없는 경우도 있다.

### 생성하고 연결하기

먼저 Volume을 만든다.

```shell
docker volume create volume-sight
```

![[Docker Volume의 이해 - 03.png]]

목록과 Metadata는 다음 명령으로 확인한다.

```shell
docker volume ls
docker volume inspect volume-sight
```

![[Docker Volume의 이해 - 04.png]]
![[Docker Volume의 이해 - 05.png]]

Container의 `/app/data`에 연결한다. `--mount`는 Source와 Target이 명시되어 읽기 쉽고 Option 실수를 줄일 수 있다.

```shell
docker run --detach \
  --name devtest \
  --mount type=volume,source=volume-sight,target=/app/data \
  nginx:latest
```

짧은 `-v volume-sight:/app/data` 문법도 같은 결과를 낸다. 다만 `-v`는 존재하지 않는 Host 경로를 Bind Mount Source로 지정하면 Directory를 자동 생성하는 등 의도하지 않은 동작이 생길 수 있어, 복잡한 설정에서는 `--mount`가 더 분명하다.

### 빈 Volume의 초기 복사 규칙

빈 Volume을 Container의 **이미 파일이 들어 있는 경로**에 처음 Mount하면 Docker는 기본적으로 그 파일을 Volume으로 복사한다. Image가 Database 초기 파일이나 기본 설정을 넣어 두었을 때 유용하다.

반대로 이미 데이터가 있는 Volume을 Mount하면 Image 안의 같은 경로는 가려진다. 데이터가 삭제된 것은 아니지만 Container에서는 Mount를 제거하기 전까지 볼 수 없다. “새 Version을 배포했는데 Image 안의 설정 변경이 반영되지 않는다”면 이 규칙을 먼저 확인한다.

### Compose에서 사용하기

```yaml
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_PASSWORD: example
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

Compose Project를 내려도 `docker compose down`만으로 Named Volume은 보통 남는다. `docker compose down --volumes`는 Volume까지 삭제하므로 운영 데이터가 있는 환경에서는 의미를 확인한 뒤 실행해야 한다.

## 2. Bind Mount

Bind Mount는 사용자가 지정한 Host의 File이나 Directory를 Container 경로에 직접 연결한다. Source Code를 수정하자마자 개발 Container에서 읽게 하거나, Host가 관리하는 설정 파일을 주입할 때 편리하다.

```shell
docker run --rm \
  --mount type=bind,source="$PWD/config",target=/app/config,readonly \
  example-app:latest
```

Bind Mount는 상대 경로 자체를 저장하는 개념이 아니다. Docker Daemon이 실행되는 Host의 경로에 강하게 의존한다. Remote Docker Daemon을 사용하면 Client Laptop이 아니라 **Daemon Host의 경로**가 Mount 대상이다.

또한 Container Process가 쓰기 권한을 가지면 Host 파일도 변경하거나 삭제할 수 있다. 읽기만 필요하다면 `readonly` 또는 `ro`를 붙이고, 운영 환경에서는 Mount할 Directory 범위를 최소화한다.

![[Docker Volume의 이해 - 06.png]]
![[Docker Volume의 이해 - 07.png]]

## 3. tmpfs Mount

Linux에서 tmpfs Mount는 데이터를 Host Memory에 두며 Container가 중지되면 내용이 사라진다. Disk에 남기고 싶지 않은 일시적 Secret이나 고속 임시 데이터에 사용할 수 있다. Memory를 사용하므로 크기 제한을 함께 설정하고, Memory 부족 위험을 고려해야 한다.

```shell
docker run --rm \
  --mount type=tmpfs,target=/app/runtime,tmpfs-size=67108864 \
  example-app:latest
```

## 권한 문제는 왜 생길까?

Volume에 기록하는 주체는 Container 안의 Process다. Process의 UID와 GID가 Volume Directory의 소유권과 맞지 않으면 `Permission denied`가 발생한다. Image가 Root가 아닌 User로 실행되도록 만들어졌다면 특히 자주 드러난다.

해결할 때 무조건 `chmod 777`을 적용하면 다른 Process에도 쓰기 권한을 열어 보안 경계가 사라진다. 대신 다음 순서로 확인한다.

1. `docker inspect`로 Mount의 Source와 Destination을 확인한다.
2. Container Process의 UID/GID를 확인한다.
3. 초기화 단계에서 필요한 Directory의 소유권만 해당 UID/GID로 맞춘다.
4. SELinux를 사용하는 Host라면 Label Option도 확인한다.

## Volume은 Backup이 아니다

영속 Volume도 같은 Disk에만 있다면 Host 장애와 함께 잃을 수 있다. Backup은 Application의 일관성 요구까지 고려해야 한다. Database를 실행 중인 채로 Directory만 복사하면 Memory와 WAL 상태가 맞지 않는 Backup이 만들어질 수 있으므로 Database가 제공하는 Dump, Snapshot 또는 Backup 기능을 우선 사용한다.

일반 File Volume이라면 별도 Container로 읽기 전용 Mount한 뒤 Archive할 수 있다.

```shell
docker run --rm \
  --mount type=volume,source=volume-sight,target=/source,readonly \
  --mount type=bind,source="$PWD/backup",target=/backup \
  alpine:3.21 \
  tar czf /backup/volume-sight.tar.gz -C /source .
```

Backup은 생성 성공만으로 끝나지 않는다. 정기적으로 새 Volume에 복원하고 Application이 실제 데이터를 읽을 수 있는지 검증해야 한다.

## 선택 기준

- 운영 Database처럼 Docker가 수명을 관리할 데이터에는 Named Volume을 우선 고려한다.
- 개발 Source Code나 명시적인 Host 설정 공유에는 Bind Mount를 사용한다.
- 재시작 후 없어져야 하는 임시 데이터에는 tmpfs를 검토한다.
- Container Layer에는 언제든 다시 만들 수 있는 데이터만 둔다.

Volume을 선택하는 기준은 단순히 “파일을 남긴다”가 아니다. **누가 저장 위치를 관리하는지, Container와 데이터의 수명이 어떻게 다른지, Backup과 복원을 누가 책임지는지**를 함께 결정하는 일이다.

# Reference
[Docker Docs - OverlayFS storage driver](https://docs.docker.com/engine/storage/drivers/overlayfs-driver/)
[Docker Docs - Volumes](https://docs.docker.com/engine/storage/volumes/)
[Docker Docs - Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
[Docker Docs - tmpfs mounts](https://docs.docker.com/engine/storage/tmpfs/)
