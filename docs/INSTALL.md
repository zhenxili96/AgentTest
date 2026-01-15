# 环境依赖安装指南

## 前提条件

在安装项目依赖之前，您需要先安装Python。

### 检查Python是否已安装

在命令行中运行以下命令：

```bash
python --version
```

或者：

```bash
python3 --version
```

如果显示版本号（如 `Python 3.9.0`），说明Python已安装。

## 安装Python（如果未安装）

### Windows系统

1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载最新的Python 3.x版本（推荐3.9或更高版本）
3. 运行安装程序
4. **重要**：在安装时勾选 "Add Python to PATH"
5. 完成安装后，重新打开命令行窗口

### 验证安装

安装完成后，重新打开命令行，运行：

```bash
python --version
pip --version
```

如果两个命令都能显示版本号，说明安装成功。

## 安装项目依赖

### 方法1：使用pip安装（推荐）

在项目根目录下运行：

```bash
pip install -r requirements.txt
```

如果提示权限错误，可以使用：

```bash
pip install --user -r requirements.txt
```

### 方法2：使用Python模块方式

如果 `pip` 命令不可用，可以尝试：

```bash
python -m pip install -r requirements.txt
```

### 方法3：创建虚拟环境（推荐用于开发）

1. 创建虚拟环境：
```bash
python -m venv venv
```

2. 激活虚拟环境：

   **Windows (CMD)**:
   ```bash
   venv\Scripts\activate
   ```

   **Windows (PowerShell)**:
   ```powershell
   venv\Scripts\Activate.ps1
   ```

   **Linux/Mac**:
   ```bash
   source venv/bin/activate
   ```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 依赖包列表

项目需要以下Python包：

- `requests` - HTTP请求库
- `python-dotenv` - 环境变量管理
- `openai` - OpenAI API客户端
- `schedule` - 任务调度
- `sqlalchemy` - 数据库ORM
- `beautifulsoup4` - HTML解析
- `lxml` - XML/HTML解析器
- `feedparser` - RSS/Atom解析
- `pandas` - 数据处理
- `numpy` - 数值计算
- `flask` - Web框架
- `flask-cors` - CORS支持
- `pydantic` - 数据验证

## 验证安装

安装完成后，可以运行以下命令验证：

```bash
python -c "import requests, openai, flask, sqlalchemy; print('所有依赖安装成功！')"
```

如果没有错误信息，说明依赖安装成功。

## 常见问题

### Q: 提示 "pip 不是内部或外部命令"

**解决方案**：
1. 确认Python已正确安装
2. 确认安装时勾选了 "Add Python to PATH"
3. 尝试使用 `python -m pip` 代替 `pip`

### Q: 安装速度慢或超时

**解决方案**：
1. 使用国内镜像源：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

2. 或者使用阿里云镜像：
```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### Q: 权限错误

**解决方案**：
1. 使用 `--user` 参数安装到用户目录：
```bash
pip install --user -r requirements.txt
```

2. 或者使用管理员权限运行命令行

### Q: 某些包安装失败

**解决方案**：
1. 更新pip：
```bash
python -m pip install --upgrade pip
```

2. 单独安装失败的包：
```bash
pip install 包名
```

3. 检查Python版本是否满足要求（需要Python 3.9+）
