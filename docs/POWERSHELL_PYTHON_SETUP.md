# PowerShell中使用Python的配置指南

## 问题描述

在Windows PowerShell中无法使用`python`命令，通常是因为Python没有正确添加到系统PATH环境变量中。

## 快速解决方案

### 方案1：刷新PowerShell环境变量（临时解决）

在PowerShell中运行以下命令重新加载环境变量：

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
python --version
```

这个方法只对当前PowerShell会话有效，关闭后需要重新运行。

### 方案2：永久添加到PATH环境变量（推荐）

#### 方法A：通过图形界面添加

1. **找到Python安装路径**
   - 常见路径：
     - `C:\Users\<用户名>\AppData\Local\Programs\Python\Python3xx\`
     - `C:\Python3xx\`
     - `C:\Users\<用户名>\AppData\Local\Microsoft\WindowsApps\`（Windows Store版本）

2. **添加到系统PATH**
   - 按 `Win + R`，输入 `sysdm.cpl`，回车
   - 点击"高级"选项卡
   - 点击"环境变量"按钮
   - 在"系统变量"部分找到`Path`，点击"编辑"
   - 点击"新建"，添加Python的安装目录（例如：`C:\Python39\`）
   - 再添加Scripts目录（例如：`C:\Python39\Scripts\`）
   - 点击"确定"保存所有更改

3. **重新打开PowerShell验证**
   ```powershell
   python --version
   pip --version
   ```

#### 方法B：通过PowerShell命令添加（需要管理员权限）

1. **以管理员身份运行PowerShell**
   - 右键点击开始菜单
   - 选择"Windows PowerShell (管理员)"或"终端 (管理员)"

2. **查找Python安装路径**
   ```powershell
   Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
   ```
   
   或者手动查找：
   ```powershell
   # 查找Python安装位置
   where.exe python
   ```

3. **添加到用户PATH（推荐，不需要管理员权限）**
   ```powershell
   # 替换为您的Python实际路径
   $pythonPath = "C:\Python39"
   $pythonScripts = "C:\Python39\Scripts"
   
   $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
   $newPath = "$currentPath;$pythonPath;$pythonScripts"
   [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
   ```

4. **添加到系统PATH（需要管理员权限）**
   ```powershell
   # 替换为您的Python实际路径
   $pythonPath = "C:\Python39"
   $pythonScripts = "C:\Python39\Scripts"
   
   $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
   $newPath = "$currentPath;$pythonPath;$pythonScripts"
   [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
   ```

5. **重新打开PowerShell验证**
   ```powershell
   python --version
   ```

### 方案3：使用完整路径（临时方案）

如果不想修改PATH，可以直接使用Python的完整路径：

```powershell
# 替换为您的Python实际路径
C:\Python39\python.exe --version
C:\Python39\python.exe -m pip install -r requirements.txt
```

### 方案4：重新安装Python并勾选"Add Python to PATH"

如果Python还未安装或安装时未勾选"Add Python to PATH"：

1. 下载Python：https://www.python.org/downloads/
2. 运行安装程序
3. **重要**：勾选 "Add Python to PATH" 选项
4. 完成安装
5. 重新打开PowerShell

### 方案5：使用py启动器（Windows专用）

Windows Python安装通常包含`py`启动器，即使PATH未配置也可以使用：

```powershell
py --version
py -m pip install -r requirements.txt
```

## 验证配置

配置完成后，在PowerShell中运行以下命令验证：

```powershell
# 检查Python版本
python --version

# 检查pip版本
pip --version

# 检查Python路径
(Get-Command python).Source

# 测试安装包
python -c "print('Python配置成功！')"
```

## 常见问题

### Q: 添加PATH后仍然无法使用python命令？

**解决方案**：
1. 关闭所有PowerShell窗口，重新打开一个新的PowerShell
2. 检查PATH是否正确添加：
   ```powershell
   $env:Path -split ';' | Select-String Python
   ```
3. 确认Python安装目录确实存在
4. 尝试使用`py`启动器

### Q: PowerShell显示"无法加载文件，因为在此系统上禁止运行脚本"？

这是PowerShell的执行策略问题，解决方法是：

```powershell
# 以管理员身份运行PowerShell，然后执行：
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

或者使用更宽松的策略（不推荐）：
```powershell
Set-ExecutionPolicy Bypass -Scope Process
```

### Q: Windows Store版本的Python无法使用？

Windows Store版本的Python路径通常在：
```
C:\Users\<用户名>\AppData\Local\Microsoft\WindowsApps\
```

将其添加到PATH即可。或者使用`py`启动器。

### Q: 多个Python版本如何管理？

Windows的`py`启动器可以管理多个版本：
```powershell
# 查看所有安装的Python版本
py --list

# 使用特定版本
py -3.9 --version
py -3.10 --version

# 使用最新版本
py -3 --version
```

## 推荐做法

1. **开发环境**：使用虚拟环境隔离项目依赖
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # 如果执行策略有问题，使用: venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

2. **生产环境**：确保Python已添加到系统PATH，并验证可正常使用

3. **多项目开发**：每个项目使用独立的虚拟环境

## 相关文档

- `docs/INSTALL.md` - 完整的安装指南
- `docs/TERMINAL_FIX.md` - Cursor Terminal相关问题
- `docs/QUICKSTART.md` - 快速开始指南