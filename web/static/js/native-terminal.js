/**
 * 原生终端实现 - 使用 pty 直接创建系统 shell
 * 不依赖 SSH，直接使用系统的 shell
 */
function NativeTerminal(el, config) {
    if (typeof config == "undefined") {
        config = {};
    }
    this.el = el;
    this.id = config.id || 'native-terminal';
    this.ws = null; // websocket对象
    this.route = 'native_terminal'; // SocketIO 路由
    this.term = null; // term对象
    this.fontSize = config.fontSize || 14; // 终端字体大小
    this.term_timer = null;
    this.is_connected = false;
    this.callback_close = null;
    this.callback_connected = null;
    this.callback_exit = null;
    this.run();
}

NativeTerminal.prototype = {

    registerCloseCallBack: function(callback) {
        this.callback_close = callback;
    },

    registerConnectedCallBack: function(callback) {
        this.callback_connected = callback;
    },

    registerExitCallBack: function(callback) {
        this.callback_exit = callback;
    },

    connectWs: function() {
        this.ws = io.connect();
    },

    close: function() {
        if (this.term_timer) {
            clearInterval(this.term_timer);
            this.term_timer = null;
        }
        if (this.ws) {
            this.ws.disconnect();
            this.ws.close();
        }
        if (this.term) {
            this.term.destroy();
        }
    },

    on_message: function(ws_event) {
        if (this.term && ws_event.data) {
            this.term.write(ws_event.data);
        }
    },

    on_connect: function(ws_event) {
        this.is_connected = true;
        if (this.callback_connected) {
            this.callback_connected();
        }
    },

    on_reconnect: function(ws_event) {
        this.is_connected = false;
    },

    on_exit: function() {
        if (this.callback_exit) {
            this.callback_exit();
        }
    },

    send: function(data) {
        if (this.ws && this.is_connected) {
            this.ws.emit(this.route, data);
        }
    },

    resize: function(size) {
        if (this.ws && this.is_connected) {
            size['resize'] = 1;
            this.send(size);
        }
    },

    run: function() {
        var that = this;
        this.connectWs();

        // 获取容器元素
        var container = null;
        if (typeof this.el === 'string') {
            var elId = this.el.replace('#', '');
            container = document.getElementById(elId);
        } else if (this.el && typeof jQuery !== 'undefined' && this.el instanceof jQuery) {
            container = this.el[0];
        } else if (this.el && this.el.nodeType) {
            container = this.el;
        } else {
            container = document.getElementById(this.id);
        }

        if (!container) {
            console.error('无法找到终端容器元素: ' + this.el);
            return;
        }

        // 初始化终端
        var termCols = 83;
        var termRows = 21;
        this.term = new Terminal({
            fontSize: this.fontSize,
            screenKeys: true,
            useStyle: true,
            cols: termCols,
            rows: termRows
        });

        this.term.open(container);
        this.term.setOption('cursorBlink', true);

        // 绑定 SocketIO 事件
        this.ws.on('server_response', function(ev) {
            that.on_message(ev);
        });

        this.ws.on('connect', function(ev) {
            that.on_connect(ev);
        });

        this.ws.on('reconnect', function(ev) {
            that.on_reconnect(ev);
        });

        this.ws.on('exit', function(ev) {
            that.on_exit(ev);
        });

        this.ws.on('disconnect', function() {
            that.is_connected = false;
            if (that.term) {
                that.term.write('\r\n连接已断开\r\n');
            }
        });

        // 心跳检测
        if (this.ws) {
            this.term_timer = setInterval(function() {
                if (that.is_connected) {
                    // 发送空消息保持连接
                    that.send('');
                } else {
                    that.on_exit();
                }
            }, 600);
        }

        // 处理终端输入
        this.term.on('data', function(data) {
            if (that.is_connected) {
                that.send(data);
            } else {
                that.term.write('\r\n连接丢失,正在尝试重新连接...\r\n');
                // 尝试重新连接
                that.send({});
            }
        });

        // 处理终端大小变化
        this.term.on('resize', function(size) {
            if (that.is_connected) {
                that.resize({
                    cols: size.cols,
                    rows: size.rows
                });
            }
        });

        // 初始化连接 - 等待 SocketIO 连接成功后再发送
        this.term.write('\r\n正在初始化原生终端...\r\n');
        
        // 等待 SocketIO 连接成功
        var initTimer = setInterval(function() {
            if (that.ws && that.ws.connected) {
                clearInterval(initTimer);
                // 发送空对象以创建终端
                that.send({});
            }
        }, 100);
        
        // 如果 5 秒后还没连接，也尝试发送
        setTimeout(function() {
            clearInterval(initTimer);
            if (that.ws) {
                that.send({});
            }
        }, 5000);
        
        this.term.focus();
    }
};
