"""Public character submissions: only admin approval enables server-wide discovery."""
import json
import os
from .models import AppSetting, CharacterPublication
PREFIX="character_publication_review:"

def review(db,ident):
 row=db.get(AppSetting,PREFIX+ident)
 return json.loads(row.value) if row else {"status":"pending","revision":0,"reason":""}

def record(db,ident,status,reason=""):
 value=review(db,ident)
 value.update(status=status,revision=value["revision"]+1,reason=reason)
 row=db.get(AppSetting,PREFIX+ident)
 if row:row.value=json.dumps(value,ensure_ascii=False)
 else:db.add(AppSetting(key=PREFIX+ident,value=json.dumps(value,ensure_ascii=False)))
 return value

def withdraw_on_edit(db,ident):
 pub=db.get(CharacterPublication,ident)
 if pub:
  pub.is_public=0
  record(db,ident,"private")

def bind_publication_review(runtime):
 app=runtime.app
 @app.get("/v1/admin/character-submissions")
 def listing(_:None=runtime.Depends(runtime.docs_auth),db:runtime.DBSession=runtime.Depends(runtime.db_session)):
  result=[]
  for pub in db.query(runtime.CharacterPublication).all():
   r=review(db,pub.character_id)
   if r["status"]=="private":continue
   c=db.get(runtime.Character,pub.character_id)
   if c:result.append({"id":c.id,"owner":c.user_id,"spec":runtime.spec(c).model_dump(),"tags":json.loads(pub.tags),**r})
  return result
 @app.put("/v1/admin/character-submissions/{ident}")
 def decide(ident:str,data:dict,_:None=runtime.Depends(runtime.docs_auth),db:runtime.DBSession=runtime.Depends(runtime.db_session)):
  pub=db.get(runtime.CharacterPublication,ident);c=db.get(runtime.Character,ident)
  if not pub or not c:raise runtime.HTTPException(404,"Submission not found")
  old=review(db,ident)
  if type(data.get("revision")) is not int or data["revision"]!=old["revision"]:
   raise runtime.HTTPException(409,"Submission changed; reload")
  decision=data.get("decision")
  if decision not in ("approved","rejected"):raise runtime.HTTPException(422,"Invalid decision")
  reason=data.get("reason","")
  if not isinstance(reason,str) or len(reason)>600:raise runtime.HTTPException(422,"Invalid reason")
  if decision=="approved" and os.getenv("COMMUNITY_CHARACTER_PUBLICATION_ENABLED","false").lower()!="true":
   raise runtime.HTTPException(403,"Community publication is temporarily disabled")
  if decision=="approved":
   runtime.enforce_character_policy({**runtime.spec(c).model_dump(),"tags":json.loads(pub.tags),"character_type":pub.character_type})
  # Lock current publication row conditionally; concurrent user edits/re-submissions
  # change updated_at. Recheck review revision too before publishing.
  expected=pub.updated_at
  db.expire_all()
  if review(db,ident)["revision"]!=old["revision"]:raise runtime.HTTPException(409,"Reload submission")
  changed=db.query(runtime.CharacterPublication).filter_by(character_id=ident,updated_at=expected).update(
   {"is_public":int(decision=="approved"),"updated_at":runtime.now()},synchronize_session=False)
  if changed!=1:db.rollback();raise runtime.HTTPException(409,"Submission changed")
  value=record(db,ident,decision,reason.strip())
  db.commit()
  return value
