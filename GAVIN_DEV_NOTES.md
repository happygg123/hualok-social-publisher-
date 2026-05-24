# Gavin Social Publisher 开发记录

## 当前目标

基于 `social-auto-upload` 二次开发，优先打通：

- 视频号：`sau tencent ...`
- 抖音：`sau douyin ...`
- 小红书：`sau xiaohongshu ...`
- CSV 批量发布：`publish_batch.py`

## 本机路径

Windows 路径：

```powershell
D:\workspace\gavin-social-publisher
```

WSL 路径：

```bash
/mnt/d/workspace/gavin-social-publisher
```

## 环境启动

PowerShell：

```powershell
D:
cd D:\workspace\gavin-social-publisher
.venv\Scripts\activate
```

WSL：

```bash
cd /mnt/d/workspace/gavin-social-publisher
source .venv/bin/activate
```

## 已新增命令

### 视频号登录

```powershell
sau tencent login --account gavin --headed
```

### 视频号检查

```powershell
sau tencent check --account gavin
```

### 视频号单条发布

```powershell
sau tencent upload-video `
  --account gavin `
  --file "D:\videos\test.mp4" `
  --title "测试标题" `
  --desc "测试简介" `
  --tags "采购,工厂,供应链" `
  --thumbnail "D:\videos\test.jpg" `
  --short-title "测试短标题" `
  --headed
```

## CSV 批量发布

示例文件：

```text
tasks/publish.example.csv
```

执行：

```powershell
python publish_batch.py --csv tasks\publish.example.csv --headed
```

日志输出：

```text
publish_logs/summary.json
publish_logs/records/
```

## 当前修改

- `sau_cli.py`：新增 `tencent login/check/upload-video`
- `publish_batch.py`：新增 CSV 串行批量发布脚本
- `tasks/publish.example.csv`：新增示例 CSV
- `uploader/xiaohongshu_uploader/main.py`：修复 Python 3.11 f-string 语法错误

## 下一步

1. 在 Windows PowerShell 里激活 `.venv`。
2. 先执行 `sau tencent login --account gavin --headed` 扫码保存视频号 cookie。
3. 依次执行抖音、小红书登录检查。
4. 用真实小视频做三平台单条发布测试。
5. 单条稳定后，把真实成片写入 CSV，跑 `publish_batch.py`。
