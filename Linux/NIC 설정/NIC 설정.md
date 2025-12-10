---
id: NIC 설정
started: 2025-02-27
tags:
  - ✅DONE
group: "[[Linux]]"
---
# NIC 설정
## NIC 활성, 비활성 커맨드
```shell title="NIC 활성, 비활성 커맨드"

# NIC DOWN Command (3가지 방법중 1개)
sudo ip link set dev eth0 down
sudo ifconfig eth0 down
nmcli device disconnect eth0

# 영구적으로 DOWN 시키는 방법
sudo vi /etc/sysconfig/network-scripts/ifcfg-eth0
# 파일 내에서 `ONBOOT=no` 설정

# NIC UP Command
sudo ip link set dev eth0 up
sudo ifconfig eth0 up
nmcli device connect eth0

# 영구적으로 UP 시키는 방법
sudo vi /etc/sysconfig/network-scripts/ifcfg-eth0
# 파일 내에서 `ONBOOT=yes` 설정

# 모든 설정 후 적용할때 서비스를 다시 시작해야함
sudo systemctl restart network

```

# Reference