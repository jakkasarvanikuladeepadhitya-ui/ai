import shutil
from . import config
def collect():
    ff=bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    return {"provider":config.VIDEO_PROVIDER,"ffmpeg":ff,"ready":ff,"narration":config.NARRATION_ENGINE,"problems":[] if ff else ["FFmpeg not found"]}
