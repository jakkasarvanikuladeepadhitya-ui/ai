import asyncio, json, uuid
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from .. import config
from ..jobs import manager
from ..schemas.models import GenerateRequest, StoryboardRequest, StoryboardResponse
from .. import diagnostics
from ..services.storyboard import build_storyboard

router = APIRouter(prefix="/api")
ALLOWED = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}

@router.post("/storyboard", response_model=StoryboardResponse)
def storyboard(req: StoryboardRequest):
    scenes, source, warning = build_storyboard(req.prompt, req.style, req.duration, req.smart_script)
    return StoryboardResponse(scenes=scenes, source=source, warning=warning)

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    ext = ALLOWED.get(file.content_type)
    if not ext: raise HTTPException(400, "Only PNG, JPG or WEBP images are allowed")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024: raise HTTPException(400, "Image must be under 10 MB")
    iid = uuid.uuid4().hex[:12]
    (config.UPLOADS / f"{iid}.{ext}").write_bytes(data)
    return {"image_id": iid}

@router.post("/generate")
def generate(req: GenerateRequest): return {"job_id": manager.submit(req)}

@router.get("/jobs/{jid}")
def job(jid: str):
    j = manager.get(jid)
    if not j: raise HTTPException(404, "Job not found")
    return j

@router.get("/jobs/{jid}/events")
async def events(jid: str):
    if not manager.get(jid): raise HTTPException(404, "Job not found")
    async def stream():
        last = None
        while True:
            j = manager.get(jid)
            if j is None: break
            data = j.model_dump_json()
            if data != last:
                yield f"data: {data}\n\n"; last = data
            if j.status in ("done", "failed"): break
            await asyncio.sleep(0.5)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@router.get("/jobs/{jid}/scene/{i}")
def scene_thumb(jid: str, i: int):
    f = config.CLIPS / f"{jid}_{i}.jpg"
    if not jid.isalnum() or not f.exists(): raise HTTPException(404, "Scene not ready")
    return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control":"no-store"})

@router.get("/download/{jid}")
def download(jid: str, inline: bool = True):
    f = config.EXPORTS / f"{jid}.mp4"
    if not jid.isalnum() or not f.exists(): raise HTTPException(404, "Not ready")
    return FileResponse(f, media_type="video/mp4", filename=f"video_{jid}.mp4", content_disposition_type="attachment" if inline is False else "inline")

@router.get("/jobs/{jid}/poster")
def poster(jid: str):
    f = config.EXPORTS / f"{jid}.jpg"
    if not jid.isalnum() or not f.exists(): raise HTTPException(404, "No poster")
    return FileResponse(f, media_type="image/jpeg")

@router.get("/health")
def health(): return {"ok": True, **diagnostics.collect()}
