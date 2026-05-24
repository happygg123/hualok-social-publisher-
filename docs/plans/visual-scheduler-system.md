# Gavin Social Publisher 可视化和定时系统方案

## 结论

需要做一个轻量可视化系统，但不要一开始做复杂后台。

原因：
- 批量发布任务是长流程，看不到当前状态会很难判断卡在哪个平台。
- 定时任务更需要可视化，否则不知道哪些待发、哪些已发、哪些失败。
- 后续视频号原创声明、失败重试、Telegram 回传，都需要统一任务状态。

## MVP 形态

优先做本机 Windows 可跑的轻量 Web 面板：

- 后端：FastAPI 或 Flask
- 存储：SQLite
- 前端：简单 HTML + Bootstrap/原生 JS，不做复杂 Vue
- 运行位置：D:\workspace\gavin-social-publisher
- 真实发布仍由 Windows PowerShell/本机 Chrome 执行

## 页面

### 1. 任务列表页

字段：
- ID
- 视频路径
- 封面路径
- 标题
- 平台：视频号/抖音/小红书
- 发布时间
- 状态：待发布/发布中/成功/失败/待原创声明
- 最新错误
- 操作：查看日志、重试、取消、打开截图

### 2. 新建任务页

一次填写：
- 视频
- 封面
- 标题
- 简介
- 标签
- 平台勾选
- 立即发布/定时发布
- 视频号发布后是否尝试后台原创声明

保存后自动拆分平台任务。

### 3. 日志详情页

显示：
- 每个平台 stdout/stderr
- 截图路径
- 发布命令
- 开始/结束时间

## 数据库表

### publish_jobs

- id
- video
- cover
- title
- desc
- tags
- platforms
- schedule_time
- status
- created_at
- updated_at

### publish_attempts

- id
- job_id
- platform
- account
- status
- command
- stdout
- stderr
- screenshot
- started_at
- finished_at

### post_actions

- id
- job_id
- platform
- action_type，例如 tencent_declare_original
- status
- stdout
- stderr
- screenshot
- started_at
- finished_at

## 调度规则

第一版不用 Celery，不引入复杂服务。

用一个本机常驻 Python worker：

```powershell
python publisher_worker.py
```

worker 每 30 秒扫描 SQLite：

```text
status = queued
schedule_time <= now
```

然后调用：

```powershell
python publish_once_to_many.py --job-id xxx
```

或直接复用内部函数执行。

## 定时功能

定时不是靠各平台自己的定时发布为主，而是：

```text
我们自己的系统到点再执行发布
```

优点：
- 各平台定时能力不一致
- 页面定时选择器容易变
- 本地系统统一可控
- 状态更清楚

如果某个平台本身定时很稳定，以后再加平台内定时。

## 视频号原创声明

不要放在主发布流程。

流程：

```text
视频号发布成功 -> 创建 post_action: tencent_declare_original -> 后台执行 -> 成功/失败单独记录
```

如果失败，不影响抖音/小红书。

## 实施顺序

1. SQLite 任务数据库
2. 把 publish_once_to_many.py 支持从 job_id 读取任务
3. 本机 worker 扫描定时任务
4. 简单 Web 面板：列表 + 新建 + 日志
5. 失败重试
6. 视频号原创声明 post_action
7. Telegram 成功/失败通知

## 不做

第一版不做：
- 多用户权限
- 复杂 Vue 前端
- 云端 VPS 发布
- 并发发布
- 坐标硬点
- 强依赖平台内定时

