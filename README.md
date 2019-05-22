# BILILIVEBGM
直播间点歌机，使用mpg123向虚拟声卡播放音乐

## 使用方法
### 安装需要的软件包(Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y pulseaudio jackd2 alsa-utils dbus-x11 mpg123
```
### 获取运行程序
```bash
git clone https://github.com/kamino-space/BiliLiveBgm.git
pip install -r requirements.txt
python run.py
```
### 通过socket控制
...

## 功能
- 下一曲
- 下载网易云音乐

## 协议
MIT