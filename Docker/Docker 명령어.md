---
id: Docker 명령어
started: 2025-05-02
tags:
  - ✅DONE
group:
  - "[[Docker]]"
---
# Docker 명령어

Docker 명령을 외울 때는 `Image`와 `Container`를 먼저 구분해야 한다. Image는 Container를 만들기 위한 읽기 전용 원본이고, Container는 그 Image에서 실제로 실행되는 Process다. 따라서 `pull`은 원본을 받고, `run`은 새 Container를 만들고 시작하며, `exec`는 이미 실행 중인 Container에 새 Process를 추가한다.

## 이미지 다운로드
```shell title="MariaDB 이미지 다운로드 예시"
docker pull mariadb:11.7
```

`latest`는 “가장 안정적인 Version”이 아니라 Registry가 가리키는 이름일 뿐이며 시간이 지나면 다른 Image를 받을 수 있다. 재현 가능한 환경에는 Version Tag를 고정하고, 공급망 검증이 필요한 운영 배포에는 Digest도 고려한다.

## 컨테이너 생성
```shell title="MariaDB 컨테이너 생성 예시"
docker run -d \
  --name my-mariadb \
  --env-file ./mariadb.env \
  --publish 127.0.0.1:3306:3306 \
  --mount type=volume,source=mariadb-data,target=/var/lib/mysql \
  --restart unless-stopped \
  mariadb:11.7
```

Password를 Shell History와 Process 목록에 남기지 않도록 `--env-file` 또는 Secret 관리 기능을 사용한다. `127.0.0.1`에 Bind하면 Host 외부에 Port를 직접 공개하지 않는다. Named Volume은 Container가 교체되어도 Database 데이터를 보존한다.

`docker run`은 `docker create`와 `docker start`를 합친 명령이다. 같은 이름의 중지된 Container가 있으면 새로 만드는 대신 `docker start my-mariadb`를 사용한다.

## 명령어 실행
```shell title="MariaDB 컨테이너 내부에서 명령어 실행"
docker exec -it my-mariadb mysql -uroot -p
```

`-i`는 표준 입력을 열고 `-t`는 Terminal을 할당한다. 자동화 Script에서 출력만 필요하면 TTY 없이 실행하는 편이 안전하다.

## 상태와 Log 확인

```shell
docker ps
docker ps --all
docker logs --follow --tail 100 my-mariadb
docker inspect my-mariadb
docker stats my-mariadb
```

`ps`는 실행 상태, `logs`는 Container의 표준 출력과 오류, `inspect`는 Mount·Network·환경 설정, `stats`는 CPU와 Memory 사용량을 보여 준다. Application Log가 파일에만 기록되면 `docker logs`에서 보이지 않으므로 Container 환경에서는 표준 출력 Logging을 기본으로 삼는다.

## 정상 종료와 삭제

```shell
docker stop --time 30 my-mariadb
docker rm my-mariadb
docker image rm mariadb:11.7
```

`stop`은 먼저 종료 Signal을 보내고 제한 시간 뒤 강제 종료한다. Database가 Flush할 시간을 확보하도록 즉시 `kill`하지 않는다. Container 삭제와 Volume 삭제는 별개이므로 `docker volume rm mariadb-data`는 Backup과 보존 정책을 확인한 뒤 실행한다.

## 문제를 좁히는 순서

1. `docker ps --all`에서 종료 코드와 상태를 본다.
2. `docker logs`에서 시작 실패 원인을 찾는다.
3. `docker inspect`로 환경 변수, Port, Mount와 Network를 확인한다.
4. `docker exec`로 Container 내부만 보지 말고 Host Port와 Volume 권한도 함께 확인한다.
5. 재현 가능한 `docker run` 또는 Compose 설정을 Version Control에 남긴다.


# Reference
[Docker Docs - Running containers](https://docs.docker.com/engine/containers/run/)
[Docker CLI - docker container](https://docs.docker.com/reference/cli/docker/container/)
[Docker CLI - docker image](https://docs.docker.com/reference/cli/docker/image/)
