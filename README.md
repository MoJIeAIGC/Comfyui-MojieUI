# MJApplication_server_new 项目部署文档

## 一、项目概述
mjAI 是一个集成了多种功能的项目，使用前后端分离的开发模式，涉及模板图片生成、队列服务管理、ComfyUI 任务处理等多个模块。本项目依赖于 ComfyUI、Redis 和 MySQL 等服务，以下是详细的部署说明。

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
python main.py --listen 0.0.0.0 --port 1004
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

## 五、抠图服务配置
根据操作系统的不同，选择合适的安装方式：
### 5.1 下载模型
通过下方地址下载模型文件，放在BiRefNet目录下：
```bash
https://huggingface.co/yiwangsimple/BiRefNet-general-epoch_244/tree/main
```
### 5.2 安装 Python 依赖
在BiRefNet目录下，执行以下命令安装 Python 依赖：
```bash
pip install -r requirements.txt
```
### 5.3 运行 flask 项目
在项目根目录下，执行以下命令启动 Django 项目：
```bash
python app.py --listen 0.0.0.0 --port 8000
```

## 六、后端项目配置
### 6.1 克隆项目代码
从代码仓库克隆项目代码到本地：
```bash
git clone <项目仓库地址>
cd mjAI/MJApplication_server_new
```

### 6.2 安装 Python 依赖
在项目根目录下，执行以下命令安装 Python 依赖：
```bash
pip install -r requirements.txt
```

### 6.3 配置项目参数
打开 `config/config.ini` 文件，确保以下基础配置项正确，其他的根据需要自行配置：
```ini
[mysql]
name = MJApplicationDate
user = root
password = mojie0303
host = 127.0.0.1
port = 3306

[redis]
locate = redis://127.0.0.1:6379/6
```

## 七、启动项目
### 7.1 生成并执行迁移
Django 内置了manage.py工具，用于处理数据库迁移：：
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7.2 运行 Django 项目
在项目根目录下，执行以下命令启动 Django 项目：
```bash
python manage.py runserver 0.0.0.0:9152
```
### 7.2 验证项目运行
打开浏览器，访问 `http://127.0.0.1:8000`，确保项目正常运行。
## 八、前端项目
前端项目位于mojie-front目录下，使用Vue3+Vite进行开发。
### 安装依赖

bash
yarn install
```

### 开发环境

```bash
# 启动开发服务器
yarn dev

# 启动开发服务器并指定端口
yarn dev --port 8080

# 启动开发服务器并启用 HTTPS
yarn dev --https
```

### 生产环境

```bash
# 构建生产环境
yarn build

# 预览生产环境
yarn preview
```
## 九、后台项目（可选）
### 安装依赖
前端项目位于mojie-front-back目录下。
```bash
yarn install
```

### 开发环境

```bash
# 启动开发服务器
yarn dev

# 启动开发服务器并指定端口
yarn dev --port 8080

# 启动开发服务器并启用 HTTPS
yarn dev --https
```

### 生产环境

```bash
# 构建生产环境
yarn build

# 预览生产环境
yarn preview
```
