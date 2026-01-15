# Cursor Terminal中Python命令不可用的解决方案

## 问题描述

在Windows命令提示符（CMD）中可以运行`python`命令，但在Cursor的Terminal中无法运行。

## 原因分析

Cursor的Terminal默认使用PowerShell，而您平时使用的是CMD。两者对环境变量的加载方式不同：

1. **CMD**：直接使用系统PATH环境变量
2. **PowerShell**：可能需要重新加载环境变量，或者使用不同的执行策略

## 解决方案

### 方案1：使用批处理文件安装（推荐）

我已经创建了 `install_dependencies.bat` 文件，您可以：

1. 在Windows资源管理器中找到项目文件夹
2. 双击运行 `install_dependencies.bat`
3. 等待安装完成

或者在Cursor的Terminal中运行：
```powershell
cmd /c install_dependencies.bat
```

### 方案2：在CMD中安装

1. 打开Windows命令提示符（CMD）
2. 切换到项目目录：
   ```cmd
   cd D:\dev\financial-agent
   ```
3. 运行安装命令：
   ```cmd
   pip install -r requirements.txt
   ```
   或者：
   ```cmd
   python -m pip install -r requirements.txt
   ```

### 方案3：在Cursor中使用完整路径

如果Python在WindowsApps目录下，可以直接使用完整路径：

```powershell
C:\Users\zhenx\AppData\Local\Microsoft\WindowsApps\python.exe -m pip install -r requirements.txt
```

### 方案4：刷新PowerShell环境变量

在PowerShell中运行以下命令重新加载环境变量：

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
python --version
```

然后运行：
```powershell
python -m pip install -r requirements.txt
```

### 方案5：更改Cursor的默认终端为CMD

1. 打开Cursor设置（Ctrl+,）
2. 搜索 "terminal.integrated.defaultProfile.windows"
3. 将值改为 "Command Prompt" 或 "cmd"

或者在Terminal中点击右上角的下拉菜单，选择"Command Prompt"

## 验证安装

安装完成后，可以在CMD或PowerShell中验证：

```bash
python -c "import requests, openai, flask; print('安装成功！')"
```

## 使用建议

- **开发时**：建议使用CMD或者在CMD中运行安装命令
- **日常使用**：可以使用批处理文件 `install_dependencies.bat`
- **VS Code/Cursor**：可以更改默认终端为CMD以避免此类问题

## 常见问题

### Q: 为什么WindowsApps目录下的Python找不到？

A: Windows Store版本的Python有时候在PowerShell中需要额外配置。使用完整路径或CMD可以解决。

### Q: 安装后还是无法在Cursor Terminal中使用python？

A: 重启Cursor编辑器，或者使用方案4刷新环境变量。

### Q: 可以使用虚拟环境吗？

A: 可以！即使Terminal有问题，也可以在CMD中创建虚拟环境：
```cmd
cd D:\dev\financial-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
