# coding:utf-8

# ---------------------------------------------------------------------------------
# MW-Linux面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/midoks/mdserver-web) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

import os
import psutil

from flask import Blueprint, render_template
from flask import request

from admin.user_login_check import panel_login_required
from utils.system import monitor

import core.mw as mw
import utils.system as sys
import thisdb

blueprint = Blueprint('system', __name__, url_prefix='/system', template_folder='../../templates')

# 获取系统的统计信息
@blueprint.route('/system_total', endpoint='system_total', methods=['GET','POST'])
@panel_login_required
def system_total():
    data = sys.getMemInfo()
    cpu = sys.getCpuInfo(interval=1)
    data['cpuNum'] = cpu[1]
    data['cpuRealUsed'] = cpu[0]
    data['time'] = sys.getBootTime()
    data['system'] = sys.getSystemVersion()
    data['version'] = '0.0.1'
    return data

# 获取环境信息
@blueprint.route('/get_env_info', endpoint='get_env_info', methods=['GET','POST'])
@panel_login_required
def get_env_info():
    return sys.getEnvInfo()

# 获取系统的网络流量信息
@blueprint.route('/network', endpoint='network')
@panel_login_required
def network():
    stat = {}
    stat['cpu'] = sys.getCpuInfo()
    stat['load'] = sys.getLoadAverage()
    stat['mem'] = sys.getMemInfo()
    stat['iostat'] = sys.stats().disk()
    stat['network'] = sys.stats().network()
    return stat

# 获取系统的磁盘信息
@blueprint.route('/disk_info', endpoint='disk_info', methods=['GET','POST'])
@panel_login_required
def disk_info():
    data = sys.getDiskInfo()
    return mw.returnData(True, 'ok', data)

# 获取系统的负载统计信息
@blueprint.route('/get_load_average', endpoint='get_load_average', methods=['GET'])
@panel_login_required
def get_load_average():
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    data = sys.getLoadAverageByDB(start, end)
    return mw.returnData(True, 'ok', data)

# 获取系统的磁盘IO统计信息
@blueprint.route('/get_disk_io', endpoint='get_disk_io', methods=['GET'])
@panel_login_required
def get_disk_io():
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    data = sys.getDiskIoByDB(start, end)
    return mw.returnData(True, 'ok', data)

# 获取系统的CPU/IO统计信息
@blueprint.route('/get_cpu_io', endpoint='get_cpu_io', methods=['GET'])
@panel_login_required
def get_cpu_io():
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    data = sys.getCpuIoByDB(start, end)
    return mw.returnData(True, 'ok', data)

# 获取系统网络IO统计信息
@blueprint.route('/get_network_io', endpoint='get_network_io', methods=['GET'])
@panel_login_required
def get_network_io():
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    data = sys.getNetworkIoByDB(start, end)
    return mw.returnData(True, 'ok', data)

# 重启面板
@blueprint.route('/restart', endpoint='restart', methods=['POST'])
@panel_login_required
def restart():
    mw.restartMw()
    return mw.returnData(True, '面板已重启!')

# 重启面板
@blueprint.route('/restart_server', endpoint='restart_server', methods=['POST'])
@panel_login_required
def restart_server():
    if mw.isAppleSystem():
        return mw.returnData(False, "开发环境不可重起!")
    sys.restartServer()
    return mw.returnData(True, '正在重启服务器!')

# 设置
@blueprint.route('/set_control', endpoint='set_control', methods=['POST'])
@panel_login_required
def set_control():
    stype = request.form.get('type', '')
    day = request.form.get('day', '')

    

    if stype == '0':
        _day = int(day)
        if _day < 1:
            return mw.returnData(False, "保存天数异常!")
        thisdb.setOption('monitor_day', day, type='monitor')
        thisdb.setOption('monitor_status', 'close', type='monitor')
        return mw.returnData(True, "关闭监控成功!")
    elif stype == '1':
        _day = int(day)
        if _day < 1:
            return mw.returnData(False, "保存天数异常!")

        thisdb.setOption('monitor_day', day, type='monitor')
        thisdb.setOption('monitor_status', 'open', type='monitor')
        return mw.returnData(True, "开启监控成功!")
    elif stype == '2':
        thisdb.setOption('monitor_only_netio', 'close', type='monitor')
        return mw.returnData(True, "关闭仅统计外网成功!")
    elif stype == '3':
        thisdb.setOption('monitor_only_netio', 'open', type='monitor')
        return mw.returnData(True, "开启仅统计外网成功!")
    elif stype == 'del':
        if not mw.isRestart():
            return mw.returnData(False, '请等待所有安装任务完成再执行')
        monitor.instance().clearDbFile()
        return mw.returnData(True, "清空监控记录成功!")
    else:
        monitor_status = thisdb.getOption('monitor_status', default='open', type='monitor')
        monitor_day = thisdb.getOption('monitor_day', default='30', type='monitor')
        monitor_only_netio = thisdb.getOption('monitor_only_netio', default='open', type='monitor')
        data = {}
        data['day'] = monitor_day
        if monitor_status == 'open':   
            data['status'] = True
        else:
            data['status'] = False
        if monitor_only_netio == 'open':
            data['stat_all_status'] = True
        else:
            data['stat_all_status'] = False

        return data

    return mw.returnData(False, "异常!")

