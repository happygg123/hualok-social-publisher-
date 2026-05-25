from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from publisher_db import cancel_job, create_job, get_job, init_db, list_attempts, list_jobs, queue_job
from app.publisher_engines.multipost_payload import build_multipost_video_payload
from app.web.view_models import build_dashboard_context, build_job_detail_context

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="HuaLok Publisher", version="0.2.0")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def dashboard(request: Request, status: str = Query("all")):
    init_db()
    context = build_dashboard_context(list_jobs(), status)
    return templates.TemplateResponse("dashboard.html", {"request": request, **context})


@app.get("/new")
def new_job(request: Request):
    return templates.TemplateResponse("job_new.html", {"request": request})


@app.post("/create")
def create(
    account: str = Form("hualok"),
    video: str = Form(...),
    cover: str = Form(""),
    title: str = Form(...),
    desc: str = Form(""),
    tags: str = Form(""),
    platforms: str = Form("tencent,douyin,xiaohongshu"),
    schedule_time: str = Form(""),
    short_title: str = Form(""),
    tencent_declare_original: str | None = Form(None),
):
    job_id = create_job(
        {
            "account": account,
            "video": video,
            "cover": cover,
            "title": title,
            "desc": desc,
            "tags": tags,
            "platforms": platforms,
            "schedule_time": schedule_time,
            "short_title": short_title,
            "tencent_declare_original": bool(tencent_declare_original),
        }
    )
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.get("/job/{job_id}")
def job_detail(request: Request, job_id: int):
    init_db()
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    context = build_job_detail_context(job, list_attempts(job_id))
    return templates.TemplateResponse("job_detail.html", {"request": request, **context})


@app.post("/job/{job_id}/run")
def run_job_now(job_id: int):
    queue_job(job_id, schedule_time="")
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.post("/job/{job_id}/cancel")
def cancel(job_id: int):
    cancel_job(job_id)
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.get("/file")
def serve_file(path: str):
    file_path = Path(path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)


@app.get("/media/job/{job_id}/{asset}")
def serve_job_media(job_id: int, asset: str):
    if asset not in {"video", "cover"}:
        raise HTTPException(status_code=404, detail="不支持的素材类型")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    file_path = Path(job.get(asset) or "")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="素材文件不存在")
    return FileResponse(file_path)


@app.get("/api/jobs/{job_id}/multipost-payload")
def multipost_payload(request: Request, job_id: int):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    base_url = str(request.base_url).rstrip("/")
    return build_multipost_video_payload(job, base_url=base_url)
