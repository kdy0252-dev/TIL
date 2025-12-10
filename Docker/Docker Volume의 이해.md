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
도커 볼륨이 무엇인지 제대로 이해하기 위해서는
먼저 Docker의 파일 시스템의 작동 방식을 정리 할 필요가 있다.
**Docker Image**는 일련의 **Read Only Layer** 로 구성되어있다.
컨테이너가 시작될 때, **Read Only** **Layer** 맨 위에 **Read Write** **Layer**를 추가한다.
실행중인 컨테이너가 기존 파일을 수정하는 경우,
파일은 **Read Only Layer**에서 맨 위의  **Read Write** **Layer**로 복사된다.
도커에서 이런 **Read-Only + Read-Write Layer**의 조합을 **Union File System**이라고 부른다.

![[Pasted image 20250429150710.png]]
**Read Only Layer** 는 기존 파일이 수정될 경우 파일을 숨기지만, 삭제하지 않는다. **(위의 file 2)**
이후 컨테이너가 삭제되면 기존에 숨겨진 파일을 다시 가져와서 로딩하기 때문에 **변경 내역이 유실**된다.
이를 방지하기 위해 컨테이너의 데이터를 **영속화** 시킬 수 있는 방법이 몇가지 있다.
그중 가장 활용하기 쉬운 방법이 이번에 정리할  **도커 볼륨**을 활용하는 것 있다.

### 1. Volume Mount
![[Pasted image 20250429150745.png]]
도커 공식 문서에서 권장하는 방식이다. **/var/lib/docker/volumes/** 아래에 
도커 엔진이 관리하는 볼륨들이 생성되어 마운트하여 사용할 수 있다.
도커 엔진이 관리하기 때문에 관리 측면에서 유리하다.

### - Tutorial
다음과 같이 **docker volume**을 생성해준다.
![[Pasted image 20250429150833.png]]
생성된 볼륨 목록은 **docker volume ls** 명령어를 통해 볼 수 있고,
![[Pasted image 20250429150850.png]]
**docker volume inspect** 명령어를 통해 세부 내역을 볼 수 있다.
![[Pasted image 20250429150858.png]]
우리가 예상한 대로 **/var/lib/docker/volumes** 안에 데이터가 생성된 걸 확인할 수 있다.
이렇게 생성된 볼륨은 컨테이너 시작시 -v 옵션을 통해 마운트할 수 있다.
기존에 호스트에 있는 파일을 마운트 하는것도  위와 같이 작동한다.

```shell title="도커 볼륨 마운트"
docker run -d --name devtest -v volume-sight:/app nginx:latest
```

### 2. Bind Mount
**Bind Mount**를 사용하면 호스트의 파일 또는 디렉토리가 **상대경로로 참조되어** 컨테이너에 마운트된다. 
도커 초창기부터 사용된 방식이며, 이 파일들은 도커 엔진이 관리하지 않기 때문에
위의 **Volume Mount** 에 비해 기능이 제한된다. 또한 호스트상에서 도커 외에 다른 프로세스가
마운트된 공간에 접근 할 수 있기 때문에 격리된 환경을 만들지 못한다는 단점이 있다.
바인드 마운트를 사용하려면 볼륨 이름대신 host의 경로를 입력해주면 사용가능하다.
볼륨을 사용하는것이 아니기에 당연히 **docker** **volume ls** 등으로 확인할 수 없다.
![[Pasted image 20250429151007.png]]
컨테이너를 inspect 해보면 다음과 같이 경로가 호스트에 바인딩 된 걸 확인 할 수 있다.
(위의 **docker volume inspect**와 혼동 주의)
![[Pasted image 20250429151015.png]]

# Reference
[도커 파일시스템 문서](https://docs.docker.com/storage/storagedriver/overlayfs-driver/)
[도커 볼륨 문서](https://docs.docker.com/storage/volumes/)
[도커 bind mounts 문서](https://docs.docker.com/storage/bind-mounts/)
