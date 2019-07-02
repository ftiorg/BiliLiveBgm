import os
import socket
import threading
import json
import queue
import time
import subprocess
import requests
import hashlib
import random
import re
import shutil

from mutagen.mp3 import MP3

ROOT_PATH = os.path.dirname(os.path.abspath(__file__)) + '/'


class Player(object):
    _playlist = queue.Queue(100)
    _playing = None
    _musicpath = os.path.abspath(ROOT_PATH + 'music') + '/'
    _switch = True
    _player = None
    _next = None

    def music_list(self):
        """
        音乐列表
        :return:
        """
        mlist = []  # TODO: 文件夹没有音乐时add无效
        for item in os.listdir(self._musicpath):
            if item.endswith('.mp3'):
                path = os.path.abspath(self._musicpath + '%s' % item)
                mlist.append({
                    'id': Encrypt.md5(item)[:10],
                    'name': item,
                    'path': path,
                    'length': self.mp3_length(path)
                })
        return mlist

    def make_play_list(self):
        """
        生成播放列表
        :return:
        """
        Log.info('生成播放列表')
        for item in self.music_list():
            self.add_to_list(item)

    def get_music_obj(self, name):
        """
        获取音乐对象
        :param path:
        :return:
        """
        return {
            'id': Encrypt.md5(name)[:10],
            'name': name,
            'path': os.path.abspath(self._musicpath + name),
            'length': self.mp3_length(self._musicpath + name)
        }

    def add_to_list(self, music):
        """
        添加音乐到播放列表
        :param music:
        :return:
        """
        Log.info('添加', music['name'])
        self._playlist.put_nowait(music)

    def play_all(self):
        """
        启动播放器
        :return:
        """
        Log.info("开始播放")
        while True:
            if self._next is None: self.play_next()
            self._playing = self._next
            self.play_next()
            self.play(self._playing)
            while self.is_playing():
                time.sleep(0.5)

    def play_next(self):
        """
        获取下一曲
        :return:
        """
        if self._playlist.empty(): self.make_play_list()
        self._next = self._playlist.get()
        return self._next

    def play(self, music):
        """
        播放音乐
        :param music:
        :return:
        """
        print(music)
        try:
            Log.info('播放音乐', str(music['name']))
            command = ['mpg123', '%s' % music['path']]
            self._player = subprocess.Popen(command, stdin=subprocess.PIPE)
        except Exception as e:
            Log.error('播放错误', str(e))

    def what_playing(self):
        """
        正在播放的
        :return:
        """
        if self.is_playing():
            return self._playing
        return None

    def what_next(self):
        """
        下一曲是啥
        :return:
        """
        if self._next is None:
            return None
        return self._next

    def is_playing(self):
        """
        正在播放
        :return:
        """
        try:
            if self._player.poll() is None:
                return True
            else:
                return False
        except Exception as e:
            return False

    def ctrl_start(self):
        """
        播放
        :return:
        """
        self.is_playing() is False or self._player.stdin.write('S'.encode('utf-8'))

    def ctrl_stop(self):
        """
        暂停
        :return:
        """
        self.is_playing() is False or self._player.stdin.write('S'.encode('utf-8'))

    def ctrl_next(self):
        """
        下一曲
        :return:
        """
        self.is_playing() is False or self._player.kill()

    def mp3_info(self, path):
        """
        获取音频信息
        :param path:
        :return:
        """
        try:
            mp3 = MP3(path)
            return mp3.info
        except Exception as e:
            Log.error('错误', str(e))
            return None

    def clear_list(self):
        """
        清空当前播放列表 TODO: 貌似不能用
        :return:
        """
        while self._playlist.empty() is False:
            self._playlist.get()
        self.ctrl_stop()

    def mp3_add_directly(self, url):
        """
        下载网易云音乐
        :param url:
        :return:
        """
        data = self.get_163_music_data(url)
        name = '%s - %s.mp3' % (data['author'], data['title'])
        temp = os.path.abspath(ROOT_PATH + 'temp/%s' % name)
        save = os.path.abspath(ROOT_PATH + 'music/%s' % name)
        if (self.mp3_check(save)):
            return self.get_music_obj(name)
        Log.info('下载', name)
        if data is None:
            Log.info('获取信息失败')
            return False
        response = requests.get(data['url'], headers={
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'Referer': data['url']
        })
        if response.status_code != 200:
            return False
        with open(temp, 'wb') as f:
            f.write(response.content)
        if self.mp3_check(temp):
            Log.info('下载成功')
            shutil.move(temp, save)
            music = self.get_music_obj(name)
            self.add_to_list(music)
            return music
        Log.info('下载失败')
        os.unlink(temp)
        return False

    def get_163_music_data(self, url):
        """
        获取网易云音乐的信息
        :param url:
        :return:
        """
        if re.search('music.163.com', url) is None:
            return None
        response = requests.post('https://cloud.aikamino.cn/music/',
                                 data='input=%s&filter=url&type=_&page=1' % url,
                                 headers={
                                     'Accept': "application/json, text/javascript, */*; q=0.01",
                                     'Accept-Encoding': "gzip, deflate, br",
                                     'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8",
                                     'Connection': "keep-alive",
                                     'Content-Length': "86",
                                     'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
                                     'Host': "cloud.aikamino.cn",
                                     'Origin': "https://cloud.aikamino.cn",
                                     'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36",
                                     'X-Requested-With': "XMLHttpRequest",
                                     'cache-control': "no-cache",
                                 })
        try:
            data = json.loads(response.content.decode('utf-8'))
            if data['code'] != 200:
                raise Exception('服务器错误', str(data))
            Log.info('获取歌曲信息', str(data))
            return {
                'title': data['data'][0]['title'],
                'author': data['data'][0]['author'],
                'url': data['data'][0]['url']
            }
        except Exception as e:
            Log.error('错误', str(e))
            return None

    def mp3_length(self, path):
        """
        获取音频长度
        :param path:
        :return:
        """
        return self.mp3_info(path).length or None

    def mp3_check(self, path):
        """
        判断是否为mp3
        :return:
        """
        if self.mp3_info(path) is not None:
            return True
        return False

    def __del__(self):
        """
        退出清理
        :return:
        """
        try:
            self._player.terminate()
        except Exception as e:
            Log.error(str(e))


