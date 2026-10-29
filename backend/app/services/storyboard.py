from .. import config
from ..schemas.models import Scene
BEATS=[("Opening cinematic establishing shot of {p}","slow push-in","Our story begins with {p}."),("Detailed view of {p}, rich atmosphere and natural motion","slow pan right","Every detail brings the story to life."),("Main action and dramatic development around {p}","tracking shot","Now the story moves forward."),("Climactic cinematic moment involving {p}","slow orbit","This is the moment everything changes."),("Beautiful closing shot of {p}","slow pull-out","And the journey continues.")]
def build_storyboard(prompt,style="realistic",duration=30,smart=True):
    n=max(2,-(-duration//config.SCENE_SECONDS)); per=-(-duration//n); scenes=[]
    look="photorealistic, cinematic lighting, 35mm film, high detail" if style!="animated" else "stylized 3D animation, vibrant colors, smooth motion"
    for i in range(n):
        b=BEATS[0] if i==0 else BEATS[-1] if i==n-1 else BEATS[1+(i-1)%3]
        scenes.append(Scene(index=i,duration=per,visual_prompt=f"{b[0].format(p=prompt)}, {look}",camera=b[1],narration=b[2].format(p=prompt),subtitle=b[2].format(p=prompt)))
    return scenes,"rules",None
