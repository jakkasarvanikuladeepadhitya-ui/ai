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

def _video_path(v):
    if isinstance(v,str): return v
    if isinstance(v,dict):
        for k in ("path","video","url"):
            x=v.get(k)
            if isinstance(x,str): return x
            if isinstance(x,dict) and isinstance(x.get("path"),str): return x["path"]
    if isinstance(v,(list,tuple)):
        for x in v:
            p=_video_path(x)
            if p: return p
    return None

def _copy_result(result,out):
    p=_video_path(result)
    if not p: raise RuntimeError("Provider returned no video file")
    if p.startswith("http://") or p.startswith("https://"):
        import httpx
        with httpx.stream("GET",p,follow_redirects=True,timeout=120) as r:
            r.raise_for_status()
            with open(out,"wb") as f:
                for chunk in r.iter_bytes(): f.write(chunk)
    else: shutil.copyfile(p,str(out))

def _wan_api(prompt,out,duration):
    # Verified public Gradio API: inspect live endpoint schema instead of guessing names.
    from gradio_client import Client
    c=Client("numanajmal0/Wan-Video-API",token=os.getenv("HF_TOKEN") or None)
    info=c.view_api(return_format="dict")
    named=info.get("named_endpoints",{}) if isinstance(info,dict) else {}
    endpoint="/generate" if "/generate" in named else ("/generate_video" if "/generate_video" in named else None)
    if not endpoint:
        candidates=[k for k in named if "generate" in k.lower()]
        endpoint=candidates[0] if candidates else None
    if not endpoint: raise RuntimeError("Wan API has no generation endpoint")
    params=named.get(endpoint,{}).get("parameters",[])
    vals=[]
    for p in params:
        name=(p.get("parameter_name") or p.get("label") or "").lower()
        if "prompt" in name and "negative" not in name: vals.append(prompt[:600])
        elif "negative" in name: vals.append("")
        elif "duration" in name or "second" in name: vals.append(max(2,min(5,int(round(float(duration))))))
        elif "seed" in name: vals.append(-1)
        elif "step" in name: vals.append(4)
        elif p.get("parameter_has_default"): vals.append(p.get("parameter_default"))
        elif not p.get("parameter_has_default"): raise RuntimeError(f"Unsupported required Wan parameter: {name}")
    _copy_result(c.predict(*vals,api_name=endpoint),out)
    return "numanajmal0/Wan-Video-API"

def _free_clip(prompt,out,aspect,duration):
    errors=[]
    for fn in (_wan_api,):
        try: return fn(prompt,out,duration)
        except Exception as e: errors.append(str(e))
    raise RuntimeError("Free GPU generator is temporarily unavailable. Please retry later. "+" | ".join(errors)[-500:])

def _mock_clip(prompt,out,w,h,duration):
    hue=sum(map(ord,prompt))%360
    r=subprocess.run(["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x26345f:s={w}x{h}:d={duration}:r=25","-vf",f"hue=h={hue}+t*18:s=1.3","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-an",str(out)],capture_output=True,text=True)
    if r.returncode: raise RuntimeError(r.stderr[-300:])

def _run(jid,req):
    try:
        _set(jid,status="running",stage="script",progress=5,message="Creating storyboard")
        scenes=req.scenes or build_storyboard(req.prompt,req.style,req.duration,req.smart_script)[0]
        config.apply_quality(req.quality); w,h=config.out_size(req.aspect_ratio); clips=[]
        for i,s in enumerate(scenes):
            _set(jid,stage="clips",progress=10+int(55*i/max(1,len(scenes))),message=f"Generating free AI scene {i+1}/{len(scenes)}",scenes_state=["done" if x<i else "running" if x==i else "pending" for x in range(len(scenes))])
            out=config.CLIPS/f"{jid}_{i}.mp4"
            if config.VIDEO_PROVIDER=="hf_space": _free_clip(s.visual_prompt,out,req.aspect_ratio,s.duration)
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
    except Exception as e: _set(jid,status="failed",message="Generation unavailable",error=str(e))