class Server():

    def __init__(self, unix=False, host='127.0.0.1', port=9999, path='/var/run/bgm.sock'):
        self.unix = unix
        self.host = host
        self.port = port
        self.path = path

    def server_init(self):
        """
        初始化服务端
        :return:
        """
        if self.unix is True:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            if os.path.exists(self.path):
                os.unlink(self.path)
            self.sock.bind(self.path)
            Log.info('UNIX监听', self.path)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind((self.host, self.port))
            Log.info('SOCKET监听', '%s:%s' % (socket.gethostname(), str(self.port)))

    def server_start(self):
        """
        服务器开始等待客户端
        :return:
        """
        Log.info('启动服务端')
        self.server_init()
        self.sock.listen(10)
        while True:
            try:
                client, addr = self.sock.accept()
                Log.info('客户端连接', str(addr))
                threading.Thread(target=self.server_link, args=(client, addr,)).start()
            except Exception as e:
                Log.error('错误', str(e))

    def server_link(self, sock, addr):
        """
        连接一个客户端
        :param sock:
        :param addr:
        :return:
        """
        try:
            msg_recv = sock.recv(1024).decode('utf-8')
            Log.info('接收消息', msg_recv, str(addr))
            msg_send = self.handle_msg(msg_recv)
            if msg_send is None:
                raise Exception('无返回消息')
            Log.info('发送消息', msg_send, str(addr))
            sock.send(msg_send.encode('utf-8'))
        except Exception as e:
            Log.error('错误', str(e))
        finally:
            Log.info('断开连接', str(addr))
            sock.close()

    def run_player(self):
        """
        启动播放器
        :return:
        """
        self.player = Player()
        self.player.play_all()

    def handle_msg(self, msg):
        """
        处理消息
        :param msg:
        :return:
        """
        try:
            mbj = json.loads(msg)
            if mbj['action'] == 'playlist':
                return json.dumps({
                    'data': self.player.make_play_list()
                })
            elif mbj['action'] == 'playing':
                return json.dumps({
                    'data': self.player.what_playing()
                })
            elif mbj['action'] == 'willplay':
                return json.dumps({
                    'data': self.player.what_next()
                })
            elif mbj['action'] == 'add':
                add = self.player.mp3_add_directly(mbj['url'])
                if add is not False:
                    return json.dumps({
                        'data': add
                    })
                else:
                    return json.dumps({
                        'data': False
                    })
            elif mbj['action'] == 'start':
                self.player.ctrl_start()
                return json.dumps({
                    'data': True
                })
            elif mbj['action'] == 'stop':
                self.player.ctrl_stop()
                return json.dumps({
                    'data': True
                })
            elif mbj['action'] == 'next':
                self.player.ctrl_next()
                return json.dumps({
                    'data': self.player.what_next()
                })
            elif mbj['action'] == 'clear':
                self.player.clear_list()
                return json.dumps({
                    'data': True
                })
            else:
                raise Exception('未知操作', str(mbj))
        except Exception as e:
            Log.error('消息处理错误', str(e))
            return None

    def run(self):
        """
        启动
        :return:
        """
        threading.Thread(target=self.run_player).start()
        self.server_start()


class Log(object):
    @staticmethod
    def add(msg, level):
        """
        输出保存日志
        :param msg:
        :param level:
        :return:
        """
        text = '[{time}] [{level}]  {msg}'.format(
            time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            level=level,
            msg=msg
        )
        print(text)
        # with open(ROOT_PATH + 'log.txt', 'a', encoding='utf-8') as f:
        #    f.write(text + '\r')

    @staticmethod
    def info(*args):
        """
        INFO
        :param args:
        :return:
        """
        Log.add(' '.join(args), 'INFO')

    @staticmethod
    def warning(*args):
        """
        INFO
        :param args:
        :return:
        """
        Log.add(' '.join(args), 'WARNING')

    @staticmethod
    def error(*args):
        """
        INFO
        :param args:
        :return:
        """
        Log.add(' '.join(args), 'ERROR')


class Encrypt(object):

    @staticmethod
    def md5(text=''):
        """计算md5"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def sha1(text=''):
        """计算sha1"""
        return hashlib.sha1(text.encode('utf-8')).hexdigest()

    @staticmethod
    def key(length=16):
        """生成指定位数字符串"""
        di = '0123456789abcdef'
        key = ''
        for i in range(length):
            key += di[random.randint(0, 15)]
        return key
