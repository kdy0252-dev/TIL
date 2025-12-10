---
id: Docker 명령어
started: 2025-05-02
tags:
  - ✅DONE
group:
  - "[[Docker]]"
---
# Docker 명령어
## 이미지 다운로드
```shell title="MariaDB 이미지 다운로드 예시"
docker pull mariadb:latest
```

## 컨테이너 생성
```shell title="MariaDB 컨테이너 생성 예시"
docker run -d \
  --name my-mariadb \
  -e MYSQL_ROOT_PASSWORD=your_root_password \
  -e MYSQL_DATABASE=mydb            # (선택) 컨테이너 시작 시 생성할 DB 이름
  -e MYSQL_USER=myuser              # (선택) 생성할 일반 계정
  -e MYSQL_PASSWORD=myuser_password # (선택) 일반 계정 비번
  -p 3306:3306                       # 호스트:컨테이너 포트 매핑
  -v /path/on/host/mysql_data:/var/lib/mysql  # (권장) 데이터 퍼시스턴스 볼륨
  mariadb:latest
```

## 명령어 실행
```shell title="MariaDB 컨테이너 내부에서 명령어 실행"
docker exec -it my-mariadb mysql -uroot -p
```


# Reference