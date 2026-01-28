// 处理排序
function listProcessOrder(skey, obj) {
    var or = getCookie('process_order');
    var orderType = 'desc';
    if(or) {
        var or_arr = or.split('|');
        if(or_arr[0] == skey) {
            if(or_arr[1] == 'desc') {
                orderType = 'asc';
            } else if(or_arr[1] == 'asc') {
                orderType = 'none';
            } else {
                orderType = 'desc';
            }
        }
    }
    setCookie('process_order', skey + '|' + orderType);
    
    // 更新所有表头的排序图标
    $("#processTable thead th").each(function() {
        $(this).find(".glyphicon-triangle-top, .glyphicon-triangle-bottom, .glyphicon-option-horizontal").remove();
        $(this).append("<span class='glyphicon glyphicon-option-horizontal' style='margin-left:5px;color:#bbb'></span>");
    });
    
    // 更新当前列的排序图标
    $(obj).find(".glyphicon-triangle-top, .glyphicon-triangle-bottom, .glyphicon-option-horizontal").remove();
    if(orderType == 'none') {
        $(obj).append("<span class='glyphicon glyphicon-option-horizontal' style='margin-left:5px;color:#bbb'></span>");
    } else if(orderType == 'asc') {
        $(obj).append("<span class='glyphicon glyphicon-triangle-bottom' style='margin-left:5px;color:#bbb'></span>");
    } else {
        $(obj).append("<span class='glyphicon glyphicon-triangle-top' style='margin-left:5px;color:#bbb'></span>");
    }
    
    getProcessList(1);
}

// 获取进程列表
function getProcessList(p) {
    var post = {};
    post['p'] = p || 1;
    post['row'] = 20;
    
    var search = $("#search_process").val();
    if(search && search.length > 0){
        post['search'] = search;
    }
    
    // 获取排序信息
    var process_order = getCookie('process_order');
    if(process_order) {
        post['order'] = process_order.replace('|', ' ');
    }
    
    var loadT = layer.load();
    $.post('/system/get_process_list', post, function(rdata) {
        layer.close(loadT);
        
        if(!rdata) {
            layer.msg('请求失败，请检查网络连接', {icon: 2});
            $("#processBody").html('<tr><td colspan="10" style="text-align:center;padding:20px;color:red;">请求失败，请检查网络连接</td></tr>');
            return;
        }
        
        if(!rdata.status) {
            var errorMsg = rdata.msg || '获取进程列表失败';
            layer.msg(errorMsg, {icon: 2, time: 3000});
            $("#processBody").html('<tr><td colspan="10" style="text-align:center;padding:20px;color:red;">' + errorMsg + '</td></tr>');
            return;
        }
        
        var data = rdata.data;
        var body = '';
        
        if(data.list && data.list.length > 0) {
            for(var i = 0; i < data.list.length; i++) {
                var p = data.list[i];
                var memory = toSize(p.memory_rss || 0);
                var memoryPercent = ((p.memory_percent || 0) * 1).toFixed(2) + '%';
                var cpuPercent = ((p.cpu_percent || 0) * 1).toFixed(2) + '%';
                var status = p.status;
                var statusClass = 'label-default';
                if(status == 'running') {
                    statusClass = 'label-success';
                } else if(status == 'sleeping') {
                    statusClass = 'label-info';
                } else if(status == 'zombie') {
                    statusClass = 'label-danger';
                }
                
                var startTime = getLocalTime(p.create_time);
                
                body += '<tr>';
                body += '<td>' + p.pid + '</td>';
                var cmdline = (p.cmdline || p.name).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                var pname = p.name.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                body += '<td><span title="' + cmdline + '">' + pname + '</span></td>';
                body += '<td>' + p.username + '</td>';
                body += '<td>' + cpuPercent + '</td>';
                body += '<td>' + memory + '</td>';
                body += '<td>' + memoryPercent + '</td>';
                body += '<td>' + p.num_threads + '</td>';
                body += '<td><span class="label ' + statusClass + '">' + status + '</span></td>';
                body += '<td>' + startTime + '</td>';
                body += '<td>';
                body += '<a class="btlink" href="javascript:;" onclick="viewProcessInfo(' + p.pid + ')">详情</a> | ';
                body += '<a class="btlink" href="javascript:;" onclick="killProcess(' + p.pid + ', ' + JSON.stringify(p.name) + ')">结束</a>';
                body += '</td>';
                body += '</tr>';
            }
        } else {
            body = '<tr><td colspan="10" style="text-align:center;padding:20px;">未找到进程</td></tr>';
        }
        
        $("#processBody").html(body);
        
        // 显示分页
        if(data && data.page_html) {
            $("#processPage").html(data.page_html);
        } else {
            $("#processPage").html('');
        }
        
        // 初始化排序图标
        initProcessOrder();
    }, 'json').fail(function(xhr, status, error) {
        layer.close(loadT);
        var errorMsg = '请求失败: ' + (error || status || '未知错误');
        layer.msg(errorMsg, {icon: 2, time: 3000});
        $("#processBody").html('<tr><td colspan="10" style="text-align:center;padding:20px;color:red;">' + errorMsg + '</td></tr>');
        console.error('获取进程列表失败:', xhr, status, error);
    });
}

