---
id: NIC 설정
started: 2025-02-27
tags:
  - ✅DONE
group: "[[Linux]]"
---
# Linux NIC 상태와 Network 설정 이해하기

NIC를 “내린다”는 표현에는 서로 다른 동작이 섞여 있다. Kernel의 Network Interface Link를 비활성화할 수도 있고, NetworkManager의 Connection Profile을 끊을 수도 있다. 전자는 Device 상태, 후자는 IP·Route·DNS를 포함한 설정 단위다.

원격 SSH Server의 NIC나 Default Route를 변경하면 접속이 즉시 끊길 수 있다. Console, Out-of-band 관리망 또는 자동 Rollback 수단을 확보한 뒤 작업한다.

## Device와 Connection Profile 확인

```shell
ip -brief link
ip -brief address
ip route
nmcli device status
nmcli connection show --active
```

`eth0` 같은 이름을 가정하지 않는다. 최근 Linux는 `enp1s0`, `ens5`처럼 Hardware 위치를 반영한 예측 가능한 이름을 주로 사용한다. `ip link`의 `UP`은 관리상 활성 상태이고 `LOWER_UP`은 Cable이나 Virtual Link가 실제 연결되었음을 뜻한다.

## 일시적으로 Link 활성화·비활성화

```shell
sudo ip link set dev enp1s0 down
sudo ip link set dev enp1s0 up
```

이 명령은 현재 Boot Session의 Kernel Device 상태를 바꾼다. NetworkManager가 관리 중이면 자동 연결 정책에 의해 다시 올라올 수 있다. `ifconfig`는 오래된 net-tools 명령이므로 새 Script에서는 `ip`와 `nmcli`를 우선한다.

## NetworkManager Connection 제어

```shell
nmcli connection show
sudo nmcli connection down 'System enp1s0'
sudo nmcli connection up 'System enp1s0'
```

Device 이름과 Connection 이름은 다를 수 있다. `nmcli device disconnect enp1s0`은 Device를 끊고 자동 연결도 막을 수 있으며, `connection down`은 특정 Profile을 비활성화한다. 의도에 맞는 단위를 선택한다.

## 재부팅 후 자동 연결 설정

RHEL 9 계열의 새 Profile은 `/etc/NetworkManager/system-connections/`의 Keyfile 형식을 기본으로 사용한다. 과거의 `/etc/sysconfig/network-scripts/ifcfg-*`만 직접 편집하는 방식은 Distribution과 Version에 따라 적용되지 않을 수 있다.

```shell
sudo nmcli connection modify 'System enp1s0' connection.autoconnect no
sudo nmcli connection modify 'System enp1s0' connection.autoconnect yes
```

Static IPv4 설정은 주소, Gateway, DNS를 하나의 Profile에 명시한다.

```shell
sudo nmcli connection modify 'System enp1s0' \
  ipv4.method manual \
  ipv4.addresses 192.0.2.10/24 \
  ipv4.gateway 192.0.2.1 \
  ipv4.dns '192.0.2.53 192.0.2.54'

sudo nmcli connection up 'System enp1s0'
```

설정 후에는 Link만 보지 말고 다음 계층을 순서대로 검증한다.

1. `ip link`로 물리·가상 Link 상태 확인
2. `ip address`로 IP와 Prefix 확인
3. `ip route get <destination>`으로 실제 선택 Route 확인
4. `resolvectl status` 또는 `nmcli device show`로 DNS 확인
5. Gateway, 내부 IP, Domain 순서로 연결 확인

모든 Network 서비스를 통째로 Restart하면 관련 없는 Interface까지 끊길 수 있다. 변경한 Connection만 다시 활성화하고, Network 설정을 자동화할 때는 배포판의 NetworkManager, systemd-networkd 또는 Netplan 중 실제 관리자를 먼저 확인한다.

# Reference
[RHEL 9 - Configuring and managing networking](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/)
[ip-link Manual](https://man7.org/linux/man-pages/man8/ip-link.8.html)
[NetworkManager nmcli](https://networkmanager.dev/docs/api/latest/nmcli.html)
