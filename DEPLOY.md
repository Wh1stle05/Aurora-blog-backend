# 部署到 Vercel Hobby（serverless）

架构：**Vercel Functions (FastAPI) + Neon Postgres + Cloudflare R2 + Resend + Turnstile**

## 本次部署实况（2026-09-16）

| 项 | 值 |
| --- | --- |
| Vercel 项目 | `wh1stle05s-projects/aurora-blog-backend`（GitHub 生产分支 `master`） |
| 函数区域 | `sin1`（新加坡，来自 `vercel.json` 的 `regions`） |
| 数据库 | Neon `lingering-glade-73613632` / branch `production`，区域 `ap-southeast-1`（AWS 新加坡） |
| 迁移 | 已 `alembic upgrade head`（先 `merge` 了 refresh_tokens / post_slug 两个 head） |
| 对象存储 | Cloudflare R2 bucket `blog`，公开域 `cdn.aurorablog.me` |
| 反滥用定时入口 | `GET /api/system/cron/monitor`（`CRON_SECRET` 校验） |
| 自定义域 | `api.aurorablog.me` 已加到项目，**待 Cloudflare DNS 指向 Vercel**（`CNAME cname.vercel-dns.com` 或 `A 76.76.21.21`） |

> Neon 上不需要执行 `neon.ts` / `neon deploy` —— 那是把应用部署到 Neon 平台的流程；
> 本项目跑在 Vercel，只需要 Neon 的连接串。

Vercel 的 Python 运行时支持 ASGI 零配置部署：仓库根目录下的 `app/main.py`
里名为 `app` 的 `FastAPI` 实例会被自动识别，不需要 `vercel.json` 里的
`builds`/`routes`，也不需要 `api/index.py`。

## 1. 建数据库（Neon）

1. https://neon.com 新建项目，**区域选 AWS `ap-southeast-1`（新加坡）**，
   与 `vercel.json` 里的 `regions: ["sin1"]` 同区，否则每个请求多 100ms+。
2. 复制 **Pooled** 连接串（主机名带 `-pooler`），形如：

   ```
   postgresql://user:pass@ep-xxx-pooler.ap-southeast-1.aws.neon.tech/blogdb?sslmode=require
   ```

3. 本地（或 CI）对 Neon 执行一次迁移，**不要**在运行时跑 Alembic：

   ```bash
   cd Aurora-blog-backend
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   DATABASE_URL="<Neon pooled 连接串>" alembic upgrade head
   ```

## 2. 导入 Vercel

1. Vercel → Add New → Project → 选 `Wh1stle-Aurora-blog-backend` 仓库。
2. Framework Preset 保持自动识别（Python / FastAPI），Root Directory 用仓库根目录。
3. 环境变量（Production / Preview 都加上）：

   | 变量 | 说明 |
   | --- | --- |
   | `POSTGRES_URL` | Neon 的 **pooled** 连接串（优先级高于 `DATABASE_URL`） |
   | `ENV` | `prod` |
   | `JWT_SECRET` | 随机长字符串 |
   | `JWT_EXPIRES_MINUTES` | 如 `15` |
   | `REFRESH_TOKEN_PEPPER` | 随机长字符串 |
   | `REFRESH_TOKEN_EXPIRES_DAYS` | 如 `30` |
   | `ADMIN_EMAILS` | 管理员邮箱，逗号分隔 |
   | `CORS_ORIGINS` | `https://aurorablog.me,https://www.aurorablog.me,https://admin.aurorablog.me` |
   | `RESEND_API_KEY` / `RESEND_FROM` | 邮件验证码 |
   | `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile |
   | `R2_ENDPOINT` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | 图片存储（缺一个就会启动失败） |
   | `FRONTEND_REVALIDATE_URL` | `https://aurorablog.me/api/revalidate` |
   | `FRONTEND_REVALIDATE_SECRET` | 与前端一致 |
   | `CRON_SECRET` | 定时任务密钥（见第 3 步） |

4. 部署完成后先访问 `https://<project>.vercel.app/api/system/health`，
   返回 `{"status":"ok","database":true}` 说明应用与数据库都通了。

## 3. 定时任务（替代常驻监控循环）

serverless 下没有常驻进程，原 `monitor_system()` 循环默认关闭
（可用 `ENABLE_SYSTEM_MONITOR=1` 强开，但不建议）。

替代方案是 `GET /api/system/cron/monitor`，它执行一次反滥用检查
（5 分钟内评论数 > 50 的用户自动封禁），需要密钥：

```bash
curl -H "Authorization: Bearer $CRON_SECRET" \
  https://<project>.vercel.app/api/system/cron/monitor
# 也支持 ?secret=$CRON_SECRET
```

- **Vercel Cron（Hobby）**：Hobby 只允许「每天一次」的表达式，更频繁会导致部署失败，
  所以本仓库默认没有配置 `crons`。若要启用，在 `vercel.json` 加：
  `"crons": [{"path": "/api/system/cron/monitor", "schedule": "0 3 * * *"}]`
  （Vercel 检测到 `CRON_SECRET` 环境变量时会自动带上 `Authorization: Bearer <CRON_SECRET>`）
- **想要 5~10 分钟级别**：用外部免费定时器（cron-job.org、GitHub Actions `schedule`）
  定时请求上面的 URL，带上 `?secret=`。

## 4. serverless 相关的代码约定

- `app/db/session.py`：检测到 `VERCEL`/`SERVERLESS` 时使用 `NullPool`
  （serverless 实例会横向膨胀，连接池会打爆数据库），因此**必须**用 Neon 的
  `-pooler` 连接串；想强制用连接池可设 `DB_POOL=default`。
- `app/api/routers/monitor.py`：拆成单次执行的 `run_monitor_once()` + 自托管循环
  `monitor_system()`；`psutil` 改为延迟导入，serverless 下完全不加载。
- `app/main.py`：启动时按环境决定是否拉起监控循环。
- `Dockerfile`：已改为生产启动命令（去掉 `--reload`，监听 `$PORT`），
  供 Render / Cloud Run 等容器平台使用；Vercel 用不到它。

## 5. 免费额度与限制（Vercel Hobby，2026-09 核实）

- 每月：1,000,000 次函数调用 / 4 小时 active CPU / 360 GB·h provisioned memory /
  100 GB 流量
- 单函数：2 GB 内存（1 vCPU），最长 300s，请求与响应合计
- Python bundle 上限 500 MB（本项目依赖远低于此）
- 运行时日志只保留 1 小时
- **仅限非商业用途**（个人博客可以；挂广告/接单需要 Pro）
- Neon 免费档：0.5 GB 存储 / 100 CU·h per project / 自动 scale-to-zero，
  超限当月挂起
