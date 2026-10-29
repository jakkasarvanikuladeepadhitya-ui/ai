const j=async r=>{if(!r.ok)throw new Error(await r.text());return r.json()}
export const getHealth=()=>fetch("/api/health").then(j)
export const getStoryboard=p=>fetch("/api/storyboard",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)}).then(j)
export const generate=p=>fetch("/api/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)}).then(j)
export const getJob=id=>fetch("/api/jobs/"+id).then(j)
