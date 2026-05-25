from __future__ import annotations

import html
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from publisher_db import cancel_job, create_job, get_job, init_db, list_attempts, list_jobs, queue_job

HOST = "127.0.0.1"
PORT = 8765
BASE_DIR = Path(__file__).resolve().parent
SCREENSHOT_RE = re.compile(r"([A-Za-z]:\\[^\n\r\t<>|]+?\.(?:png|jpg|jpeg|webp)|/[^^\n\r\t<>|]+?\.(?:png|jpg|jpeg|webp))", re.I)

STATUS_META = {
    "queued": ("待发布", "queued", "⏱"),
    "running": ("发布中", "running", "●"),
    "success": ("已成功", "success", "✓"),
    "partial_success": ("部分成功", "warning", "!"),
    "failed": ("失败", "failed", "×"),
    "cancelled": ("已取消", "cancelled", "–"),
}
PLATFORM_LABELS = {"tencent": "视频号", "douyin": "抖音", "xiaohongshu": "小红书"}


def esc(value) -> str:
    return html.escape(str(value or ""))


def win_path(value: str) -> str:
    if not value:
        return ""
    return value.replace("/mnt/d/", "D:\\").replace("/mnt/c/", "C:\\").replace("/", "\\") if value.startswith("/mnt/") else value


def status_badge(status: str) -> str:
    label, cls, icon = STATUS_META.get(status or "", (status or "未知", "neutral", "•"))
    return f"<span class='badge badge-{cls}'><span>{icon}</span>{esc(label)}</span>"


def platform_pills(platforms: str) -> str:
    names = [p.strip() for p in (platforms or "").split(",") if p.strip()]
    if not names:
        return "<span class='muted'>未设置</span>"
    return "".join(f"<span class='platform-pill'>{esc(PLATFORM_LABELS.get(p, p))}</span>" for p in names)


def truncate(value: str, length: int = 140) -> str:
    value = str(value or "")
    return value if len(value) <= length else value[:length] + "…"


