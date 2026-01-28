#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全入口管理工具
用于查看和修改面板安全入口路径
"""

import sys
import os

# 切换到 web 目录
web_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(web_dir)
sys.path.insert(0, web_dir)

import thisdb
import core.mw as mw

def show_admin_path():
    """显示当前安全入口路径"""
    admin_path = thisdb.getOption('admin_path')
    if admin_path == '':
        print("=" * 60)
        print("当前安全入口: /login (已关闭)")
        print("=" * 60)
        print("\n访问地址: http://localhost:7201/")
    else:
        print("=" * 60)
        print("当前安全入口: /{}".format(admin_path))
        print("=" * 60)
        print("\n访问地址: http://localhost:7201/{}".format(admin_path))
        print("\n提示: 如果忘记了入口路径，可以使用此工具关闭安全入口")

def close_admin_path():
    """关闭安全入口"""
    print("=" * 60)
    print("警告: 关闭安全入口将使您的面板登录地址直接暴露在互联网上！")
    print("=" * 60)
    
    confirm = input("\n确定要关闭安全入口吗？(yes/no): ").strip().lower()
    if confirm == 'yes':
        thisdb.setOption('admin_path', '')
        print("\n✓ 安全入口已关闭")
        print("现在可以通过 http://localhost:7201/ 直接访问面板")
    else:
        print("\n操作已取消")

def set_admin_path(path=None):
    """设置安全入口路径"""
    if path is None:
        path = input("请输入新的安全入口路径 (例如: mypanel): ").strip()
    
    if not path:
        print("错误: 入口路径不能为空")
        return
    
    # 移除开头的斜杠
    if path.startswith('/'):
        path = path[1:]
    
    if len(path) < 6:
        print("错误: 安全入口路径长度不能小于6位")
        return
    
    # 检查敏感路径
    sensitive_paths = ['login', 'do_login', 'site', 'sites', 'download_file', 
                      'control', 'crontab', 'firewall', 'files', 'config', 
                      'setting', 'monitor', 'soft', 'system', 'code', 'ssl', 
                      'plugins', 'hook', 'close']
    
    if path in sensitive_paths:
        print("错误: 该入口已被面板占用，请使用其它入口")
        return
    
    thisdb.setOption('admin_path', path)
    print("\n✓ 安全入口已设置为: /{}".format(path))
    print("访问地址: http://localhost:7201/{}".format(path))

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'show' or cmd == 'default':
            show_admin_path()
        elif cmd == 'close':
            close_admin_path()
        elif cmd == 'set':
            path = sys.argv[2] if len(sys.argv) > 2 else None
            set_admin_path(path)
        else:
            print("用法:")
            print("  python admin_path_tool.py show      - 查看当前安全入口")
            print("  python admin_path_tool.py close     - 关闭安全入口")
            print("  python admin_path_tool.py set [path] - 设置安全入口路径")
    else:
        # 交互式菜单
        print("\n" + "=" * 60)
        print("面板安全入口管理工具")
        print("=" * 60)
        print("\n1. 查看当前安全入口")
        print("2. 关闭安全入口")
        print("3. 设置安全入口路径")
        print("0. 退出")
        print("=" * 60)
        
        choice = input("\n请选择操作 (0-3): ").strip()
        
        if choice == '1':
            show_admin_path()
        elif choice == '2':
            close_admin_path()
        elif choice == '3':
            set_admin_path()
        elif choice == '0':
            print("退出")
        else:
            print("无效的选择")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print("\n错误: {}".format(str(e)))
        import traceback
        traceback.print_exc()
