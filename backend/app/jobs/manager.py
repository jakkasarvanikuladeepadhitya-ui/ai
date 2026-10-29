import os,shutil,subprocess,threading,uuid
from .. import config
from ..schemas.models import JobStatus
from ..services.storyboard import build_storyboard
_jobs={}; _lock=threading.Lock()
def get(jid): return _jobs.get(jid)
def submit(req):
    jid=uuid.uuid4().hex[:12]; _jobs[jid]=JobStatus(id=jid,status="queued",message="Queued",provider=config.VIDEO_PROVIDER)
    threading.Thread(target=_run,args=(jid,req),daemon=True).start(); return jid
def _set(jid,**kw): _jobs[jid]=_jobs[jid].model_copy(update=kw)

def _extract_video(result):
    v=result[0] if isinstance(result,(list,tuple)) and result else result
    if isinstance(v,dict): v=v.get("path") or v.get("video")
    return v if isinstance(v,str) else None

def _try_space(space,prompt,out,aspect,duration):
    from gradio_client import Client
    token=os.getenv("HF_TOKEN") or None
    c=Client(space,token=token)
    ratio={"16:9":"832x480","9:16":"480x832","1:1":"640x640"}.get(aspect,"832x480")
    seconds=max(2,min(5,int(round(float(duration)))))
    # Public Spaces change APIs; try common named endpoints and compatible argument sets.
    attempts=[
        ("/generate_video",(prompt[:600],)),
        ("/generate_video",(None,prompt[:600],ratio,seconds)),
        ("/generate",(prompt[:600],)),
        ("/infer",(prompt[:600],)),
    ]
    errors=[]
    for api,args in attempts:
        try:
            r=c.predict(*args,api_name=api)
            v=_extract_video(r)
            if v and os.path.exists(v):
                shutil.copyfile(v,str(out)); return
        except Exception as e: errors.append(str(e)[:160])
    raise RuntimeError("Space API unavailable: "+" | ".join(errors[-2:]))

def _free_space_clip(prompt,out,aspect,duration):
    spaces=[s.strip() for s in os.getenv("HF_SPACES","numanajmal0/Wan-Video-API,ByteDance/AnimateDiff-Lightning").split(",") if s.strip()]
    errors=[]
    for space in spaces:
        try:
            _try_space(space,prompt,out,aspect,duration); return space
        except Exception as e:
            errors.append(f"{space}: {e}")
    raise RuntimeError("All free ZeroGPU providers are unavailable right now. "+" || ".join(errors)[-900:])

def _mock_clip(prompt,out,w,h,duration):
    hue=sum(map(ord,prompt))%360
    cmd=["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x26345f:s={w}x{h}:d={duration}:r=25","-vf",f"hue=h={hue}+t*18:s=1.3","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-an",str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: raise RuntimeError(r.stderr[-300:])

def _run(jid,req):
    try:
        _set(jid,status="running",stage="script",progress=5,message="Creating storyboard")
        scenes=req.scenes or build_storyboard(req.prompt,req.style,req.duration,req.smart_script)[0]
        config.apply_quality(req.quality); w,h=config.out_size(req.aspect_ratio); clips=[]; used=[]
        for i,s in enumerate(scenes):
            _set(jid,stage="clips",progress=10+int(55*i/max(1,len(scenes))),message=f"Generating free AI scene {i+1}/{len(scenes)}",scenes_state=["done" if x<i else "running" if x==i else "pending" for x in range(len(scenes))])
            out=config.CLIPS/f"{jid}_{i}.mp4"
            if config.VIDEO_PROVIDER=="hf_space": used.append(_free_space_clip(s.visual_prompt,out,req.aspect_ratio,s.duration))
            else: _mock_clip(s.visual_prompt,out,w,h,s.duration)
            clips.append(out)
        _set(jid,stage="render",progress=75,message="Rendering final video")
        lst=config.CLIPS/f"{jid}.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips))
        final=config.EXPORTS/f"{jid}.mp4"
        r=subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(lst),"-c","copy","-movflags","+faststart",str(final)],capture_output=True,text=True)
        if r.returncode:
            r=subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(lst),"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-movflags","+faststart",str(final)],capture_output=True,text=True)
            if r.returncode: raise RuntimeError(r.stderr[-500:])
        subprocess.run(["ffmpeg","-y","-ss","1","-i",str(final),"-frames:v","1","-vf","scale=640:-2",str(config.EXPORTS/f"{jid}.jpg")],capture_output=True)
        _set(jid,status="done",stage="done",progress=100,message="Video ready",duration=sum(s.duration for s in scenes),download_url=f"/api/download/{jid}",scenes_state=["done"]*len(scenes))
    except Exception as e: _set(jid,status="failed",message="Free AI providers unavailable",error=str(e))
