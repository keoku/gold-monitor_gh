# 外部定时服务配置指南

解决 GitHub Actions cron 延迟问题（通常 15-30 分钟），使用 cron-job.org 精确触发 workflow_dispatch。

## 原理

```
cron-job.org（精确定时）
  → 调用 GitHub REST API 的 workflow_dispatch 接口
    → 触发 gold_alert.yml 工作流
      → 运行 gold_monitor.py 并发送邮件
```

## 第一步：创建 GitHub Personal Access Token (PAT)

1. 打开 https://github.com/settings/tokens?type=beta （Fine-grained tokens）
2. 点击 **Generate new token**
3. 配置：
   - Token name: `gold-monitor-cron`
   - Expiration: **建议选择 90 天或 1 年**（到期需续签，届时需同步更新 cron-job.org 中的 Header）
   - Repository access: **Only select repositories** → 选择你的 `gold-monitor_gh` 仓库
   - Permissions → Repository permissions:
     - **Actions**: Read and Write
     - **Contents**: Read
4. 点击 **Generate token**
5. **立即复制保存 token**（只显示一次！）

## 第二步：注册 cron-job.org

1. 打开 https://cron-job.org/en/signup/
2. 注册免费账号并验证邮箱

## 第三步：创建 3 个定时任务

在 cron-job.org 中创建以下 3 个 Cron Job。

> **重要**：URL 中的 `你的用户名` 需替换为你的 GitHub 用户名。

### 任务 1：早报 (北京时间 07:30)

| 设置项 | 值 |
|--------|-----|
| Title | Gold Monitor 07:30 |
| URL | `https://api.github.com/repos/你的用户名/gold-monitor_gh/actions/workflows/gold_alert.yml/dispatches` |
| Schedule | Custom: **Minute=30, Hour=7, Day=\*, Month=\*, Weekday=\*** |
| Timezone | Asia/Shanghai |

### 任务 2：午报 (北京时间 13:00)

| 设置项 | 值 |
|--------|-----|
| Title | Gold Monitor 13:00 |
| URL | `https://api.github.com/repos/你的用户名/gold-monitor_gh/actions/workflows/gold_alert.yml/dispatches` |
| Schedule | Custom: **Minute=0, Hour=13, Day=\*, Month=\*, Weekday=\*** |
| Timezone | Asia/Shanghai |

### 任务 3：晚报 (北京时间 18:00)

| 设置项 | 值 |
|--------|-----|
| Title | Gold Monitor 18:00 |
| URL | `https://api.github.com/repos/你的用户名/gold-monitor_gh/actions/workflows/gold_alert.yml/dispatches` |
| Schedule | Custom: **Minute=0, Hour=18, Day=\*, Month=\*, Weekday=\*** |
| Timezone | Asia/Shanghai |

### Advanced 设置（3 个任务相同）

在创建任务时切换到 **Advanced** 标签页：

1. **Request Method**: 选择 **POST**（默认是 GET，必须改！）

2. **Request Headers**（添加以下 4 个，逐行填入）：

| Key | Value |
|-----|-------|
| `Authorization` | `Bearer ghp_你的TOKEN` |
| `Accept` | `application/vnd.github+json` |
| `Content-Type` | `application/json` |
| `X-GitHub-Api-Version` | `2026-03-10` |

3. **Request Body**：

```json
{"ref": "main"}
```

## 第四步：测试

1. 在 cron-job.org 任意一个任务点击 **Run Now** / **Test Run**
2. 如果返回 HTTP **204 No Content** → 配置成功
3. 前往 `https://github.com/你的用户名/gold-monitor_gh/actions` 确认有新的 workflow run

### 验证成功的标志

- cron-job.org 显示 Response Code: **204**
- GitHub Actions 页面出现新的运行记录，触发方式显示为 `workflow_dispatch`

### 测试时立即收到邮件

正常的定时任务只在 07:30、13:00、18:00 附近发送邮件。如果你想在非报告时间测试邮件发送，可以：

**方法 1**：在 GitHub Actions 页面手动触发，勾选 `force_send = true`

**方法 2**：在 cron-job.org 新建一个专用测试任务，Request Body 改为：

```json
{"ref": "main", "inputs": {"force_send": "true"}}
```

点击 **Run Now** 即可强制发送邮件。

> ⚠️ 正式的 3 个定时任务**不要加** `force_send`，保持 `{"ref": "main"}` 即可。否则会跳过时间去重判断，可能重复发送。

## 常见问题

### 返回 401 Unauthorized
- PAT 过期或无效，请重新生成并更新 cron-job.org 中的 `Authorization` Header

### 返回 404 Not Found
- 检查 URL 中的用户名和仓库名是否正确
- 确认 PAT 的 Repository access 包含了目标仓库

### 返回 422 Unprocessable Entity
- 检查 Request Body 是否正确：`{"ref": "main"}`
- 确认仓库的默认分支是 `main`

## 注意事项

- PAT 到期需要重新生成并更新到 cron-job.org 的三个任务中
- cron-job.org 免费版完全够用（每天只触发 3 次）
- 原有的 GitHub Actions schedule 保留作为备份，万一外部服务宕机也不会完全停止
- 如果成功运行外部触发，可考虑移除 schedule 触发器以节省 Actions 分钟数
