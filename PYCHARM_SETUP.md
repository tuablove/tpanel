# PyCharm 启动配置指南

## 项目信息

- **启动文件**: `web/app.py`
- **工作目录**: `web/`
- **Python 版本要求**: Python 3.6 或更高版本
- **默认端口**: 7201

## 配置步骤

### 1. 打开项目

1. 在 PyCharm 中选择 `File` -> `Open`
2. 选择项目根目录 `/Users/tobin/java/git/p/tpanel`
3. 等待 PyCharm 索引项目

### 2. 配置 Python 解释器

1. 打开 `File` -> `Settings` (Windows/Linux) 或 `PyCharm` -> `Preferences` (macOS)
2. 进入 `Project: tpanel` -> `Python Interpreter`
3. 选择 Python 3.6+ 解释器
4. 如果没有虚拟环境，建议创建一个：
   - 点击齿轮图标 -> `Add...`
   - 选择 `Virtualenv Environment` 或 `Conda Environment`
   - 创建新的虚拟环境

### 3. 安装依赖

在 PyCharm 终端中执行：

```bash
cd /Users/tobin/java/git/p/tpanel
pip install -r requirements.txt
```

或者使用 PyCharm 的包管理器：
1. 打开 `File` -> `Settings` -> `Project: tpanel` -> `Python Interpreter`
2. 点击 `+` 按钮
3. 选择 `Install from requirements.txt`
4. 选择项目根目录下的 `requirements.txt`

### 4. 配置运行配置 (Run Configuration)

#### 方法一：使用 Flask 运行配置（推荐用于开发）

1. 点击右上角的运行配置下拉菜单 -> `Edit Configurations...`
2. 点击 `+` -> 选择 `Python`
3. 配置如下：
   - **Name**: `MW Panel (Flask)`
   - **Script path**: `web/app.py` (使用绝对路径或相对于项目根目录)
   - **Working directory**: `web/` (使用绝对路径: `/Users/tobin/java/git/p/tpanel/web`)
   - **Python interpreter**: 选择已配置的 Python 解释器
   - **Environment variables**: (可选) 可以添加环境变量
   - **Parameters**: (留空)

#### 方法二：使用模块运行（推荐）

1. 点击右上角的运行配置下拉菜单 -> `Edit Configurations...`
2. 点击 `+` -> 选择 `Python`
3. 配置如下：
   - **Name**: `MW Panel (Module)`
   - **Module name**: `app` (因为 app.py 在 web 目录下)
   - **Working directory**: `web/`
   - **Python interpreter**: 选择已配置的 Python 解释器
   - **Add content roots to PYTHONPATH**: ✅ 勾选
   - **Add source roots to PYTHONPATH**: ✅ 勾选

#### 方法三：直接运行脚本（最简单）

1. 右键点击 `web/app.py` 文件
2. 选择 `Run 'app'`
3. PyCharm 会自动创建运行配置

### 5. 配置环境变量（可选）

如果需要自定义配置，可以在运行配置中添加环境变量：

1. 在运行配置中，找到 `Environment variables`
2. 点击右侧的文件夹图标
3. 添加环境变量，例如：
   - `FLASK_ENV=development`
   - `FLASK_DEBUG=1`

### 6. 启动项目

1. 选择配置好的运行配置
2. 点击运行按钮（绿色三角形）或按 `Shift + F10`
3. 查看控制台输出，应该看到类似信息：
   ```
   Starting MW面板 v...
   Running on http://0.0.0.0:7201
   ```

### 7. 访问应用

在浏览器中访问：
- 本地访问: `http://localhost:7201`
- 或: `http://127.0.0.1:7201`

## 调试配置

### 配置调试器

1. 在运行配置中，勾选 `Attach to subprocess`
2. 在代码中设置断点
3. 点击调试按钮（绿色虫子图标）或按 `Shift + F9`
4. 程序会在断点处暂停

## 常见问题

### 1. 模块导入错误

**问题**: `ModuleNotFoundError: No module named 'admin'`

**解决**: 
- 确保工作目录设置为 `web/`
- 在运行配置中勾选 `Add content roots to PYTHONPATH`

### 2. 端口已被占用

**问题**: `Address already in use`

**解决**:
- 修改 `web/config.py` 中的 `DEFAULT_SERVER_PORT`
- 或在运行配置的 `Parameters` 中添加端口参数（需要修改代码支持）

### 3. 数据库文件不存在

**问题**: SQLite 数据库文件不存在

**解决**:
- 项目首次运行会自动创建数据库
- 确保 `web/data/` 目录有写权限

### 4. SocketIO 连接问题

**问题**: WebSocket 连接失败

**解决**:
- 确保安装了 `flask-socketio` 和相关依赖
- 检查防火墙设置
- 确保使用支持 WebSocket 的浏览器

## 开发模式配置

如果需要启用调试模式，可以修改 `web/config.py`:

```python
DEBUG = True
```

或者在运行配置的环境变量中添加：
```
FLASK_DEBUG=1
```

## 使用 Gunicorn 运行（生产模式）

如果需要使用 Gunicorn 运行（类似生产环境）：

1. 创建新的运行配置
2. 选择 `Python`
3. 配置：
   - **Script path**: `gunicorn` (需要先安装 gunicorn)
   - **Parameters**: `-c setting.py app:app`
   - **Working directory**: `web/`

或者直接在终端运行：
```bash
cd web
gunicorn -c setting.py app:app
```

## 注意事项

1. **工作目录很重要**: 必须设置为 `web/` 目录，否则会出现模块导入错误
2. **Python 路径**: 确保 `web/` 目录在 Python 路径中
3. **虚拟环境**: 建议使用虚拟环境隔离依赖
4. **端口冲突**: 如果 7201 端口被占用，需要修改配置或停止占用端口的进程

## 快速启动脚本

你也可以创建一个简单的启动脚本 `run_dev.py` 放在项目根目录：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

# 切换到 web 目录
web_dir = os.path.join(os.path.dirname(__file__), 'web')
os.chdir(web_dir)
sys.path.insert(0, web_dir)

# 导入并运行
from app import main
if __name__ == '__main__':
    main()
```

然后在 PyCharm 中运行这个脚本即可。
