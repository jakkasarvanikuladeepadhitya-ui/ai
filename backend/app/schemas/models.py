from typing import List, Optional
from pydantic import BaseModel, Field
class Scene(BaseModel):
    index:int; visual_prompt:str; camera:str="slow push-in"; duration:int=Field(default=5,ge=3,le=12); narration:str=""; subtitle:str=""
class GenerateRequest(BaseModel):
    prompt:str=Field(min_length=3,max_length=1000); style:str="realistic"; duration:int=Field(default=30,ge=10,le=120); quality:str="balanced"; aspect_ratio:str="16:9"; image_id:Optional[str]=None; narration:bool=True; music:bool=True; subtitles:bool=True; scenes:Optional[List[Scene]]=None; smart_script:bool=False
class StoryboardRequest(BaseModel):
    prompt:str=Field(min_length=3,max_length=1000); style:str="realistic"; duration:int=Field(default=30,ge=10,le=120); smart_script:bool=True
class StoryboardResponse(BaseModel):
    scenes:List[Scene]; source:str; warning:Optional[str]=None
class JobStatus(BaseModel):
    id:str; status:str; progress:int=0; message:str=""; duration:Optional[float]=None; download_url:Optional[str]=None; error:Optional[str]=None; warnings:List[str]=[]; scenes_state:List[str]=[]; stage:str="queued"; elapsed:float=0.0; provider:str=""; scenes_ready:List[int]=[]