# 进程管理页面
@blueprint.route('/process', endpoint='process')
@panel_login_required
def process():
    name = thisdb.getOption('template', default='default')
    return render_template('%s/process.html' % name)

# 获取进程列表
@blueprint.route('/get_process_list', endpoint='get_process_list', methods=['POST'])
@panel_login_required
def get_process_list():
    try:
        search = request.form.get('search', '').strip()
        page = int(request.form.get('p', '1'))
        row = int(request.form.get('row', '20'))
        order = request.form.get('order', '').strip()  # 格式: "field desc" 或 "field asc"
        
        process_list = []
        try:
            pids = psutil.pids()
        except Exception as e:
            return mw.returnData(False, '获取进程ID列表失败: ' + str(e))
        
        # 限制处理的进程数量，避免超时
        max_processes = 500
        if len(pids) > max_processes and not search:
            # 如果没有搜索条件，只处理前500个进程
            pids = pids[:max_processes]
        
        # 先获取所有进程的基本信息，不计算CPU（因为会阻塞）
        for pid in pids:
            try:
                p = psutil.Process(pid)
                process_info = {}
                process_info['pid'] = pid
                
                # 基本信息
                try:
                    process_info['name'] = p.name()
                except:
                    continue
                
                try:
                    process_info['status'] = p.status()
                except:
                    process_info['status'] = 'unknown'
                
                try:
                    process_info['username'] = p.username()
                except:
                    process_info['username'] = 'unknown'
                
                # CPU使用率 - 第一次调用返回0，不阻塞
                try:
                    cpu_pct = p.cpu_percent()
                    if cpu_pct is None:
                        cpu_pct = 0.0
                    process_info['cpu_percent'] = round(cpu_pct, 2)
                except:
                    process_info['cpu_percent'] = 0.0
                
                # 内存使用
                try:
                    if mw.getOs() == 'darwin':
                        # macOS系统
                        mem_info = p.memory_info()
                        process_info['memory_rss'] = mem_info.rss
                        process_info['memory_vms'] = mem_info.vms
                        # macOS上memory_percent可能不可用
                        try:
                            mem_percent = p.memory_percent()
                        except:
                            # 计算内存百分比
                            total_mem = psutil.virtual_memory().total
                            mem_percent = (mem_info.rss / total_mem) * 100 if total_mem > 0 else 0
                        process_info['memory_percent'] = round(mem_percent, 2)
                    else:
                        mem_info = p.memory_info()
                        process_info['memory_rss'] = mem_info.rss
                        process_info['memory_vms'] = mem_info.vms
                        mem_percent = p.memory_percent()
                        process_info['memory_percent'] = round(mem_percent, 2)
                except Exception as e:
                    process_info['memory_rss'] = 0
                    process_info['memory_vms'] = 0
                    process_info['memory_percent'] = 0.0
                
                # 创建时间
                try:
                    process_info['create_time'] = int(p.create_time())
                except:
                    process_info['create_time'] = 0
                
                # 命令行
                try:
                    cmdline = p.cmdline()
                    process_info['cmdline'] = ' '.join(cmdline) if cmdline else ''
                except:
                    process_info['cmdline'] = ''
                
                # 线程数
                try:
                    process_info['num_threads'] = p.num_threads()
                except:
                    process_info['num_threads'] = 0
                
                # 父进程ID
                try:
                    process_info['ppid'] = p.ppid()
                except:
                    process_info['ppid'] = 0
                
                # 如果设置了搜索条件，进行过滤
                if search:
                    search_lower = search.lower()
                    if (search_lower not in str(process_info['pid']).lower() and
                        search_lower not in process_info['name'].lower() and
                        search_lower not in process_info['username'].lower() and
                        search_lower not in process_info['cmdline'].lower()):
                        continue
                
                process_list.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                # 忽略其他异常，继续处理下一个进程
                continue
        
        # 排序处理
        if order:
            order_parts = order.split()
            if len(order_parts) == 2:
                order_field = order_parts[0]
                order_direction = order_parts[1]
                reverse = (order_direction == 'desc')
                
                if order_field in ['pid', 'cpu_percent', 'memory_rss', 'memory_percent', 'num_threads', 'create_time']:
                    # 数值类型排序
                    process_list.sort(key=lambda x: float(x.get(order_field, 0)), reverse=reverse)
                elif order_field in ['name', 'username', 'status']:
                    # 字符串类型排序
                    process_list.sort(key=lambda x: str(x.get(order_field, '')).lower(), reverse=reverse)
            else:
                # 默认按CPU使用率排序
                process_list.sort(key=lambda x: x['cpu_percent'], reverse=True)
        else:
            # 默认按CPU使用率排序
            process_list.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        # 分页
        total = len(process_list)
        start = (page - 1) * row
        end = start + row
        paged_list = process_list[start:end]
        
        # 生成分页HTML
        try:
            page_html = mw.getPage({
                'p': page,
                'row': row,
                'tojs': 'getProcessList',
                'count': total
            }, '1,2,3,4,5,6,7,8')
        except:
            page_html = ''
        
        data = {
            'list': paged_list,
            'count': total,
            'page': page,
            'row': row,
            'page_html': page_html
        }
        
        return mw.returnData(True, 'ok', data)
    except Exception as e:
        import traceback
        error_msg = str(e) + '\n' + traceback.format_exc()
        mw.writeLog('进程管理', '获取进程列表失败: ' + error_msg)
        return mw.returnData(False, '获取进程列表失败: ' + str(e))

