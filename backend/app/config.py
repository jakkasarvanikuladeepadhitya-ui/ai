import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STORAGE=ROOT/"storage"; UPLOADS=STORAGE/"uploads"; CLIPS=STORAGE/"clips"; AUDIO=STORAGE/"audio"; EXPORTS=STORAGE/"exports"
for d in (UPLOADS,CLIPS,AUDIO,EXPORTS): d.mkdir(parents=True,exist_ok=True)
VIDEO_PROVIDER=os.getenv("VIDEO_PROVIDER","mock")
STORYBOARD_ENGINE=os.getenv("STORYBOARD_ENGINE","rules")
NARRATION_ENGINE=os.getenv("NARRATION_ENGINE","espeak")
MUSIC_FILE=os.getenv("MUSIC_FILE","auto")
MIN_DURATION=float(os.getenv("MIN_DURATION","10")); SCENE_SECONDS=max(3,int(os.getenv("SCENE_SECONDS","5")))
RES=720
def apply_quality(mode):
    global RES
    RES={"turbo":480,"balanced":720,"quality":1080}.get(mode,720)
def out_size(aspect):
    sizes={480:{"16:9":(848,480),"9:16":(480,848),"1:1":(480,480)},720:{"16:9":(1280,720),"9:16":(720,1280),"1:1":(720,720)},1080:{"16:9":(1920,1080),"9:16":(1080,1920),"1:1":(1080,1080)}}
    return sizes[RES].get(aspect,sizes[RES]["16:9"])
