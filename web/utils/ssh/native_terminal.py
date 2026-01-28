# coding: utf-8

# ---------------------------------------------------------------------------------
# MW-Linux面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/midoks/mdserver-web) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 原生终端操作 - 使用 pty 直接创建系统 shell
# ---------------------------------------------------------------------------------

import os
import sys
import pty
import select
import termios
import struct
import fcntl
import threading
import time
import signal

import core.mw as mw


class native_terminal(object):
    """
    原生终端实现，使用 pty 模块直接创建系统 shell
    不依赖 SSH，直接使用系统的 shell (bash/sh)
    """

    __debug_file = 'logs/native_terminal.log'
    __log_type = '原生终端'

    # 存储每个会话的终端进程
    __terminals = {}
    __terminal_locks = {}
    __terminal_threads = {}

    # lock
    _instance_lock = threading.Lock()

    def __init__(self):
        self.__debug_file = mw.getPanelDir() + '/logs/native_terminal.log'

    @classmethod
    def instance(cls, *args, **kwargs):
        if not hasattr(native_terminal, "_instance"):
            with native_terminal._instance_lock:
                if not hasattr(native_terminal, "_instance"):
                    native_terminal._instance = native_terminal(*args, **kwargs)
        return native_terminal._instance

    def debug(self, msg):
        msg = "{} => {} \n".format(mw.formatDate(), msg)
        if not mw.isDebugMode():
            return
        mw.writeFile(self.__debug_file, msg, 'a+')

    def returnMsg(self, status, msg):
        return {'status': status, 'msg': msg}

    def _set_winsize(self, fd, row, col):
        """设置终端窗口大小"""
        try:
            winsize = struct.pack('HHHH', row, col, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
        except Exception as e:
            self.debug('设置窗口大小失败: {}'.format(str(e)))

    def _read_output(self, sid, master_fd, socketio_instance):
        """读取终端输出的线程函数"""
        try:
            while sid in self.__terminals:
                try:
                    # 使用 select 检查是否有数据可读
                    ready, _, _ = select.select([master_fd], [], [], 0.1)
                    if master_fd in ready:
                        try:
                            data = os.read(master_fd, 1024)
                            if data:
                                # 发送数据到前端
                                try:
                                    text = data.decode('utf-8', errors='replace')
                                    if socketio_instance:
                                        socketio_instance.emit('server_response', {'data': text}, room=sid)
                                except Exception as e:
                                    self.debug('发送数据失败: {}'.format(str(e)))
                        except OSError as e:
                            # 文件描述符关闭或进程退出
                            if e.errno != 9:  # 9 = Bad file descriptor
                                self.debug('读取数据错误: {}'.format(str(e)))
                            break
                except ValueError:
                    # master_fd 可能已关闭
                    break
                except Exception as e:
                    self.debug('select 错误: {}'.format(str(e)))
                    break
        except Exception as e:
            self.debug('读取输出线程错误: {}'.format(str(e)))
        finally:
            # 清理资源
            if sid in self.__terminals:
                self.close_terminal(sid)

    def create_terminal(self, sid, cols=83, rows=21, socketio_instance=None):
        """创建新的终端会话"""
        try:
            # 获取 shell 路径
            shell = os.environ.get('SHELL', '/bin/bash')
            if not os.path.exists(shell):
                shell = '/bin/sh'

            # 创建伪终端
            master_fd, slave_fd = pty.openpty()

            # 设置终端大小
            self._set_winsize(slave_fd, rows, cols)

            # 设置非阻塞模式
            fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

            # 创建子进程
            pid = os.fork()
            if pid == 0:
                # 子进程
                os.close(master_fd)
                os.setsid()
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr
                os.close(slave_fd)

                # 设置环境变量
                env = os.environ.copy()
                env['TERM'] = 'xterm-256color'
                env['COLUMNS'] = str(cols)
                env['LINES'] = str(rows)

                # 执行 shell
                os.execve(shell, [shell], env)
            else:
                # 父进程
                os.close(slave_fd)

                # 存储终端信息
                self.__terminals[sid] = {
                    'pid': pid,
                    'master_fd': master_fd,
                    'cols': cols,
                    'rows': rows,
                    'socketio': socketio_instance
                }

                # 启动读取线程
                read_thread = threading.Thread(
                    target=self._read_output,
                    args=(sid, master_fd, socketio_instance),
                    daemon=True
                )
                read_thread.start()
                self.__terminal_threads[sid] = read_thread

                self.debug('创建终端成功: sid={}, pid={}'.format(sid, pid))
                
                # 等待一下让 shell 初始化，然后发送换行来触发提示符
                time.sleep(0.2)
                try:
                    os.write(master_fd, b'\n')
                except:
                    pass
                
                if socketio_instance:
                    socketio_instance.emit('connect', {'data': 'ok'}, room=sid)
                return True

        except Exception as e:
            self.debug('创建终端失败: {}'.format(str(e)))
            import traceback
            self.debug('错误详情: {}'.format(traceback.format_exc()))
            if socketio_instance:
                socketio_instance.emit('server_response', {'data': '创建终端失败: {}\r\n'.format(str(e))}, room=sid)
            return False

    def close_terminal(self, sid):
        """关闭终端会话"""
        try:
            if sid in self.__terminals:
                term_info = self.__terminals[sid]
                pid = term_info['pid']
                master_fd = term_info['master_fd']

                # 关闭文件描述符
                try:
                    os.close(master_fd)
                except:
                    pass

                # 终止进程
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except:
                        pass
                except:
                    pass

                # 清理资源
                del self.__terminals[sid]
                if sid in self.__terminal_threads:
                    del self.__terminal_threads[sid]

                self.debug('关闭终端: sid={}'.format(sid))
                return True
        except Exception as e:
            self.debug('关闭终端失败: {}'.format(str(e)))
        return False

    def resize_terminal(self, sid, cols, rows):
        """调整终端大小"""
        try:
            if sid in self.__terminals:
                term_info = self.__terminals[sid]
                master_fd = term_info['master_fd']
                self._set_winsize(master_fd, rows, cols)
                term_info['cols'] = cols
                term_info['rows'] = rows
                self.debug('调整终端大小: sid={}, {}x{}'.format(sid, cols, rows))
                return True
        except Exception as e:
            self.debug('调整终端大小失败: {}'.format(str(e)))
        return False

    def send_input(self, sid, data):
        """发送输入到终端"""
        try:
            if sid in self.__terminals:
                term_info = self.__terminals[sid]
                master_fd = term_info['master_fd']
                if isinstance(data, str):
                    data = data.encode('utf-8')
                os.write(master_fd, data)
                return True
            else:
                # 如果终端不存在，尝试创建
                if isinstance(data, dict) and 'resize' in data:
                    # 这是 resize 请求，忽略
                    return False
                # 创建新终端
                self.create_terminal(sid)
                return False
        except Exception as e:
            self.debug('发送输入失败: {}'.format(str(e)))
            return False

    def run(self, sid, data, socketio_instance=None):
        """
        处理 SocketIO 消息
        data 可能是字符串（输入数据）或字典（包含 resize 信息）
        socketio_instance: SocketIO 实例，用于发送消息
        """
        try:
            # 如果终端不存在，创建它
            if sid not in self.__terminals:
                if isinstance(data, dict):
                    cols = data.get('cols', 83)
                    rows = data.get('rows', 21)
                    self.create_terminal(sid, cols, rows, socketio_instance)
                else:
                    # 空对象或空字符串都创建终端
                    self.create_terminal(sid, socketio_instance=socketio_instance)
                return

            # 处理 resize 请求
            if isinstance(data, dict):
                if 'resize' in data:
                    cols = data.get('cols', 83)
                    rows = data.get('rows', 21)
                    self.resize_terminal(sid, cols, rows)
                    return
                # 如果是其他字典，忽略
                return

            # 处理空字符串（心跳检测）
            if isinstance(data, str) and data == '':
                # 心跳检测，不做任何处理，但保持连接
                return

            # 处理输入数据
            if isinstance(data, str):
                self.send_input(sid, data)
            elif isinstance(data, bytes):
                self.send_input(sid, data)

        except Exception as e:
            self.debug('处理消息失败: {}'.format(str(e)))
            import traceback
            self.debug('错误详情: {}'.format(traceback.format_exc()))
            if socketio_instance:
                socketio_instance.emit('server_response', {'data': '错误: {}\r\n'.format(str(e))}, room=sid)
