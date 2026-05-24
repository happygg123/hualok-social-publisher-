from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from publisher_db import create_job, get_job, init_db, list_attempts, list_jobs

HOST = "127.0.0.1"
PORT = 8765


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 24px; background:#f6f7f9; color:#222; }}
    a {{ color:#1769e0; text-decoration:none; }}
    .card {{ background:#fff; border-radius:10px; padding:18px; margin-bottom:16px; box-shadow:0 1px 4px #0001; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; }}
    th,td {{ border-bottom:1px solid #eee; padding:10px; text-align:left; vertical-align:top; }}
    th {{ background:#fafafa; }}
    input, textarea {{ width:100%; box-sizing:border-box; padding:8px; margin:4px 0 10px; }}
    textarea {{ height:70px; }}
    button {{ padding:10px 18px; border:0; background:#ff6a00; color:#fff; border-radius:6px; cursor:pointer; }}
    .status-success {{ color:#14833b; font-weight:bold; }}
    .status-failed {{ color:#c62828; font-weight:bold; }}
    .status-running {{ color:#1769e0; font-weight:bold; }}
    .muted {{ color:#777; font-size:12px; }}
    .nav {{ margin-bottom:16px; }}
    .nav a {{ margin-right:16px; }}
    code {{ background:#f0f0f0; padding:2px 4px; border-radius:4px; }}
  </style>
</head>
<body>
  <div class="nav"><a href="/">任务列表</a><a href="/new">新建任务</a></div>
  {body}
</body>
</html>""".encode("utf-8")


def esc(value) -> str:
    return html.escape(str(value or ""))


class Handler(BaseHTTPRequestHandler):
    def send_html(self, title: str, body: str, status: int = 200) -> None:
        data = page(title, body)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        init_db()
        parsed = urlparse(self.path)
        if parsed.path == "/":
            jobs = list_jobs()
            rows = []
            for job in jobs:
                status = esc(job["status"])
                rows.append(
                    f"<tr><td>{job['id']}</td><td><a href='/job?id={job['id']}'>{esc(job['title'])}</a><div class='muted'>{esc(job['video'])}</div></td>"
                    f"<td>{esc(job['platforms'])}</td><td>{esc(job['schedule_time']) or '立即'}</td>"
                    f"<td class='status-{status}'>{status}</td><td>{esc(job['last_error'])}</td></tr>"
                )
            body = "<div class='card'><h2>发布任务</h2><p>本页显示一次设置、多平台分发任务。</p></div>"
            body += "<table><tr><th>ID</th><th>标题/视频</th><th>平台</th><th>发布时间</th><th>状态</th><th>错误</th></tr>" + "".join(rows) + "</table>"
            self.send_html("发布任务", body)
            return
        if parsed.path == "/new":
            body = """
<div class="card"><h2>新建发布任务</h2>
<form method="post" action="/create">
<label>账号</label><input name="account" value="gavin">
<label>视频路径</label><input name="video" placeholder="D:\\videos\\001.mp4" required>
<label>封面路径</label><input name="cover" placeholder="D:\\videos\\001.jpg">
<label>标题</label><input name="title" required>
<label>简介</label><textarea name="desc"></textarea>
<label>标签（逗号分隔）</label><input name="tags">
<label>平台（逗号分隔：tencent,douyin,xiaohongshu）</label><input name="platforms" value="tencent,douyin,xiaohongshu" required>
<label>定时发布时间（YYYY-MM-DD HH:MM:SS，空=立即）</label><input name="schedule_time">
<label>视频号短标题</label><input name="short_title">
<label><input type="checkbox" name="tencent_declare_original" value="1" style="width:auto"> 视频号发布后尝试后台原创声明（后置动作）</label><br><br>
<button type="submit">保存任务</button>
</form></div>
"""
            self.send_html("新建任务", body)
            return
        if parsed.path == "/job":
            qs = parse_qs(parsed.query)
            job_id = int(qs.get("id", ["0"])[0])
            job = get_job(job_id)
            if not job:
                self.send_html("未找到", "<div class='card'>任务不存在</div>", 404)
                return
            attempts = list_attempts(job_id)
            body = f"<div class='card'><h2>{esc(job['title'])}</h2><p><b>状态：</b>{esc(job['status'])}</p><p><b>视频：</b><code>{esc(job['video'])}</code></p><p><b>封面：</b><code>{esc(job['cover'])}</code></p><p><b>平台：</b>{esc(job['platforms'])}</p><p><b>定时：</b>{esc(job['schedule_time']) or '立即'}</p><p><b>错误：</b>{esc(job['last_error'])}</p></div>"
            body += "<div class='card'><h3>平台执行记录</h3><table><tr><th>平台</th><th>状态</th><th>时间</th><th>错误</th></tr>"
            for item in attempts:
                body += f"<tr><td>{esc(item['platform'])}</td><td>{esc(item['status'])}</td><td>{esc(item['finished_at'])}</td><td><pre>{esc(item['stderr'][-1000:])}</pre></td></tr>"
            body += "</table></div>"
            self.send_html("任务详情", body)
            return
        self.send_html("404", "<div class='card'>Not found</div>", 404)

    def do_POST(self):
        init_db()
        parsed = urlparse(self.path)
        if parsed.path != "/create":
            self.send_html("404", "<div class='card'>Not found</div>", 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        payload = {key: values[0] if values else "" for key, values in data.items()}
        payload["tencent_declare_original"] = payload.get("tencent_declare_original") == "1"
        job_id = create_job(payload)
        self.send_response(303)
        self.send_header("Location", f"/job?id={job_id}")
        self.end_headers()


def main() -> int:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"dashboard: http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