// 搜索进程
function searchProcess() {
    getProcessList(1);
}

// 刷新进程列表
function refreshProcess() {
    getProcessList(1);
}

// 查看进程详情
function viewProcessInfo(pid) {
    var loadT = layer.msg('正在获取进程信息...', {icon: 16, time: 0, shade: [0.3, '#000']});
    $.post('/system/get_process_info', {'pid': pid}, function(rdata) {
        layer.close(loadT);
        
        if(!rdata.status) {
            layer.msg(rdata.msg, {icon: 2});
            return;
        }
        
        var p = rdata.data;
        var memory = toSize(p.memory_rss);
        var memoryPercent = p.memory_percent.toFixed(2) + '%';
        var cpuPercent = p.cpu_percent.toFixed(2) + '%';
        var startTime = getLocalTime(p.create_time);
        
        var openFilesHtml = '';
        if(p.open_files && p.open_files.length > 0) {
            for(var i = 0; i < p.open_files.length; i++) {
                openFilesHtml += '<tr><td>' + p.open_files[i] + '</td></tr>';
            }
        } else {
            openFilesHtml = '<tr><td>无</td></tr>';
        }
        
        var content = '<div class="pd15">';
        content += '<div class="divtable">';
        content += '<table class="table">';
        content += '<tbody>';
        content += '<tr><th width="100">PID</th><td>' + p.pid + '</td>';
        content += '<th width="100">进程名</th><td>' + p.name + '</td></tr>';
        content += '<tr><th>状态</th><td>' + p.status + '</td>';
        content += '<th>用户</th><td>' + p.username + '</td></tr>';
        content += '<tr><th>CPU使用率</th><td>' + cpuPercent + '</td>';
        content += '<th>内存使用</th><td>' + memory + ' (' + memoryPercent + ')</td></tr>';
        content += '<tr><th>线程数</th><td>' + p.num_threads + '</td>';
        content += '<th>网络连接</th><td>' + p.connections + '</td></tr>';
        content += '<tr><th>父进程</th><td>' + p.ppid_name + ' (' + p.ppid + ')</td>';
        content += '<th>启动时间</th><td>' + startTime + '</td></tr>';
        content += '<tr><th>工作目录</th><td colspan="3">' + p.cwd + '</td></tr>';
        content += '<tr><th>命令行</th><td colspan="3"><code style="word-break:break-all;">' + (p.cmdline || 'N/A') + '</code></td></tr>';
        content += '</tbody>';
        content += '</table>';
        content += '</div>';
        
        if(p.open_files && p.open_files.length > 0) {
            content += '<h4 class="mt15">打开的文件</h4>';
            content += '<div class="divtable">';
            content += '<table class="table">';
            content += '<thead><tr><th>文件路径</th></tr></thead>';
            content += '<tbody>' + openFilesHtml + '</tbody>';
            content += '</table>';
            content += '</div>';
        }
        
        content += '</div>';
        
        layer.open({
            type: 1,
            shift: 5,
            closeBtn: 1,
            area: ['800px', '600px'],
            title: '进程详情 [' + p.name + ']',
            content: content
        });
    }, 'json');
}

// 结束进程
function killProcess(pid, name) {
    layer.confirm('确定要结束进程 [' + name + '] (PID: ' + pid + ') 吗？<br/>此操作可能会影响服务器运行，请谨慎操作！', {
        title: '结束进程',
        closeBtn: 2,
        icon: 3
    }, function(index) {
        var loadT = layer.msg('正在结束进程...', {icon: 16, time: 0, shade: [0.3, '#000']});
        $.post('/system/kill_process', {'pid': pid}, function(rdata) {
            layer.close(loadT);
            layer.close(index);
            layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
            if(rdata.status) {
                setTimeout(function() {
                    getProcessList(1);
                }, 1000);
            }
        }, 'json');
    });
}