# 结束进程
@blueprint.route('/kill_process', endpoint='kill_process', methods=['POST'])
@panel_login_required
def kill_process():
    try:
        pid = int(request.form.get('pid', '0'))
        if pid <= 0:
            return mw.returnData(False, '无效的进程ID')
        
        # 防止误杀系统关键进程
        if pid < 100:
            return mw.returnData(False, '不能结束系统关键进程')
        
        p = psutil.Process(pid)
        process_name = p.name()
        
        # 结束进程
        p.terminate()
        
        # 等待进程结束，最多等待3秒
        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            # 如果进程没有结束，强制杀死
            p.kill()
        
        msg = mw.getInfo('结束进程[{1}][{2}]成功!', (process_name, str(pid)))
        mw.writeLog('进程管理', msg)
        return mw.returnData(True, msg)
    except psutil.NoSuchProcess:
        return mw.returnData(False, '进程不存在')
    except psutil.AccessDenied:
        return mw.returnData(False, '没有权限结束此进程')
    except Exception as e:
        return mw.returnData(False, '结束进程失败: ' + str(e))

# 获取进程详情
@blueprint.route('/get_process_info', endpoint='get_process_info', methods=['POST'])
@panel_login_required
def get_process_info():
    try:
        pid = int(request.form.get('pid', '0'))
        if pid <= 0:
            return mw.returnData(False, '无效的进程ID')
        
        p = psutil.Process(pid)
        process_info = {}
        process_info['pid'] = pid
        process_info['name'] = p.name()
        process_info['status'] = p.status()
        process_info['username'] = p.username()
        
        # CPU使用率
        try:
            process_info['cpu_percent'] = round(p.cpu_percent(interval=0.1), 2)
        except:
            process_info['cpu_percent'] = 0.0
        
        # 内存使用
        try:
            if mw.getOs() == 'darwin':
                mem_info = p.memory_info()
            else:
                mem_info = p.memory_full_info()
            process_info['memory_rss'] = mem_info.rss
            process_info['memory_vms'] = mem_info.vms
            if hasattr(mem_info, 'pss'):
                process_info['memory_pss'] = mem_info.pss
            mem_percent = p.memory_percent()
            process_info['memory_percent'] = round(mem_percent, 2)
        except:
            process_info['memory_rss'] = 0
            process_info['memory_vms'] = 0
            process_info['memory_percent'] = 0.0
        
        # 创建时间
        try:
            process_info['create_time'] = int(p.create_time())
        except:
            process_info['create_time'] = 0
        
        # 命令行
        try:
            cmdline = p.cmdline()
            process_info['cmdline'] = ' '.join(cmdline) if cmdline else ''
        except:
            process_info['cmdline'] = ''
        
        # 线程数
        try:
            process_info['num_threads'] = p.num_threads()
        except:
            process_info['num_threads'] = 0
        
        # 父进程ID
        try:
            process_info['ppid'] = p.ppid()
            if process_info['ppid'] > 0:
                pp = psutil.Process(process_info['ppid'])
                process_info['ppid_name'] = pp.name()
            else:
                process_info['ppid_name'] = 'N/A'
        except:
            process_info['ppid'] = 0
            process_info['ppid_name'] = 'N/A'
        
        # 工作目录
        try:
            process_info['cwd'] = p.cwd()
        except:
            process_info['cwd'] = 'N/A'
        
        # 打开的文件
        try:
            open_files = p.open_files()
            process_info['open_files'] = [f.path for f in open_files[:10]]  # 只显示前10个
        except:
            process_info['open_files'] = []
        
        # 网络连接
        try:
            connections = p.connections()
            process_info['connections'] = len(connections)
        except:
            process_info['connections'] = 0
        
        return mw.returnData(True, 'ok', process_info)
    except psutil.NoSuchProcess:
        return mw.returnData(False, '进程不存在')
    except Exception as e:
        return mw.returnData(False, '获取进程信息失败: ' + str(e))




