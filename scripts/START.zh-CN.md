# 后端启动指南

本文档说明如何在生产分支中使用 `scripts/start.sh` 启动后端服务。

## 脚本会做什么

`scripts/start.sh` 是这个后端项目的一键启动入口。它会依次完成以下工作：

- 从 `.env` 读取环境变量
- 检查 `DOMAIN` 对应的 HTTPS 证书是否已经存在
- 如果证书不存在，使用 Certbot 申请首个证书
- 启动 PostgreSQL
- 执行 Alembic 数据库迁移
- 构建并启动后端与 Nginx 容器
- 在宿主机启动一个后台证书续期循环

## 前置要求

在运行脚本前，请先确认服务器满足以下条件：

- 已安装 Docker
- 可以使用 `docker compose`
- `80` 与 `443` 端口已对外开放
- `api.aurorablog.me` 的 DNS 已指向当前服务器

默认假设你是在后端仓库根目录执行本分支。

## 必要文件

启动前至少需要以下文件：

- `.env`
- `docker-compose.yml`
- `scripts/start.sh`

先通过 `.env.example` 生成 `.env`：

```bash
cp .env.example .env
```

## `.env` 必填项

至少需要在 `.env` 中填好以下生产环境配置：

```env
ENV=prod
DATABASE_URL=postgresql+psycopg://blog:blogpass@db:5432/blogdb
JWT_SECRET=replace-with-a-long-random-secret
ADMIN_EMAILS=your-admin-email@example.com
CORS_ORIGINS=https://aurorablog.me,https://www.aurorablog.me,https://admin.aurorablog.me
RESEND_API_KEY=...
RESEND_FROM=Aurora Blog <no-reply@aurorablog.me>
TURNSTILE_SECRET_KEY=...
R2_ENDPOINT=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=...
R2_PUBLIC_BASE_URL=https://cdn.aurorablog.me
REFRESH_TOKEN_EXPIRES_DAYS=30
REFRESH_TOKEN_PEPPER=replace-with-a-random-secret
DOMAIN=api.aurorablog.me
CERTBOT_EMAIL=your-email@example.com
```

说明：

- `CERTBOT_EMAIL` 是强制项，缺失时脚本会直接退出。
- `DOMAIN` 默认是 `api.aurorablog.me`，但建议在 `.env` 中显式写出。
- 当前生产环境文件存储只支持 R2，因此 R2 相关变量必须完整配置。

## 首次启动

在仓库根目录运行：

```bash
bash scripts/start.sh
```

首次执行时，脚本会按以下顺序运行：

1. 加载 `.env`
2. 创建 `nginx/certbot`、`nginx/letsencrypt` 和 `logs`
3. 检查 `nginx/letsencrypt/live/$DOMAIN/fullchain.pem` 是否存在
4. 如果证书不存在，则使用 Certbot 的 standalone 模式在 `80` 端口申请证书
5. 启动数据库容器
6. 执行 `alembic upgrade head`
7. 构建并启动 `backend` 和 `nginx`
8. 如果当前没有续期进程，则在后台启动证书续期循环

如果一切成功，脚本最后会输出：

```text
Startup complete.
Verify:
  curl https://<DOMAIN>/
  curl https://<DOMAIN>/api/system/routes
```

## 后续重复启动

后续部署更新时，仍然执行同一条命令：

```bash
bash scripts/start.sh
```

如果证书已经存在，脚本会跳过首次申请证书的步骤，继续执行：

- `docker compose up -d db`
- `docker compose run --rm backend alembic upgrade head`
- `docker compose up -d --build backend nginx`

也就是说，后续代码更新后仍然可以重复使用同一个启动命令。

## 证书续期

脚本会在宿主机启动一个后台续期循环：

- 进程号会写入 `.renew.pid`
- 日志会写入 `logs/renew.log`
- 每 `12` 小时运行一次
- 成功续期后会在容器内重载 Nginx

只有在 `.renew.pid` 不存在，或者记录的进程已经失效时，脚本才会重新启动续期循环。

## 常用命令

查看容器状态：

```bash
docker compose ps
```

查看后端日志：

```bash
docker compose logs -f backend
```

查看 Nginx 日志：

```bash
docker compose logs -f nginx
```

查看证书续期日志：

```bash
tail -f logs/renew.log
```

停止整个栈：

```bash
docker compose down
```

只停止续期循环：

```bash
kill "$(cat .renew.pid)"
rm -f .renew.pid
```

## 常见问题

### `.env` 缺失

报错：

```text
Missing .env. Copy .env.example to .env and fill required values.
```

处理方式：

- 创建 `.env`
- 补齐必填配置
- 再次执行脚本

### `CERTBOT_EMAIL` 缺失

报错：

```text
CERTBOT_EMAIL is required in .env
```

处理方式：

- 在 `.env` 中添加 `CERTBOT_EMAIL`
- 重新执行脚本

### 证书申请失败

常见原因：

- `DOMAIN` 还没有正确解析到服务器
- 防火墙或云服务安全组没有放行 `80` 端口
- 已有其他进程占用了 `80` 端口

处理方式：

- 检查 `api.aurorablog.me` 的 DNS
- 确认 `80` 端口可以被公网访问
- 停掉占用 `80` 端口的其他服务

### 数据库迁移失败

如果 `docker compose run --rm backend alembic upgrade head` 失败：

- 查看脚本输出的后端报错信息
- 检查 `.env` 中数据库连接是否正确
- 修复连接或迁移问题后重新执行脚本

## 推荐部署流程

首次部署服务器：

```bash
git checkout release1.0
cp .env.example .env
bash scripts/start.sh
```

后续更新：

```bash
git pull
bash scripts/start.sh
```