def extract_screenshots(*texts: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for text in texts:
        for m in SCREENSHOT_RE.finditer(text or ""):
            raw = m.group(1).strip().strip('"\'')
            normalized = raw.replace("\\", "/")
            if re.match(r"^[A-Za-z]:/", normalized):
                normalized = "/mnt/" + normalized[0].lower() + normalized[2:]
            if normalized not in seen and Path(normalized).exists():
                seen.add(normalized)
                out.append(normalized)
    return out


def file_url(path: str) -> str:
    return "/file?path=" + quote(path)


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:#08090a; --panel:#0f1011; --surface:#17181a; --surface2:#1f2024;
      --text:#f7f8f8; --sub:#d0d6e0; --muted:#8a8f98; --faint:#62666d;
      --line:rgba(255,255,255,.08); --line-soft:rgba(255,255,255,.05);
      --brand:#5e6ad2; --brand2:#7170ff; --green:#10b981; --red:#ef4444; --amber:#f59e0b;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(circle at 18% -10%, rgba(94,106,210,.28), transparent 34%), var(--bg); color:var(--text); font-family:'Inter', system-ui, -apple-system, 'Microsoft YaHei', sans-serif; font-feature-settings:'cv01','ss03'; }}
    a {{ color:inherit; text-decoration:none; }}
    .shell {{ min-height:100vh; display:grid; grid-template-columns:260px 1fr; }}
    .sidebar {{ position:sticky; top:0; height:100vh; padding:26px 18px; background:rgba(15,16,17,.78); border-right:1px solid var(--line-soft); backdrop-filter:blur(18px); }}
    .brand {{ display:flex; gap:12px; align-items:center; margin-bottom:28px; }}
    .logo {{ width:38px; height:38px; border-radius:12px; background:linear-gradient(135deg, var(--brand), #9b8cff); display:grid; place-items:center; box-shadow:0 0 36px rgba(113,112,255,.35); font-weight:600; }}
    .brand-title {{ font-size:15px; font-weight:600; letter-spacing:-.2px; }}
    .brand-sub {{ color:var(--muted); font-size:12px; margin-top:2px; }}
    .nav a {{ display:flex; align-items:center; gap:10px; padding:11px 12px; margin:4px 0; border:1px solid transparent; border-radius:10px; color:var(--sub); font-size:14px; }}
    .nav a:hover,.nav a.active {{ background:rgba(255,255,255,.045); border-color:var(--line); color:var(--text); }}
    .nav a.active {{ border-left-color:var(--brand2); box-shadow:inset 3px 0 0 var(--brand2); }}
    .side-card {{ margin-top:28px; padding:14px; border-radius:14px; background:rgba(255,255,255,.035); border:1px solid var(--line); color:#a7adb7; font-size:12px; line-height:1.6; }}
    .main {{ padding:30px 36px 50px; max-width:1420px; width:100%; }}
    .topbar {{ display:flex; align-items:flex-start; justify-content:space-between; gap:20px; margin-bottom:24px; }}
    .eyebrow {{ color:var(--brand2); font:500 12px/1 'JetBrains Mono', monospace; text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px; }}
    h1 {{ margin:0; font-size:34px; line-height:1.05; letter-spacing:-.7px; font-weight:510; }}
    h2 {{ margin:0 0 14px; font-size:20px; letter-spacing:-.25px; font-weight:590; }}
    h3 {{ margin:0 0 12px; font-size:15px; color:var(--sub); font-weight:590; }}
    .subtitle {{ margin-top:10px; color:var(--muted); font-size:14px; }}
    .btn-row {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
    button,.btn {{ appearance:none; border:1px solid var(--line); background:rgba(255,255,255,.045); color:var(--text); padding:10px 14px; border-radius:9px; cursor:pointer; font-weight:510; font-size:13px; font-family:inherit; }}
    button:hover,.btn:hover {{ background:rgba(255,255,255,.075); }}
    .btn-primary {{ background:var(--brand); border-color:rgba(255,255,255,.12); color:white; box-shadow:0 0 28px rgba(94,106,210,.35); }}
    .btn-primary:hover {{ background:#7077df; }}
    .btn-danger {{ color:#fecaca; border-color:rgba(239,68,68,.35); background:rgba(239,68,68,.09); }}
    .btn-muted {{ color:var(--sub); }}
    .grid-stats {{ display:grid; grid-template-columns:repeat(5,minmax(140px,1fr)); gap:14px; margin-bottom:20px; }}
    .stat {{ padding:16px; border:1px solid var(--line); background:rgba(255,255,255,.035); border-radius:16px; }}
    .stat .num {{ font-size:26px; line-height:1; font-weight:590; letter-spacing:-.7px; }}
    .stat .label {{ color:var(--muted); font-size:12px; margin-top:8px; }}
    .card {{ background:rgba(255,255,255,.035); border:1px solid var(--line); border-radius:18px; box-shadow:0 20px 70px rgba(0,0,0,.22); }}
    .card-pad {{ padding:20px; }}
    .toolbar {{ display:flex; align-items:center; justify-content:space-between; gap:14px; margin-bottom:14px; }}
    .filters {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .chip {{ padding:7px 10px; border:1px solid var(--line); border-radius:999px; color:var(--muted); font-size:12px; background:rgba(255,255,255,.02); }}
    .chip.active {{ color:var(--text); background:rgba(113,112,255,.14); border-color:rgba(113,112,255,.35); }}
    .job-list {{ display:flex; flex-direction:column; gap:10px; }}
    .job-card {{ display:grid; grid-template-columns:64px 1fr 210px 150px 210px; gap:16px; align-items:center; padding:16px; border:1px solid var(--line-soft); background:rgba(8,9,10,.45); border-radius:14px; }}
    .job-card:hover {{ border-color:rgba(113,112,255,.35); background:rgba(255,255,255,.045); }}
    .job-id {{ color:var(--faint); font:500 12px/1 'JetBrains Mono', monospace; }}
    .job-title {{ font-size:15px; font-weight:590; margin-bottom:8px; color:var(--text); }}
    .job-meta {{ color:var(--muted); font-size:12px; display:flex; gap:10px; flex-wrap:wrap; }}
    .path {{ color:var(--faint); font-family:'JetBrains Mono', monospace; max-width:720px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; display:block; }}
    .platform-pill {{ display:inline-flex; padding:5px 8px; margin:2px 4px 2px 0; border-radius:999px; background:rgba(255,255,255,.045); border:1px solid var(--line); color:var(--sub); font-size:12px; }}
    .badge {{ display:inline-flex; align-items:center; gap:7px; width:max-content; padding:7px 10px; border-radius:999px; border:1px solid var(--line); font-size:12px; font-weight:510; }}
    .badge-success {{ color:#bbf7d0; background:rgba(16,185,129,.12); border-color:rgba(16,185,129,.3); }}
    .badge-running {{ color:#bfdbfe; background:rgba(59,130,246,.12); border-color:rgba(59,130,246,.3); }}
    .badge-queued {{ color:#ddd6fe; background:rgba(113,112,255,.12); border-color:rgba(113,112,255,.3); }}
    .badge-warning {{ color:#fde68a; background:rgba(245,158,11,.12); border-color:rgba(245,158,11,.3); }}
    .badge-failed {{ color:#fecaca; background:rgba(239,68,68,.12); border-color:rgba(239,68,68,.32); }}
    .badge-cancelled,.badge-neutral {{ color:var(--muted); background:rgba(255,255,255,.035); }}
    .muted {{ color:var(--muted); }}
    .empty {{ padding:42px; text-align:center; color:var(--muted); }}
    .form-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    .form-full {{ grid-column:1/-1; }}
    label {{ display:block; margin-bottom:7px; color:var(--sub); font-size:13px; font-weight:510; }}
    input,textarea {{ width:100%; border:1px solid var(--line); background:rgba(0,0,0,.25); color:var(--text); border-radius:10px; padding:11px 12px; outline:none; font-family:inherit; }}
    input:focus,textarea:focus {{ border-color:rgba(113,112,255,.55); box-shadow:0 0 0 3px rgba(113,112,255,.12); }}
    textarea {{ min-height:96px; resize:vertical; }}
    .hint {{ color:var(--faint); font-size:12px; margin-top:-3px; margin-bottom:8px; }}
    .detail-grid {{ display:grid; grid-template-columns:1.2fr .8fr; gap:16px; align-items:start; }}
    .kv {{ display:grid; grid-template-columns:110px 1fr; gap:10px; padding:10px 0; border-bottom:1px solid var(--line-soft); }}
    .kv:last-child {{ border-bottom:0; }}
    .kv .k {{ color:var(--muted); font-size:12px; }}
    .kv .v {{ color:var(--sub); font-size:13px; overflow-wrap:anywhere; }}
    .attempt {{ margin-top:12px; padding:15px; border:1px solid var(--line-soft); border-radius:14px; background:rgba(0,0,0,.22); }}
    .attempt-head {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; }}
    pre {{ white-space:pre-wrap; word-break:break-word; margin:8px 0 0; padding:12px; background:#060708; border:1px solid var(--line-soft); border-radius:10px; color:#cbd5e1; max-height:280px; overflow:auto; font:12px/1.55 'JetBrains Mono', monospace; }}
    details summary {{ cursor:pointer; color:var(--muted); font-size:12px; margin-top:8px; }}
    .screens {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:10px; margin-top:10px; }}
    .shot {{ border:1px solid var(--line); border-radius:12px; overflow:hidden; background:#050506; }}
    .shot img {{ width:100%; display:block; aspect-ratio:16/10; object-fit:cover; }}
    .shot div {{ padding:8px; color:var(--muted); font-size:11px; font-family:'JetBrains Mono', monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    @media (max-width:1100px) {{ .shell{{grid-template-columns:1fr}} .sidebar{{position:relative;height:auto}} .grid-stats{{grid-template-columns:repeat(2,1fr)}} .job-card{{grid-template-columns:1fr}} .detail-grid,.form-grid{{grid-template-columns:1fr}} .main{{padding:22px}} }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="logo">G</div><div><div class="brand-title">Gavin Publisher</div><div class="brand-sub">视频号 / 抖音 / 小红书</div></div></div>
      <nav class="nav"><a class="active" href="/">⌘ 发布任务</a><a href="/new">＋ 新建任务</a></nav>
      <div class="side-card">本地可视化发布中控台。worker 每 30 秒扫描一次，到点自动发布；也可手动立即执行或失败重试。</div>
    </aside>
    <main class="main">{body}</main>
  </div>
</body>
</html>""".encode("utf-8")


def dashboard_body(jobs: list[dict], active_filter: str = "all") -> str:
    counts = {"total": len(jobs), "queued": 0, "running": 0, "success": 0, "failed": 0, "partial_success": 0}
    for job in jobs:
        if job.get("status") in counts:
            counts[job["status"]] += 1
    if active_filter != "all":
        jobs = [j for j in jobs if j.get("status") == active_filter]

    stat_html = "".join(
        f"<div class='stat'><div class='num'>{num}</div><div class='label'>{label}</div></div>"
        for label, num in [
            ("全部任务", counts["total"]),
            ("待发布", counts["queued"]),
            ("发布中", counts["running"]),
            ("成功", counts["success"]),
            ("失败/部分", counts["failed"] + counts["partial_success"]),
        ]
    )
    filters = [("all", "全部"), ("queued", "待发布"), ("running", "发布中"), ("success", "成功"), ("failed", "失败"), ("partial_success", "部分成功"), ("cancelled", "已取消")]
    filter_html = "".join(f"<a class='chip {'active' if key == active_filter else ''}' href='/?status={key}'>{label}</a>" for key, label in filters)

    cards = []
    for job in jobs:
        schedule = esc(job.get("schedule_time")) or "立即发布"
        err = truncate(job.get("last_error"), 80)
        error_html = f"<div class='muted'>错误：{esc(err)}</div>" if err else "<div class='muted'>无错误</div>"
        cards.append(
            f"""
            <div class='job-card'>
              <div class='job-id'>#{job['id']}</div>
              <div>
                <a class='job-title' href='/job?id={job['id']}'>{esc(job['title'])}</a>
                <div class='job-meta'><span class='path'>{esc(win_path(job['video']))}</span></div>
              </div>
              <div>{platform_pills(job.get('platforms',''))}</div>
              <div>{status_badge(job.get('status',''))}<div class='muted' style='margin-top:7px;font-size:12px'>{schedule}</div></div>
              <div><div class='btn-row'>
                <form method='post' action='/run'><input type='hidden' name='id' value='{job['id']}'><button class='btn-primary' type='submit'>立即执行</button></form>
                <form method='post' action='/cancel'><input type='hidden' name='id' value='{job['id']}'><button class='btn-danger' type='submit'>取消</button></form>
              </div>{error_html}</div>
            </div>
            """
        )
    job_html = "".join(cards) if cards else """
      <div class='empty'>
        <h2 style='margin-bottom:8px'>还没有发布任务</h2>
        <div style='margin-bottom:18px'>点击“新建发布任务”，把视频、封面、标题和平台一次性配置好。</div>
        <div class='btn-row' style='justify-content:center'><a class='btn btn-primary' href='/new'>新建发布任务</a><span class='chip'>支持：视频号 / 抖音 / 小红书</span><span class='chip'>定时 + 失败重试</span></div>
      </div>
    """
    return f"""
      <div class='topbar'>
        <div><div class='eyebrow'>Local Scheduler</div><h1>发布任务中控台</h1><div class='subtitle'>一次配置，多平台分发；支持定时、立即执行、失败重试和执行记录追踪。</div></div>
        <div class='btn-row'><a class='btn btn-primary' href='/new'>新建发布任务</a></div>
      </div>
      <div class='grid-stats'>{stat_html}</div>
      <section class='card card-pad'>
        <div class='toolbar'><h2>任务队列</h2><div class='filters'>{filter_html}</div></div>
        <div class='job-list'>{job_html}</div>
      </section>
    """


def new_job_body() -> str:
    return """
      <div class='topbar'>
        <div><div class='eyebrow'>Create Job</div><h1>新建发布任务</h1><div class='subtitle'>填写一次素材和文案，选择平台后由 worker 到点自动发布。</div></div>
        <div class='btn-row'><a class='btn' href='/'>返回任务列表</a></div>
      </div>
      <section class='card card-pad'>
        <form method='post' action='/create' class='form-grid'>
          <div><label>账号</label><input name='account' value='gavin'></div>
          <div><label>平台</label><input name='platforms' value='tencent,douyin,xiaohongshu' required><div class='hint'>可选：tencent,douyin,xiaohongshu</div></div>
          <div class='form-full'><label>视频路径</label><input name='video' placeholder='D:\\下载\\hermes视频素材\\xxx.mp4' required></div>
          <div class='form-full'><label>封面路径</label><input name='cover' placeholder='D:\\下载\\hermes视频素材\\cover.png'></div>
          <div class='form-full'><label>标题</label><input name='title' required placeholder='输入主标题'></div>
          <div class='form-full'><label>简介</label><textarea name='desc' placeholder='发布简介 / 正文'></textarea></div>
          <div><label>标签</label><input name='tags' placeholder='采购,工厂,供应链'></div>
          <div><label>定时发布时间</label><input name='schedule_time' placeholder='YYYY-MM-DD HH:MM:SS，空=立即'></div>
          <div><label>视频号短标题</label><input name='short_title' placeholder='视频号专用短标题'></div>
          <div style='display:flex;align-items:end'><label style='margin:0'><input type='checkbox' name='tencent_declare_original' value='1' style='width:auto;margin-right:8px'>视频号发布后尝试后台原创声明</label></div>
          <div class='form-full btn-row'><button class='btn-primary' type='submit'>保存到任务队列</button><a class='btn' href='/'>取消</a></div>
        </form>
      </section>
    """


def job_detail_body(job: dict, attempts: list[dict]) -> str:
    shots: list[str] = []
    for item in attempts:
        if item.get("screenshot") and Path(item["screenshot"]).exists():
            shots.append(item["screenshot"])
        shots.extend(extract_screenshots(item.get("stdout", ""), item.get("stderr", "")))
    seen: set[str] = set()
    shots = [s for s in shots if not (s in seen or seen.add(s))]

    shot_html = "".join(
        f"<a class='shot' href='{file_url(s)}' target='_blank'><img src='{file_url(s)}'><div>{esc(Path(s).name)}</div></a>" for s in shots
    ) or "<div class='muted'>暂无截图记录</div>"

    attempt_html = []
    for item in attempts:
        stderr = item.get("stderr") or ""
        stdout = item.get("stdout") or ""
        attempt_html.append(
            f"""
            <div class='attempt'>
              <div class='attempt-head'><div>{platform_pills(item.get('platform',''))}</div>{status_badge(item.get('status',''))}</div>
              <div class='muted'>开始：{esc(item.get('started_at'))}　完成：{esc(item.get('finished_at'))}</div>
              <details open><summary>错误 / stderr</summary><pre>{esc(stderr[-3000:] or '无')}</pre></details>
              <details><summary>输出 / stdout</summary><pre>{esc(stdout[-3000:] or '无')}</pre></details>
              <details><summary>执行命令</summary><pre>{esc(item.get('command') or '')}</pre></details>
            </div>
            """
        )
    attempts_block = "".join(attempt_html) if attempt_html else "<div class='empty'>还没有执行记录。</div>"

    return f"""
      <div class='topbar'>
        <div><div class='eyebrow'>Job #{job['id']}</div><h1>{esc(job['title'])}</h1><div class='subtitle'>{status_badge(job.get('status',''))}</div></div>
        <div class='btn-row'><a class='btn' href='/'>返回</a><form method='post' action='/run'><input type='hidden' name='id' value='{job['id']}'><button class='btn-primary' type='submit'>立即执行 / 重试</button></form><form method='post' action='/cancel'><input type='hidden' name='id' value='{job['id']}'><button class='btn-danger' type='submit'>取消任务</button></form></div>
      </div>
      <div class='detail-grid'>
        <section class='card card-pad'>
          <h2>任务信息</h2>
          <div class='kv'><div class='k'>视频</div><div class='v'><span class='path'>{esc(win_path(job.get('video','')))}</span></div></div>
          <div class='kv'><div class='k'>封面</div><div class='v'><span class='path'>{esc(win_path(job.get('cover','')))}</span></div></div>
          <div class='kv'><div class='k'>平台</div><div class='v'>{platform_pills(job.get('platforms',''))}</div></div>
          <div class='kv'><div class='k'>发布时间</div><div class='v'>{esc(job.get('schedule_time')) or '立即发布'}</div></div>
          <div class='kv'><div class='k'>标签</div><div class='v'>{esc(job.get('tags')) or '未设置'}</div></div>
          <div class='kv'><div class='k'>短标题</div><div class='v'>{esc(job.get('short_title')) or '未设置'}</div></div>
          <div class='kv'><div class='k'>原创声明</div><div class='v'>{'启用' if job.get('tencent_declare_original') else '关闭'}</div></div>
          <div class='kv'><div class='k'>错误</div><div class='v'>{esc(job.get('last_error')) or '无'}</div></div>
        </section>
        <section class='card card-pad'>
          <h2>失败截图</h2>
          <div class='screens'>{shot_html}</div>
        </section>
      </div>
      <section class='card card-pad' style='margin-top:16px'>
        <h2>平台执行记录</h2>
        {attempts_block}
      </section>
    """


class Handler(BaseHTTPRequestHandler):
    def send_html(self, title: str, body: str, status: int = 200) -> None:
        data = page(title, body)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        init_db()
        parsed = urlparse(self.path)
        if parsed.path == "/file":
            qs = parse_qs(parsed.query)
            path = Path((qs.get("path") or [""])[0])
            if not path.exists() or not path.is_file():
                self.send_html("未找到", "<div class='card card-pad'>文件不存在</div>", 404)
                return
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/":
            qs = parse_qs(parsed.query)
            active_filter = (qs.get("status") or ["all"])[0]
            self.send_html("发布任务中控台", dashboard_body(list_jobs(), active_filter))
            return
        if parsed.path == "/new":
            self.send_html("新建任务", new_job_body())
            return
        if parsed.path == "/job":
            qs = parse_qs(parsed.query)
            job_id = int(qs.get("id", ["0"])[0])
            job = get_job(job_id)
            if not job:
                self.send_html("未找到", "<div class='card card-pad'>任务不存在</div>", 404)
                return
            self.send_html("任务详情", job_detail_body(job, list_attempts(job_id)))
            return
        self.send_html("404", "<div class='card card-pad'>Not found</div>", 404)

    def do_POST(self):
        init_db()
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        if parsed.path == "/run":
            job_id = int((data.get("id") or ["0"])[0])
            queue_job(job_id, schedule_time="")
            self.redirect(f"/job?id={job_id}")
            return
        if parsed.path == "/cancel":
            job_id = int((data.get("id") or ["0"])[0])
            cancel_job(job_id)
            self.redirect(f"/job?id={job_id}")
            return
        if parsed.path == "/create":
            payload = {key: values[0] if values else "" for key, values in data.items()}
            payload["tencent_declare_original"] = payload.get("tencent_declare_original") == "1"
            job_id = create_job(payload)
            self.redirect(f"/job?id={job_id}")
            return
        self.send_html("404", "<div class='card card-pad'>Not found</div>", 404)


def main() -> int:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"dashboard: http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
