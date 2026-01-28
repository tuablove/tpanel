#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取面板默认账号和密码
"""

import sys
import os

# 切换到 web 目录
web_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(web_dir)
sys.path.insert(0, web_dir)

import core.mw as mw
import thisdb

def get_default_account():
    """获取默认账号和密码"""
    print("=" * 60)
    print("面板默认账号信息")
    print("=" * 60)
    
    # 获取用户名
    user_info = thisdb.getUserByRoot()
    if user_info:
        username = user_info['name']
        print(f"\n用户名: {username}")
    else:
        print("\n错误: 未找到用户信息")
        return
    
    # 获取密码（从 default.pl 文件）
    default_pl_path = mw.getPanelDataDir() + '/default.pl'
    if os.path.exists(default_pl_path):
        password = mw.readFile(default_pl_path).strip()
        print(f"密码: {password}")
    else:
        print("密码: 未找到 default.pl 文件，密码可能已被修改")
        print("提示: 如果忘记了密码，可以使用以下命令重置：")
        print("      python panel_tools.py password")
    
    # 获取安全入口
    admin_path = thisdb.getOption('admin_path')
    if admin_path:
        print(f"\n安全入口: /{admin_path}")
        print(f"访问地址: http://localhost:7201/{admin_path}")
    else:
        print(f"\n安全入口: 已关闭")
        print(f"访问地址: http://localhost:7201/")
    
    print("\n" + "=" * 60)
    print("提示: 首次登录后请立即修改密码！")
    print("=" * 60)

if __name__ == '__main__':
    try:
        get_default_account()
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
