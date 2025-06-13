# MJApplication_server_new 项目部署文档

## 一、项目概述
MJApplication_server_new 是一个集成了多种功能的项目，涉及模板图片生成、队列服务管理、ComfyUI 任务处理等多个模块。本项目依赖于 ComfyUI、Redis 和 MySQL 等服务，以下是详细的部署说明。

## 二、环境准备
### 2.1 系统要求
- 支持 Linux、Windows 或 macOS 操作系统。
- 建议使用 8GB 以上内存的服务器或计算机。

### 2.2 软件依赖
- **Python 3.7 及以上版本**：用于运行项目代码。
- **Redis**：用于队列服务和缓存。
- **MySQL**：用于数据存储。
- **ComfyUI**：用于图像生成和处理。

## 三、ComfyUI 部署
### 3.1 下载和安装 ComfyUI
从 ComfyUI 的官方仓库（如 GitHub）下载最新版本的代码，并解压到指定目录。

### 3.2 配置 ComfyUI
修改 ComfyUI 的配置文件，确保其监听在 1004 端口。具体操作如下：
1. 找到 ComfyUI 的配置文件（通常为 `config.ini` 或类似名称）。
2. 找到 `server_address` 配置项，将其修改为 `172.31.16.2:1004`（根据实际情况调整 IP 地址）。

### 3.3 启动 ComfyUI
在终端中进入 ComfyUI 的目录，执行以下命令启动服务：
```bash
python main.py
```
确保服务正常启动，并且监听在 1004 端口。

## 四、Redis 与 MySQL 容器化部署

### 4.1 启动容器
在项目根目录下，执行以下命令启动 Redis 和 MySQL 容器：
- **Linux**：启动 Redis 和 MySQL 容器。
```bash
docker-compose up -d
```
### 4.2 验证容器状态
执行以下命令查看容器状态：
```bash
docker-compose ps
```
确保 Redis 和 MySQL 容器正常运行。

## 五、MySQL 部署
### 5.1 安装 MySQL
根据操作系统的不同，选择合适的安装方式：
- **Linux**：使用包管理器（如 `apt` 或 `yum`）安装 MySQL。
```bash
sudo apt-get install mysql-server
```
- **Windows**：从 MySQL 官方网站下载 Windows 版本的安装包，并按照提示进行安装。
- **macOS**：使用 Homebrew 安装 MySQL。
```bash
brew install mysql
```

### 5.2 配置 MySQL
在安装过程中，设置 MySQL 的 root 用户密码。安装完成后，启动 MySQL 服务，并使用以下命令登录：
```bash
mysql -u root -p
```
创建项目所需的数据库：
```sql
CREATE DATABASE MJApplicationDate;
```

### 5.3 创建用户并授权
为项目创建一个专用的 MySQL 用户，并授予其对 `MJApplicationDate` 数据库的访问权限：
```sql
CREATE USER 'root'@'localhost' IDENTIFIED BY 'mojie0303';
GRANT ALL PRIVILEGES ON MJApplicationDate.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

## 六、项目配置
### 6.1 克隆项目代码
从代码仓库克隆项目代码到本地：
```bash
git clone <项目仓库地址>
cd MJApplication_server_new
```

### 6.2 安装 Python 依赖
在项目根目录下，执行以下命令安装 Python 依赖：
```bash
pip install -r requirements.txt
```

### 6.3 配置项目参数
打开 `config/config.ini` 文件，确保以下配置项正确：
```ini
[mysql]
name = MJApplicationDate
user = root
password = mojie0303
host = 127.0.0.1
port = 3306

[redis]
locate = redis://127.0.0.1:6379/6

[comfyuiTextImage]
server_address = 172.31.16.2:1004
workflow_file = workflows/text_to_image.json
username = cynic
password = $2b$12$YMAgFLqFJUj7hnwd/5gB6uoyolJOvM3O.ZwUePt7JD/K8Bv7GkMkK
```

## 七、启动项目
### 7.1 运行 Django 项目
在项目根目录下，执行以下命令启动 Django 项目：
```bash
python manage.py runserver
```

### 7.2 验证项目运行
打开浏览器，访问 `http://127.0.0.1:8000`，确保项目正常运行。

## 八、注意事项
### 8.1 支付系统
- **支付配置**：确保正确配置各支付平台的密钥和证书，生产环境使用 HTTPS，配置正确的回调地址。
- **安全性**：所有支付回调必须验证签名，敏感信息（如密钥）不要提交到代码仓库，使用环境变量或配置文件管理敏感信息。
- **异常处理**：支付失败要有重试机制，记录详细的错误日志，实现支付超时处理。
- **对账**：定期与支付平台对账，记录支付流水号，保存原始响应数据。

### 8.2 其他注意事项
- 确保 ComfyUI、Redis 和 MySQL 服务正常运行，并且监听在正确的地址和端口。
- 在开发环境中，注意避免 Django 的自动重载导致服务重复初始化。
- 定期备份 MySQL 数据库，以防数据丢失。