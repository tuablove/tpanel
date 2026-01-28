# coding=utf-8

# ---------------------------------------------------------------------------------
# MW-Linux面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/midoks/mdserver-web) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------



import sys
import os

from admin import app, socketio
import config

# 我们需要在sys.path中包含根目录，以确保我们可以找到在独立运行时运行时所需的一切。
if sys.path[0] != os.path.dirname(os.path.realpath(__file__)):
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

if sys.version_info < (3, 6):
    raise RuntimeError('This application must be run under Python 3.6 or later.')


def get_startup_info():
    """获取启动信息：安全入口和默认账号"""
    try:
        import thisdb
        import core.mw as mw
        
        info = {}
        
        # 获取安全入口
        admin_path = thisdb.getOption('admin_path')
        if admin_path:
            info['admin_path'] = '/' + admin_path
        else:
            info['admin_path'] = '已关闭'
        
        # 获取默认账号信息
        user_info = thisdb.getUserByRoot()
        if user_info:
            info['username'] = user_info['name']
            
            # 获取密码（从 default.pl 文件）
            default_pl_path = mw.getPanelDataDir() + '/default.pl'
            if os.path.exists(default_pl_path):
                info['password'] = mw.readFile(default_pl_path).strip()
            else:
                info['password'] = '密码已修改（查看 default.pl 文件）'
        else:
            info['username'] = '未找到'
            info['password'] = '未找到'
        
        return info
    except Exception as e:
        # 如果获取信息失败，返回默认值
        return {
            'admin_path': '获取失败',
            'username': '获取失败',
            'password': '获取失败'
        }


def main():
    # 获取配置的服务器地址和端口
    host = config.DEFAULT_SERVER
    port = config.DEFAULT_SERVER_PORT
    
    # 获取启动信息
    startup_info = get_startup_info()
    
    # 打印启动信息
    print("=" * 60)
    print("Starting MW Panel Server...")
    print("Server: http://{}:{}".format(host, port))
    print("Debug mode: {}".format(config.DEBUG))
    print("-" * 60)
    print("安全入口: {}".format(startup_info['admin_path']))
    if startup_info['admin_path'] != '已关闭':
        print("访问地址: http://{}:{}{}".format(host, port, startup_info['admin_path']))
    else:
        print("访问地址: http://{}:{}".format(host, port))
    print("-" * 60)
    print("默认账号信息:")
    print("  用户名: {}".format(startup_info['username']))
    print("  密码: {}".format(startup_info['password']))
    print("=" * 60)
    print("")
    
    # 启动 SocketIO 服务器
    socketio.run(
        app,
        host=host,
        port=port,
        debug=config.DEBUG,
        allow_unsafe_werkzeug=True  # 允许在调试模式下运行
    )
    # app.run(debug=True)

if __name__ == '__main__':
    main()
