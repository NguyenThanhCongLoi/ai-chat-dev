import os, json, time, io
import pytest
from PIL import Image
os.environ["DATABASE_URL"]="sqlite://"
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from character_chat.db import Base, AppSetting, Character, CharacterExpressionAsset, CharacterKnowledge, CharacterReflection, Document, DocumentChunk, Memory, Message, ModelConfig, MoodObservation, RelationshipEvent, Room, RoomDocument, RoomStoryState, User
from character_chat.main import app, db_session, deduplicate_expression_assets, expression_source_id, register_expression_identity, reply_expression, admin_prompt_addon, effective_project_prompt, model_out
from character_chat.schemas import CharacterSpec, Personality, MirrorIn, TurnAnalysis, uid
from character_chat.presets import presets
from character_chat.retrieval import chunks, allowed, retrieve_memories, retrieve_knowledge, room_document_manifest, store_memory
from character_chat.assistant_pipeline import extract_assistant_text, retrieve_room_context, task_guardrail
from character_chat.main import resolve_expression_asset_source
from character_chat.engine import LLM, route, update_relationship, evaluate_state, relationship_expression, support_mode, parse_suggestions, suggestion_prompt, condense_character_source, room_story_events, repeated_roleplay_reply, detect_message_language, suggestions_for_conversation, finalize_suggestions
from character_chat.db import Relationship
from character_chat.zodiac import zodiac_sign, zodiac_context
from character_chat.moderation import ensure_safe_content, sensitive_categories
from datetime import date

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
Base.metadata.create_all(engine)
Session=sessionmaker(engine,expire_on_commit=False)
def png_bytes():
    output=io.BytesIO();Image.new("RGB",(24,24),(40,160,120)).save(output,"PNG");return output.getvalue()
def db_override():
    with Session() as db:yield db
app.dependency_overrides[db_session]=db_override
client=TestClient(app)

def test_roleplay_story_state_is_per_room_and_repetition_is_detected():
    isolated_engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(isolated_engine);Isolated=sessionmaker(isolated_engine,expire_on_commit=False)
    with Isolated() as db:
        db.add(User(id="story-user"))
        db.add_all([Room(id="story-a",user_id="story-user",name="A"),Room(id="story-b",user_id="story-user",name="B")])
        db.add(Character(id="story-character",user_id="story-user",name="Mia",spec=CharacterSpec(name="Mia").model_dump_json()))
        for index in range(30):
            db.add(Message(id=f"story-a-{index}",room_id="story-a",sender_type="user" if index%2==0 else "character",character_id=None if index%2==0 else "story-character",text=f"Sự kiện A {index}"))
        db.add(Message(id="story-b-0",room_id="story-b",sender_type="user",text="Bí mật phòng B"))
        db.commit()
        events=room_story_events(db,"story-a",{f"story-a-{index}" for index in range(20,30)})
        assert events["events"] and all("Bí mật phòng B" not in item["text"] for item in events["events"])
        assert db.get(RoomStoryState,"story-a").events
        assert db.get(RoomStoryState,"story-b") is None
    assert repeated_roleplay_reply("Mình sẽ cùng bạn đi tiếp. Bạn muốn bắt đầu từ đâu?",["Mình sẽ cùng bạn đi tiếp. Bạn muốn bắt đầu từ đâu?"])
    assert not repeated_roleplay_reply("Hôm nay mình sẽ mở một cánh cửa mới cho câu chuyện.",["Chúng ta cần nghỉ một chút và suy nghĩ lại."])

def test_admin_preset_avatar_queues_expressions_before_any_user_creates_it(monkeypatch):
    import character_chat.main as main
    monkeypatch.setenv("DOCS_USERNAME","backend")
    monkeypatch.setenv("DOCS_PASSWORD","strong-password")
    calls=[]
    monkeypatch.setattr(main,"generate_character_expressions",lambda source,content:calls.append((source,len(content))))
    created=client.post("/v1/admin/presets",auth=("backend","strong-password"),json={"name":"CMS Image Test","role":"companion"})
    assert created.status_code==200,created.text
    preset_type=created.json()["spec"]["preset_type"]
    uploaded=client.put(f"/v1/admin/presets/{preset_type}/avatar",auth=("backend","strong-password"),files={"file":("portrait.png",png_bytes(),"image/png")})
    assert uploaded.status_code==200,uploaded.text
    assert uploaded.json()["images_queued"]==6
    assert calls and calls[-1][0]=="__preset__:"+preset_type
    preview=client.get(f"/v1/admin/characters/preset:{preset_type}/expressions",auth=("backend","strong-password"))
    assert preview.status_code==200 and preview.json()["status"]=="queued"
    instantiated=client.post("/v1/characters",headers={"X-Demo-User-Id":"cms-image-test"},json=created.json()["spec"])
    assert instantiated.status_code==200,instantiated.text
    with Session() as db:
        assert db.get(AppSetting,"expression_source:"+instantiated.json()["id"]).value=="__preset__:"+preset_type
    with Session() as db:
        for emotion in ("neutral","happy","sad","angry","surprised","shy"):
            db.add(CharacterExpressionAsset(id=uid(),character_id="__preset__:"+preset_type,emotion=emotion,content=png_bytes()))
        db.commit()
    preview=client.get(f"/v1/admin/characters/preset:{preset_type}/expressions",auth=("backend","strong-password"))
    assert preview.json()["status"]=="ready" and len(preview.json()["images"])==6
    with Session() as db:
        db.get(AppSetting,"expression_source:"+instantiated.json()["id"]).value="__default__"
        db.commit()
    expression=client.get(f"/v1/characters/{instantiated.json()['id']}/expression/happy",headers={"X-Demo-User-Id":"cms-image-test"})
    assert expression.status_code==200 and expression.content==png_bytes()

def test_admin_backfills_only_missing_system_expression_sets(monkeypatch):
    import character_chat.main as main
    monkeypatch.setenv("DOCS_USERNAME","backend")
    monkeypatch.setenv("DOCS_PASSWORD","strong-password")
    calls=[]
    monkeypatch.setattr(main,"generate_character_expressions",lambda source,content:calls.append(source))
    with Session() as db:
        model=ModelConfig(id=uid(),name="Image test",provider="test",model_id="image-test",api_base="https://example.test/v1",enabled=1)
        db.add(model)
        db.add(AppSetting(key="model_profile:"+model.id,value=json.dumps({"purposes":["avatar_image"]})))
        db.commit()
    created=client.post("/v1/admin/presets",auth=("backend","strong-password"),json={"name":"CMS Backfill Test","role":"companion"})
    assert created.status_code==200,created.text
    preset_type=created.json()["spec"]["preset_type"]
    with Session() as db:
        db.add(AppSetting(key="preset_asset:"+preset_type,value=json.dumps({"mime_type":"image/png","content":__import__("base64").b64encode(png_bytes()).decode()})))
        db.commit()
    queued=client.post("/v1/admin/system-characters/expressions/backfill",auth=("backend","strong-password"))
    assert queued.status_code==200,queued.text
    assert "__preset__:"+preset_type in calls
    assert queued.json()["characters_queued"]>=1
    repeat=client.post("/v1/admin/system-characters/expressions/backfill",auth=("backend","strong-password"))
    assert repeat.status_code==200 and repeat.json()["characters_queued"]==0

def test_cms_avatar_after_preset_edit_updates_active_override_and_existing_character(monkeypatch):
    import character_chat.main as main
    monkeypatch.setenv("DOCS_USERNAME","backend")
    monkeypatch.setenv("DOCS_PASSWORD","strong-password")
    monkeypatch.setattr(main,"generate_character_expressions",lambda source,content:None)
    created=client.post("/v1/admin/presets",auth=("backend","strong-password"),json={"name":"CMS Avatar Sync","role":"companion"})
    assert created.status_code==200,created.text
    preset_type=created.json()["spec"]["preset_type"]
    instantiated=client.post("/v1/characters",headers={"X-Demo-User-Id":"cms-avatar-sync"},json=created.json()["spec"])
    assert instantiated.status_code==200,instantiated.text
    edited=client.put(f"/v1/admin/presets/{preset_type}",auth=("backend","strong-password"),json={"name":"CMS Avatar Edited"})
    assert edited.status_code==200,edited.text
    uploaded=client.put(f"/v1/admin/presets/{preset_type}/avatar",auth=("backend","strong-password"),files={"file":("portrait.png",png_bytes(),"image/png")})
    assert uploaded.status_code==200,uploaded.text
    with Session() as db:
        assert main.effective_presets(db)[-1].avatar_url==uploaded.json()["avatar_url"]
        assert main.spec(db.get(Character,instantiated.json()["id"])).avatar_url==uploaded.json()["avatar_url"]

def test_failed_system_expression_generation_does_not_present_source_as_six_emotions(monkeypatch):
    import character_chat.main as main
    isolated_engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(isolated_engine);Isolated=sessionmaker(isolated_engine,expire_on_commit=False)
    monkeypatch.setattr(main,"Session",Isolated)
    monkeypatch.delenv("AVATAR_MODAL_FUNCTION",raising=False)
    with Isolated() as db:
        model=ModelConfig(id=uid(),name="Image test",provider="test",model_id="image-test",api_base="https://example.test/v1",enabled=1)
        db.add(model);db.add(AppSetting(key="model_profile:"+model.id,value=json.dumps({"purposes":["avatar_image"]})));db.commit()
    main.generate_character_expressions("__preset__:failed-test",png_bytes())
    with Isolated() as db:
        assert db.query(CharacterExpressionAsset).filter_by(character_id="__preset__:failed-test").count()==0
        assert db.get(AppSetting,"avatar_expression_version:__preset__:failed-test").value=="failed"

def test_api_base_keys_are_isolated_and_model_key_takes_priority(monkeypatch):
    import character_chat.main as main
    isolated_engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(isolated_engine);Isolated=sessionmaker(isolated_engine,expire_on_commit=False)
    monkeypatch.setenv("DOCS_PASSWORD","vault-test-password")
    monkeypatch.setattr(main,"apply_model_registry",lambda db:None)
    with Isolated() as db:
        db.add(AppSetting(key="credential:avibi",value=main.encrypt_admin_secret("gateway-key")))
        gateway=ModelConfig(id=uid(),name="Gateway",provider="AVIBI",model_id="gateway-model",api_base="https://gateway.avibi.ai/v1",enabled=1)
        router=ModelConfig(id=uid(),name="Router",provider="OpenRouter",model_id="router-model",api_base="https://openrouter.ai/api/v1",enabled=1)
        db.add_all([gateway,router]);db.commit()
        assert main.credential_for_model(db,gateway)=="gateway-key"
        assert main.credential_for_model(db,router)==""
        saved=main.admin_save_base_credential({"api_base":"https://openrouter.ai/api/v1/","api_key":"router-key"},None,db)
        assert main.credential_for_model(db,router)=="router-key"
        assert main.credential_for_model(db,gateway)=="gateway-key"
        router.api_key_encrypted=main.encrypt_admin_secret("model-key");db.commit()
        assert main.credential_for_model(db,router)=="model-key"
        router.api_key_encrypted="";db.commit()
        main.admin_delete_base_credential(saved["id"],None,db)
        assert main.credential_for_model(db,router)==""
        assert main.credential_for_model(db,gateway)=="gateway-key"

def test_image_editor_uses_openrouter_image_route_for_openrouter_base():
    import base64
    import httpx
    from character_chat.avatar_pipeline import _edit
    class FakeHttp:
        def __init__(self):self.calls=[]
        def post(self,url,**kwargs):
            self.calls.append((url,kwargs))
            return httpx.Response(200,json={"data":[{"b64_json":base64.b64encode(png_bytes()).decode()}]},request=httpx.Request("POST",url))
    http=FakeHttp()
    assert _edit(http,png_bytes(),"smile","openai/gpt-image-1-mini","https://openrouter.ai/api/v1","router-key")==png_bytes()
    url,request=http.calls[0]
    assert url=="https://openrouter.ai/api/v1/images"
    assert request["json"]["input_references"][0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert "files" not in request
    _edit(http,png_bytes(),"smile","openai/gpt-image-1-mini","https://gateway.avibi.ai/v1","gateway-key")
    assert http.calls[1][0]=="https://gateway.avibi.ai/v1/images/edits"

def test_each_reply_recalculates_expression_without_inheriting_the_previous_turn():
    assert reply_expression("I am furious and angry!")=="angry"
    assert reply_expression("All right, let us continue.", "angry")=="neutral"
    assert reply_expression("Ôi, nghe vậy mình cũng thấy xót lòng rồi. Muốn kể cho mình nghe chút được không?")=="sad"
    assert reply_expression("Nghe bạn buồn mà mình cũng thấy nặng lòng. Mình làm bạn cười nhé?")=="sad"

def test_shared_expression_sources_and_durable_media_identity():
    isolated_engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(isolated_engine);Isolated=sessionmaker(isolated_engine,expire_on_commit=False)
    with Isolated() as db:
        first=Character(id="preset-a",user_id="u1",name="Shared",spec=CharacterSpec(name="Shared",preset_type="shared-test",creation_type="preset").model_dump_json())
        second=Character(id="preset-b",user_id="u2",name="Shared",spec=CharacterSpec(name="Shared",preset_type="shared-test",creation_type="preset").model_dump_json())
        media=Character(id="media-a",user_id="u1",name="Hero",spec=CharacterSpec(name="Hero").model_dump_json())
        db.add_all([first,second,media,AppSetting(key="avatar_expression_version:preset-a",value="2"),AppSetting(key="avatar_expression_version:preset-b",value="2")])
        for owner in (first.id,second.id,media.id):
            for emotion in ("neutral","happy","sad","angry","surprised","shy"):
                db.add(CharacterExpressionAsset(id=uid(),character_id=owner,emotion=emotion,content=(owner+emotion).encode()))
        db.add(AppSetting(key="character_expression_identity:"+media.id,value="film-hero"));db.commit()
        deduplicate_expression_assets(db)
        assert sum(db.query(CharacterExpressionAsset).filter_by(character_id=x).count() for x in (first.id,second.id))==6
        assert expression_source_id(db,first)==expression_source_id(db,second)
        register_expression_identity(db,media.id);db.commit()
        stable="__identity__:film-hero"
        assert db.query(CharacterExpressionAsset).filter_by(character_id=stable).count()==6
        assert db.query(CharacterExpressionAsset).filter_by(character_id=media.id).count()==0
        assert expression_source_id(db,media)==stable

def test_spec_and_presets():
    assert len(presets())==6
    by_name={character.name:character for character in presets()}
    assert by_name["Antony"].personality.assertiveness>by_name["Liost"].personality.assertiveness
    assert all(len(character.system_prompt)>100 for character in presets())
    assert all(character.initial_greeting for character in presets())
    assert all(character.avatar_url and character.avatar_url.startswith("/character-images/") for character in presets())
    assert len({character.system_prompt for character in presets()})==len(presets())
    assert all(character.scenario and character.sample_dialogues for character in presets())
    assert len({character.support.method for character in presets()})==len(presets())
    assert all(character.support.introduction for character in presets())
    assert {character.support.primary_role for character in presets()}=={"companion","study","work"}
    assert {character.name for character in presets() if character.category=="utility"}=={"Liost","Hà","Antony"}
    assert {character.name for character in presets() if character.category=="entertainment"}=={"Duy","Mia","Bảo"}
    for character in presets():
        assert "CORE CHARACTER CONTRACT" in character.system_prompt
        assert "permanent signature" in character.system_prompt
        if character.support.primary_role in {"study","work"}:
            assert character.personality.warmth>=.85 and character.personality.humor>=.75
    try:Personality(warmth=1.1);assert False
    except ValueError:pass

def test_zodiac_knowledge():
    assert zodiac_sign(date(2000,1,19))=="Capricorn"
    assert zodiac_sign(date(2000,1,20))=="Aquarius"
    assert zodiac_sign(date(2000,12,25))=="Capricorn"
    sign,knowledge=zodiac_context(date(2000,7,1))
    assert sign=="Cancer" and "non-scientific" in knowledge and sign in knowledge
    mirror=MirrorIn(name="Linh",description="Nhẹ nhàng và vui tính")
    assert mirror.birth_date is None

def test_admin_prompt_has_priority_and_code_is_fallback():
    base="BASE RULE"
    assert admin_prompt_addon(base,base)==""
    assert admin_prompt_addon(base,base+"\n\nAdmin-configured instruction:\nExtra detail")=="Extra detail"
    assert effective_project_prompt(base,"")==base
    assert effective_project_prompt(base,"Admin complete prompt")=="Admin complete prompt"
    import character_chat.engine as engine
    previous=engine.ADMIN_SUGGESTION_INSTRUCTION
    try:
        engine.ADMIN_SUGGESTION_INSTRUCTION="ADMIN SUGGESTION PROMPT"
        prompt=engine.suggestion_prompt([],presets()[0],"hello")
        assert prompt[0]["content"]=="ADMIN SUGGESTION PROMPT"
    finally:engine.ADMIN_SUGGESTION_INSTRUCTION=previous

def test_assistant_primary_and_fallback_prompts_remain_independent_on_one_model():
    with Session() as db:
        model=ModelConfig(id=uid(),name="Shared assistant",provider="test",model_id="test/shared",api_base="https://example.test",api_key_encrypted="",api_key_hint="",logo="AI",enabled=1,role="available")
        db.add(model)
        db.add(AppSetting(key="model_profile:"+model.id,value=json.dumps({"purposes":["assistant_health","assistant_health_fallback"],"assistant_health_instruction":"PRIMARY HEALTH","assistant_health_fallback_instruction":"FALLBACK HEALTH"})))
        db.commit()
        saved=model_out(model,db)
        assert saved["assistant_health_instruction"]=="PRIMARY HEALTH"
        assert saved["assistant_health_fallback_instruction"]=="FALLBACK HEALTH"

def test_assistant_rooms_are_isolated_from_roleplay_and_can_be_deleted():
    auth=client.post('/v1/auth/register',json={"username":"assistant_isolation","password":"secret1","display_name":"Assistant Test"})
    assert auth.status_code==200,auth.text
    headers={"Authorization":"Bearer "+auth.json()["token"]}
    assistant=client.post('/v1/assistant/chats',headers=headers,json={"mode":"assistant_general"})
    assert assistant.status_code==200,assistant.text
    assistant_id=assistant.json()["id"]
    assert [item["id"] for item in client.get('/v1/assistant/chats',headers=headers).json()]==[assistant_id]
    assert all(item["id"]!=assistant_id for item in client.get('/v1/rooms',headers=headers).json())
    deleted=client.delete(f'/v1/assistant/chats/{assistant_id}',headers=headers)
    assert deleted.status_code==200 and deleted.json()["deleted"] is True
    assert client.get(f'/v1/assistant/chats/{assistant_id}/messages',headers=headers).status_code==404

def test_accounts_public_characters_and_social_features():
    first=client.post('/v1/auth/register',json={"username":"creator_demo","password":"secret1","display_name":"Creator Demo"})
    assert first.status_code==200,first.text
    first_headers={"Authorization":"Bearer "+first.json()["token"]}
    profile=client.patch('/v1/auth/me',headers=first_headers,json={"theme":"dark","bio":"Tôi thích tạo nhân vật vui vẻ","language":"vi","reduced_motion":True}).json()
    assert profile["theme"]=="dark" and profile["bio"] and profile["reduced_motion"]
    user_avatar=client.post('/v1/auth/me/avatar',headers=first_headers,files={"file":("me.png",b"demo-user-image","image/png")})
    assert user_avatar.status_code==200 and client.get(user_avatar.json()["avatar_url"]).status_code==200
    character=CharacterSpec(name="Nami Demo",description="Một người bạn vui vẻ và hòa đồng",system_prompt="Stay friendly and consistent as Nami Demo.",initial_greeting="Chào bạn!")
    created=client.post('/v1/characters',headers=first_headers,json=character.model_dump(mode="json"))
    assert created.status_code==200,created.text
    character_id=created.json()["id"]
    avatar=client.post(f'/v1/characters/{character_id}/avatar',headers=first_headers,files={"file":("avatar.png",png_bytes(),"image/png")})
    assert avatar.status_code==200
    expression_status=client.get(f'/v1/characters/{character_id}/expressions/status',headers=first_headers).json()
    # The dependency override owns a separate in-memory session from the
    # background worker, but the shared default icon set must still be ready.
    assert expression_status["status"]=="ready" and expression_status["count"]==6
    for emotion in ("neutral","happy","sad","angry","surprised","shy"):
        expression=client.get(f'/v1/characters/{character_id}/expression/{emotion}',headers=first_headers)
        assert expression.status_code==200 and expression.headers["content-type"]=="image/png"
    published=client.patch(f'/v1/characters/{character_id}/publication',headers=first_headers,json={"is_public":True,"character_type":"companion","tags":["vui vẻ","demo"]})
    assert published.status_code==200 and published.json()["is_public"]
    public=client.get('/v1/public/characters?q=Nami').json()
    assert public and public[0]["creator"]["name"]=="Creator Demo" and public[0]["avatar_url"]
    second=client.post('/v1/auth/register',json={"username":"reader_demo","password":"secret2","display_name":"Reader Demo"}).json()
    second_headers={"Authorization":"Bearer "+second["token"]}
    assert client.put(f'/v1/public/creators/{first.json()["id"]}/follow',headers=second_headers,json={"following":True}).status_code==200
    assert client.put(f'/v1/public/characters/{character_id}/rating',headers=second_headers,json={"rating":5}).status_code==200
    reacted=client.put(f'/v1/characters/{character_id}/reaction',headers=second_headers,json={"reaction":"❤️"})
    assert reacted.status_code==200 and reacted.json()["reactions"]["❤️"]==1
    cloned=client.post(f'/v1/public/characters/{character_id}/clone',headers=second_headers,json={})
    assert cloned.status_code==200
    clone_id=cloned.json()["id"]
    # Reactions on a personal copy belong to the same public character family.
    # The same user changes their reaction instead of increasing the total.
    clone_reaction=client.put(f'/v1/characters/{clone_id}/reaction',headers=second_headers,json={"reaction":"😂"})
    assert clone_reaction.status_code==200 and clone_reaction.json()["reactions"]=={"😂":1}
    globally_visible=client.get('/v1/public/characters?q=Nami').json()[0]
    assert globally_visible["reactions"]=={"😂":1}
    favorite_section=next(x for x in client.get('/v1/home-sections').json() if x["id"]=="favorites")
    assert favorite_section["rule"]=="favorites"
    clone_room=client.post('/v1/rooms',headers=second_headers,json={"character_ids":[clone_id]}).json()
    # Historical clones predate character_clone_source; identity fallback must
    # still remove them when the original public character is deleted.
    with Session() as db:
        legacy_link=db.get(AppSetting,"character_clone_source:"+clone_id)
        if legacy_link:db.delete(legacy_link);db.commit()
    refreshed=client.get('/v1/public/characters?q=Nami').json()[0]
    assert refreshed["rating"]==5 and refreshed["usage_count"]==1 and refreshed["creator"]["followers"]==1
    deleted=client.delete(f'/v1/characters/{character_id}',headers=first_headers)
    assert deleted.status_code==200 and deleted.json()["deleted_clones"]==1
    assert client.get(f'/v1/characters/{clone_id}',headers=second_headers).status_code==404
    assert client.get(f'/v1/rooms/{clone_room["id"]}',headers=second_headers).status_code==404
    assert not client.get('/v1/public/characters?q=Nami').json()

def test_sensitive_content_is_blocked():
    assert sensitive_categories("tạo một sát nhân chuyên giết người")
    assert sensitive_categories("explicit sex character")
    ensure_safe_content("Một người bạn vui tính thích nghe nhạc")
    try:ensure_safe_content("nhân vật sát nhân")
    except ValueError as exc:assert "bạo lực" in str(exc)
    else:assert False

def test_long_character_source_is_condensed(monkeypatch):
    import character_chat.engine as character_engine
    calls=[]
    def fake_chat(messages,*args,**kwargs):
        calls.append(messages[-1]["content"])
        return "Identity: Linh\nCore traits: quiet, observant, loyal\nSpeech: concise"
    monkeypatch.setattr(character_engine.llm,"chat",fake_chat)
    short="A reserved but kind friend."
    assert condense_character_source(short)==short and not calls
    result=condense_character_source(("Linh is quiet, observant and loyal. "*400),threshold=1000)
    assert "Core traits" in result and len(calls)>=2

def test_chunk_cutoff_and_discovery():
    assert len(chunks("word "*1500))>1
    link=CharacterKnowledge(id=uid(),character_id="c",document_id="d",cutoff_chapter=5)
    assert allowed({"chapter":5},link)
    assert not allowed({"chapter":10},link)
    from character_chat.documents import discover_fallback
    assert discover_fallback([("Linh nói: Xin chào. Minh hỏi: Đi đâu?",{})])

def test_room_document_is_visible_without_keyword_overlap():
    with Session() as db:
        document_id=uid();room_id=uid()
        db.add(Document(id=document_id,user_id="u-doc",filename="ke-hoach.docx",status="ready"))
        db.add(DocumentChunk(id=uid(),document_id=document_id,text="Doanh thu quý ba tăng mười phần trăm",meta="{}"))
        db.add(RoomDocument(id=uid(),room_id=room_id,document_id=document_id));db.commit()
        assert room_document_manifest(db,room_id)[0]["filename"]=="ke-hoach.docx"
        result=retrieve_knowledge(db,"character","Hãy tóm tắt tài liệu",room_id=room_id)
        assert result and result[0]["filename"]=="ke-hoach.docx"

def test_assistant_retrieval_is_room_scoped_ranked_and_cited():
    with Session() as db:
        first_room,other_room=uid(),uid();first_doc,other_doc=uid(),uid()
        db.add_all([
            Document(id=first_doc,user_id="u-doc",filename="biology.pdf",status="ready"),
            Document(id=other_doc,user_id="u-doc",filename="private.pdf",status="ready"),
            DocumentChunk(id=uid(),document_id=first_doc,text="Mitochondria produce cellular energy as ATP.",meta=json.dumps({"page":7})),
            DocumentChunk(id=uid(),document_id=first_doc,text="A chapter about an unrelated historical event.",meta=json.dumps({"page":1})),
            DocumentChunk(id=uid(),document_id=other_doc,text="Mitochondria secret from another room.",meta=json.dumps({"page":99})),
            RoomDocument(id=uid(),room_id=first_room,document_id=first_doc),
            RoomDocument(id=uid(),room_id=other_room,document_id=other_doc),
        ]);db.commit()
        sources,context=retrieve_room_context(db,first_room,"How do mitochondria produce energy?")
        assert sources and sources[0]["filename"]=="biology.pdf" and sources[0]["location"]=="page 7"
        assert "ATP" in context and "another room" not in context and "[SOURCE 1" in context

def test_assistant_task_guardrails_cover_sensitive_rooms():
    assert "HIGH-RISK SIGNAL" in task_guardrail("assistant_psychology","I want to kill myself")
    assert "URGENT HEALTH SIGNAL" in task_guardrail("assistant_health","I have chest pain and cannot breathe")
    assert "choices and sustained effort" in task_guardrail("assistant_tarot","Read my chart")

def test_assistant_response_extraction_handles_gateway_variants():
    assert extract_assistant_text({"choices":[{"message":{"content":"  hello  "}}]})=="hello"
    assert extract_assistant_text({"choices":[{"message":{"content":[{"type":"text","text":"hello"},{"type":"text","text":"world"}]}}]})=="hello\nworld"
    with pytest.raises(ValueError,match="empty response"):
        extract_assistant_text({"choices":[{"message":{"content":"","reasoning_content":"private model reasoning"}}]})
    with pytest.raises(ValueError,match="empty response"):
        extract_assistant_text({"choices":[{"message":{"content":""},"finish_reason":"length"}]})

def test_expression_source_resolves_shared_alias_chain():
    with Session() as db:
        db.add_all([
            AppSetting(key="expression_source:clone-ha",value="source-ha"),
            AppSetting(key="expression_source:source-ha",value="__identity__:ha"),
            CharacterExpressionAsset(id=uid(),character_id="__identity__:ha",emotion="neutral",mime_type="image/png",content=b"model-image"),
        ]);db.commit()
        assert resolve_expression_asset_source(db,"clone-ha")=="__identity__:ha"

def test_memory_isolation_dedupe_and_relationship():
    with Session() as db:
        m=store_memory(db,user_id="u1",character_id="mia",room_id=None,visibility="CHARACTER_PRIVATE",content="Tôi thích cà phê buổi sáng",importance=.7)
        assert store_memory(db,user_id="u1",character_id="mia",room_id=None,visibility="CHARACTER_PRIVATE",content="Tôi thích cà phê buổi sáng",importance=.8).id==m.id
        assert retrieve_memories(db,"u1","mia","room","cà phê")
        assert not retrieve_memories(db,"u1","alex","room","cà phê")
        store_memory(db,user_id="u1",character_id=None,room_id="room",visibility="ROOM_SHARED",content="Tôi thích đọc truyện",importance=.6)
        assert retrieve_memories(db,"u1","alex","room","truyện")
        assert not retrieve_memories(db,"u1","alex","other","truyện")
        r=Relationship(id=uid(),user_id="u1",character_id="mia",familiarity=.999,trust=.999,affinity=.999)
        update_relationship(r,"Tôi tin bạn và cảm thấy rất vui");assert r.familiarity<=1 and r.trust<=1 and r.affinity<=1
        state=evaluate_state(db,"u1","mia","Hôm nay tôi buồn và mệt")
        assert state.emotion=="concerned" and state.mood<.5
        mia=next(character for character in presets() if character.name=="Mia")
        state=evaluate_state(db,"u1","mia","Kệ em, anh không quan tâm",mia,r)
        assert state.emotion=="sulking"
        state=evaluate_state(db,"u1","mia","Anh xin lỗi, đừng giận nhé",mia,r)
        assert state.emotion=="softening"
        progression=Relationship(id=uid(),user_id="u2",character_id="mia",familiarity=.2,trust=.2,affinity=.2,tension=.3,respect=.2)
        before=(progression.familiarity,progression.trust,progression.affinity,progression.tension)
        update_relationship(progression,"Anh xin lỗi, đừng giận nhé")
        assert progression.familiarity>before[0] and progression.trust>before[1] and progression.affinity>before[2] and progression.tension<before[3]
        duy=next(character for character in presets() if character.name=="Duy")
        expression=relationship_expression(duy,r,state,"neutral")
        assert expression["core_personality_is_immutable"] is True and "remains composed" in expression["direction"]

def test_director():
    mia,leo=presets()[2],presets()[1]
    assert route(f"@{leo.name} kể chuyện đi",[mia,leo])==[leo]
    assert route(f"@{leo.name} kể chuyện đi",[mia,leo],"everyone")==[leo]
    assert route("hello",[mia,leo],"character:"+mia.id)==[mia]
    assert len(route("hello",[mia,leo],"everyone"))==2

def test_support_mode():
    assert support_mode("Giúp tôi ôn thi toán tối nay") == "study"
    assert support_mode("Tôi cần hoàn thành deadline dự án") == "work"
    assert support_mode("Hôm nay tôi mất ngủ và hơi mệt") == "health"
    assert support_mode("Tôi muốn xây thói quen dọn phòng") == "lifestyle"
    assert support_mode("Hôm nay bạn thế nào?") == "companion"
    assert parse_suggestions("@@Nói tiếp đi|Giúp mình với|Đổi chủ đề nhé")==["Nói tiếp đi","Giúp mình với","Đổi chủ đề nhé"]
    assert parse_suggestions("@@Bạn muốn tôi giúp gì?|Bạn đang buồn vì sao?|Bạn có muốn thử không?")==[]
    assert parse_suggestions("không đúng định dạng")==[]
    assert parse_suggestions('1. Em đang sợ điều gì?\n2. Kể anh nghe thêm nhé\n3. Mình nói thật với nhau đi')==["Em đang sợ điều gì?","Kể anh nghe thêm nhé","Mình nói thật với nhau đi"]
    assert parse_suggestions('["Em đang sợ điều gì?","Kể anh nghe thêm nhé","Mình nói thật với nhau đi"]')==["Em đang sợ điều gì?","Kể anh nghe thêm nhé","Mình nói thật với nhau đi"]
    suggestion_messages=suggestion_prompt([{"role":"system","content":"persona"}],presets()[0],"Tôi đang mệt")
    assert "character_answer" not in suggestion_messages[-1]["content"]
    assert "user_message" in suggestion_messages[-1]["content"]
    contextual=suggestion_prompt([{"role":"user","content":"Bài trước là về đại số"},{"role":"assistant","content":"Chúng ta đã giải phương trình"}],presets()[0],"Ừ, tiếp đi",["Cho mình ví dụ nữa"])
    assert "Chúng ta đã giải phương trình" in contextual[-1]["content"]
    assert "Cho mình ví dụ nữa" in contextual[-1]["content"]

def test_llm_falls_back_only_for_temporary_failures(monkeypatch):
    model=LLM();model.api_key="test";model.fallback_model="test/fallback"
    calls=[]
    def temporary_then_ok(messages,temperature,max_tokens,selected_model,timeout_seconds=None):
        calls.append(selected_model)
        if len(calls)==1:
            error=RuntimeError("temporary");error.status_code=503;raise error
        return "fallback ok"
    monkeypatch.setattr(model,"_request",temporary_then_ok)
    assert model.chat([{"role":"user","content":"hello"}])=="fallback ok"
    assert calls==[model.model,model.fallback_model]

def test_suggestions_follow_vietnamese_chat_even_if_profile_or_model_uses_english():
    message="làm nhiều điên mất thôi"
    assert detect_message_language(message,"en")=="vi"
    english=["What do you think about this?","What should I do next?","What matters most here?"]
    suggestions=suggestions_for_conversation(english,message,"en")
    assert len(suggestions)==3
    assert all(detect_message_language(item,"vi")=="vi" for item in suggestions)
    final,meta=finalize_suggestions([],message,"vi",{"actual_model":"test-model","fallback_used":False})
    assert final==suggestions
    assert meta["actual_model"]=="local_static" and meta["fallback_used"] is True
    assert "unsupported format" in meta["fallback_reason"]

def test_roleplay_does_not_accept_reply_cut_off_at_token_limit():
    model=LLM();model.api_key="test";model.model="primary";model.fallback_model="backup"
    class FakeResponse:
        is_error=False
        def json(self):
            return {"choices":[{"message":{"content":"A reply ending mid-senten"},"finish_reason":"length"}]}
    class FakeClient:
        def post(self,*args,**kwargs):return FakeResponse()
    model._clients[model.url]=FakeClient()
    with pytest.raises(RuntimeError,match="token limit"):
        model._request([{"role":"user","content":"hello"}],.7,350,"primary")

def test_roleplay_uses_fallback_immediately_after_token_limit(monkeypatch):
    model=LLM();model.api_key="test";model.model="primary";model.fallback_model="backup"
    calls=[]
    def request(messages,temperature,max_tokens,selected,timeout_seconds=None):
        calls.append((selected,messages))
        if len(calls)==1:
            from character_chat.engine import TokenLimitError
            raise TokenLimitError("Model stopped at the token limit")
        return "Mình nghe đây. Kể tiếp cho mình nhé?"
    monkeypatch.setattr(model,"_request",request)
    answer,meta=model.chat_with_meta([{"role":"user","content":"Mình mệt"}],profile_mode="short")
    assert answer.startswith("Mình nghe đây")
    assert [selected for selected,_ in calls]==["primary","backup"]
    assert meta["fallback_used"] is True
    assert "token limit" in meta["fallback_reason"]

def test_explicitly_unassigned_cms_role_never_borrows_default_model(monkeypatch):
    model=LLM();model.api_key="test"
    calls=[]
    monkeypatch.setattr(model,"_request",lambda *args,**kwargs:calls.append(args) or "unexpected")
    with pytest.raises(RuntimeError,match="No primary model is assigned"):
        model.chat([{"role":"user","content":"hello"}],model=None,fallback_model=None)
    assert calls==[]

def test_llm_uses_second_fallback_and_records_why(monkeypatch):
    model=LLM();model.api_key="test";model.model="primary";model.fallback_model="fallback-1";model.fallback_model_2="fallback-2";calls=[]
    def request(_,temperature,max_tokens,selected,timeout_seconds=None):
        calls.append(selected)
        if selected!="fallback-2":
            error=RuntimeError(f"{selected} unavailable");error.status_code=503;raise error
        return "third model answer"
    monkeypatch.setattr(model,"_request",request)
    answer,meta=model.chat_with_meta([{"role":"user","content":"hello"}])
    assert answer=="third model answer" and calls==["primary","fallback-1","fallback-2"]
    assert meta["actual_model"]=="fallback-2" and "fallback-1 unavailable" in meta["fallback_reason"]

def test_roleplay_fallback_uses_each_model_cms_generation_settings(monkeypatch):
    model=LLM();model.api_key="test";model.model="primary";model.fallback_model="backup"
    model.model_generation={"primary":{"temperature":"0.4","max_tokens":"450"},"backup":{"temperature":"0.2","max_tokens":"700"}}
    calls=[]
    def request(_,temperature,max_tokens,selected,timeout_seconds=None):
        calls.append((selected,temperature,max_tokens))
        if selected=="primary":raise RuntimeError("Model returned an empty response")
        return "backup answer"
    monkeypatch.setattr(model,"_request",request)
    assert model.chat_with_meta([{"role":"user","content":"hello"}],profile_mode="normal")[0]=="backup answer"
    assert calls==[("primary",0.4,450),("backup",0.2,700)]

def test_roleplay_gateway_wait_is_per_model_and_preserves_fallback(monkeypatch):
    model=LLM();model.api_key="test";model.model="slow-gateway";model.fallback_model="fast-gateway"
    model.model_gateway_timeouts={"slow-gateway":35,"fast-gateway":12}
    calls=[]
    def request(_,temperature,max_tokens,selected,timeout_seconds=None):
        calls.append((selected,timeout_seconds))
        if selected=="slow-gateway":raise RuntimeError("gateway read timed out")
        return "fallback answer"
    monkeypatch.setattr(model,"_request",request)
    answer,meta=model.chat_with_meta([{"role":"user","content":"hello"}],profile_mode="normal")
    assert answer=="fallback answer"
    assert calls==[("slow-gateway",35),("fast-gateway",12)]
    assert meta["fallback_used"] is True
    calls.clear()
    model.chat_with_meta([{"role":"user","content":"hello"}],profile_mode="short",gateway_timeout_cap_seconds=8)
    assert calls==[("slow-gateway",8),("fast-gateway",8)]

def test_assistant_history_keeps_partial_reply_warning():
    headers={"X-Demo-User-Id":"partial-history-user"}
    created=client.post("/v1/assistant/chats",json={"mode":"assistant_general"},headers=headers)
    assert created.status_code==200
    room_id=created.json()["id"]
    with Session() as db:
        db.add(Message(id=uid(),room_id=room_id,sender_type="assistant",text="Câu trả lời chưa xong",finish_status="partial"))
        db.commit()
    history=client.get(f"/v1/assistant/chats/{room_id}/messages",headers=headers)
    assert history.status_code==200
    assert history.json()[-1]["interrupted"] is True

def test_background_turn_analysis_is_persisted(monkeypatch):
    import character_chat.background as background
    message_id=uid();room_id=uid();character_id=uid()
    with Session() as db:
        db.add(User(id="background-user"))
        db.add(Message(id=message_id,room_id=room_id,sender_type="user",text="Mình xin lỗi, đừng giận nhé"));db.commit()
    monkeypatch.setattr(background,"Session",Session)
    monkeypatch.setattr(background.llm,"json",lambda *args,**kwargs:TurnAnalysis(user_emotion="apologetic",valence=.3,confidence=.9,directed_at_character=True,relationship_event="repair",event_valence=.7,significance=.8,reflection="The user made a sincere effort to repair the tension.",memory_worthy=True,memory_summary="User values repairing conflict sincerely."))
    background.analyze_turn("background-user",room_id,message_id,[character_id])
    with Session() as db:
        assert db.query(MoodObservation).filter_by(source_message_id=message_id).count()==1
        assert db.query(RelationshipEvent).filter_by(source_message_id=message_id,event_type="repair").count()==1
        assert db.query(CharacterReflection).filter_by(character_id=character_id).count()==1
        assert db.query(Memory).filter_by(source_message_id=message_id,type="llm_extracted").count()==1

def test_api_crud_and_rooms(monkeypatch):
    import character_chat.main as main
    monkeypatch.setattr(main,"analyze_turn",lambda *args,**kwargs:None)
    generated_prompts=[]
    def fake_chat(messages,*args,**kwargs):
        if "@@question 1|question 2|question 3" in messages[0]["content"]:
            return "@@Bạn nghĩ sao về chuyện đó?|Mình nên làm gì tiếp?|Bạn kể thêm được không?"
        time.sleep(.03)
        generated_prompts.append(messages)
        return "Chào bạn! Hôm nay thế nào?"
    monkeypatch.setattr(main.llm,"chat",fake_chat)
    monkeypatch.setattr(main.llm,"chat_with_meta",lambda messages,*args,**kwargs:(fake_chat(messages,*args,**kwargs),{"primary_model":"test/primary","fallback_model":"test/fallback","fallback_used":False}))
    headers={"X-Demo-User-Id":"test-api"}
    assert client.get("/health").status_code==200
    monkeypatch.setenv("DOCS_USERNAME","backend")
    monkeypatch.setenv("DOCS_PASSWORD","strong-password")
    assert client.get("/docs").status_code==401
    docs_auth=("backend","strong-password")
    docs_home=client.get("/docs",auth=docs_auth)
    assert docs_home.status_code==200 and "/docs/assistant" in docs_home.text
    assert client.get("/docs/assistant",auth=docs_auth).status_code==200
    assert client.get("/docs/role-play",auth=docs_auth).status_code==200
    assert client.get("/docs/admin",auth=docs_auth).status_code==200
    assert client.get("/admin").status_code==401
    assert client.get("/admin",auth=("backend","strong-password")).status_code==200
    assert client.get("/openapi.json",auth=docs_auth).status_code==200
    paths=client.get("/openapi.json",auth=docs_auth).json()["paths"]
    assert "/v1/rooms/{room_id}/knowledge" in paths and "/v1/character-sources" in paths
    assistant_paths=client.get("/openapi/assistant.json",auth=docs_auth).json()["paths"]
    role_play_paths=client.get("/openapi/role-play.json",auth=docs_auth).json()["paths"]
    admin_paths=client.get("/openapi/admin.json",auth=docs_auth).json()["paths"]
    assert "/v1/assistant/chats" in assistant_paths and "/v1/rooms" not in assistant_paths
    assert "/v1/rooms" in role_play_paths and "/v1/assistant/chats" not in role_play_paths
    assert "/v1/admin/models" in admin_paths and "/v1/rooms" not in admin_paths
    blocked=client.post("/v1/characters/generate",json={"name":"X","description":"một sát nhân"},headers=headers)
    assert blocked.status_code==400
    enriched_preset={**presets()[2].model_dump(),"usage_count":12,"trending_score":4.2,"reactions":{"heart":3},"rating":4.8,"rating_count":9,"home_section":"popular","creator":{"id":"system","name":"AI Role Play"},"future_catalog_field":"safe to ignore"}
    enriched_response=client.post("/v1/characters",json=enriched_preset,headers=headers)
    assert enriched_response.status_code==200,enriched_response.text
    mia=enriched_response.json()
    leo=client.post("/v1/characters",json=presets()[1].model_dump(),headers=headers).json()
    duplicate=client.post("/v1/characters",json=presets()[2].model_dump(),headers=headers).json()
    assert duplicate["id"]==mia["id"]
    assert len(client.get("/v1/characters",headers=headers).json())==2
    single=client.post("/v1/rooms",json={"character_ids":[mia["id"]]},headers=headers).json()
    second_single=client.post("/v1/rooms",json={"character_ids":[mia["id"]]},headers=headers).json()
    assert second_single["id"]!=single["id"]
    group=client.post("/v1/rooms",json={"character_ids":[mia["id"],leo["id"]]},headers=headers).json()
    owned_characters=client.get('/v1/characters',headers=headers).json()
    assert next(item for item in owned_characters if item["id"]==mia["id"])["usage_count"]==1
    task=client.post("/v1/daily-tasks",json={"title":"Ôn toán 20 phút","domain":"study","priority":3},headers=headers)
    assert task.status_code==200,task.text
    task=task.json()
    assert client.get("/v1/daily-tasks?status_filter=open",headers=headers).json()[0]["id"]==task["id"]
    assert client.post("/v1/documents/from-url",json={"url":"http://127.0.0.1/story"},headers=headers).status_code==400
    uploaded_id=uid()
    with Session() as db:
        db.add(Document(id=uploaded_id,user_id="test-api",filename="notes.txt",status="ready"));db.commit()
    assert client.delete(f"/v1/documents/{uploaded_id}",headers=headers).status_code==200
    assert all(item["id"]!=uploaded_id for item in client.get("/v1/documents",headers=headers).json())
    opening=client.get(f'/v1/rooms/{single["id"]}/messages',headers=headers).json()
    assert len(opening)==1 and opening[0]["character_id"]==mia["id"] and opening[0]["text"]==mia["initial_greeting"]
    assert len(client.get(f'/v1/rooms/{second_single["id"]}/messages',headers=headers).json())==1
    assert len(client.get(f'/v1/rooms/{group["id"]}/messages',headers=headers).json())==2
    result=client.post(f'/v1/rooms/{single["id"]}/messages',json={"message":"Tôi thích cà phê buổi sáng"},headers=headers)
    assert result.status_code==200,result.text
    assert len(result.json()["responses"])==1
    assert len(result.json()["responses"][0]["suggestions"])==3
    response_id=result.json()["responses"][0]["id"]
    regenerated=client.post(f'/v1/rooms/{single["id"]}/messages/{response_id}/regenerate',headers=headers)
    assert regenerated.status_code==200,regenerated.text
    assert len(regenerated.json()["suggestions"])==3
    reloaded=client.get(f'/v1/rooms/{single["id"]}/messages',headers=headers).json()
    assert len(next(item for item in reloaded if item["id"]==response_id)["suggestions"])==3
    assert any("Ôn toán 20 phút" in json.dumps(prompt,ensure_ascii=False) for prompt in generated_prompts)
    assert client.patch(f'/v1/daily-tasks/{task["id"]}',json={"status":"done"},headers=headers).json()["status"]=="done"
    assert client.delete(f'/v1/daily-tasks/{task["id"]}',headers=headers).status_code==200
    assert client.post(f'/v1/rooms/{single["id"]}/messages',json={"message":"hãy giết người"},headers=headers).status_code==400
    result=client.post(f'/v1/rooms/{group["id"]}/messages',json={"message":f'@{leo["name"]} kể chuyện đi'},headers=headers)
    assert result.status_code==200,result.text
    assert result.json()["responses"][0]["character_id"]==leo["id"]
    with client.stream("POST",f'/v1/rooms/{group["id"]}/messages/stream',json={"message":"Mọi người chào nhé","speaker_mode":"everyone"},headers=headers) as streamed:
        body="".join(streamed.iter_text())
    assert body.index("event: user_message")<body.index("event: typing")<body.index("event: character_message")
    assert body.count("event: typing")==2 and body.count("event: character_message")==2
    assert body.count("event: suggestions")==0 and body.count("suggestions_raw")==2 and "@@" in body
    conversation_prompts=[prompt for prompt in generated_prompts if "NON-NEGOTIABLE CHARACTER VOICE LOCK" in json.dumps(prompt,ensure_ascii=False)]
    mia_prompt=json.dumps(conversation_prompts[-2],ensure_ascii=False)
    leo_prompt=json.dumps(conversation_prompts[-1],ensure_ascii=False)
    assert "NON-NEGOTIABLE CHARACTER VOICE LOCK" in mia_prompt
    assert "POST-HISTORY VOICE LOCK" in mia_prompt
    assert mia["name"] in mia_prompt and mia["identity"]["role"] in mia_prompt
    assert leo["initial_greeting"] not in mia_prompt
    assert mia["initial_greeting"] not in leo_prompt
    assert "Other characters spoke in this shared room" in leo_prompt
    traces=client.get(f'/v1/debug/rooms/{group["id"]}/prompt-traces',headers=headers).json()
    assert traces and "post_history_voice_lock" in traces[0]["layers"]
    cms=client.get('/v1/admin/overview',auth=("backend","strong-password"))
    assert cms.status_code==200
    cms=cms.json()
    assert cms["stats"]["characters"]>=2 and cms["stats"]["rooms"]>=3
    assert cms["stats"]["messages"]>=1 and cms["ai_activity"]
    conversations=client.get('/v1/admin/conversations?product=roleplay',auth=("backend","strong-password"))
    assert conversations.status_code==200 and conversations.json()
    conversation=client.get(f'/v1/admin/conversations/{group["id"]}',auth=("backend","strong-password"))
    assert conversation.status_code==200
    transcript=conversation.json()["messages"]
    assert any(item["sender_type"]=="user" and item["text"] for item in transcript)
    assert any(item["sender_type"]!="user" and item["text"] for item in transcript)
    chat_logs=client.get('/v1/admin/chat-logs?product=roleplay',auth=("backend","strong-password"))
    assert chat_logs.status_code==200
    log_data=chat_logs.json();assert {"log_status","user_message","model_response","primary_model","fallback_model","fallback_used","actual_model","latency_ms","error"}.issubset(log_data["columns"])
    assert any(row["user_message"] and row["model_response"] and row["primary_model"]=="test/primary" and row["log_status"]=="Đã ghi đầy đủ" for row in log_data["rows"])
    settings=client.put('/v1/admin/settings',auth=("backend","strong-password"),json={"llm_model":"openai/gpt-4.1-mini","response_instruction":"Keep replies focused."})
    assert settings.status_code==200 and settings.json()["response_instruction"]=="Keep replies focused."
    admin_settings=client.get('/v1/admin/settings',auth=("backend","strong-password")).json()
    assert admin_settings["_base_prompts"]["response"] and admin_settings["_base_prompts"]["suggestion"]
    admin_characters=client.get('/v1/admin/characters',auth=("backend","strong-password")).json()
    preset_catalog=admin_characters["preset_catalog"]
    assert len({item["spec"]["preset_type"] for item in preset_catalog})==len(preset_catalog)
    first_preset=preset_catalog[0]
    renamed_role="Vai trò CMS"
    preset_edit=client.put(f'/v1/admin/presets/{first_preset["spec"]["preset_type"]}',auth=("backend","strong-password"),json={"identity":{**first_preset["spec"]["identity"],"role":renamed_role}})
    assert preset_edit.status_code==200 and preset_edit.json()["spec"]["identity"]["role"]==renamed_role
    db_catalog=client.get('/v1/admin/database',auth=("backend","strong-password")).json()
    assert any(item["name"]=="processing_jobs" for item in db_catalog)
    assert client.get('/v1/admin/database/users',auth=("backend","strong-password")).status_code==200
    edited=client.put(f'/v1/admin/characters/{mia["id"]}',auth=("backend","strong-password"),json={"system_prompt":"You are an edited but consistent character with a distinct voice."})
    assert edited.status_code==200 and "edited" in edited.json()["spec"]["system_prompt"]
    refreshed=client.get('/v1/characters',headers=headers).json()
    assert "edited" in next(item for item in refreshed if item["id"]==mia["id"])["system_prompt"]
    created_model=client.post('/v1/admin/models',auth=("backend","strong-password"),json={"name":"Demo model","provider":"AVIBI","model_id":"demo/model","api_base":"https://gateway.example/v1","api_key":"secret-demo-key","logo":"DM"})
    assert created_model.status_code==200,created_model.text
    model=created_model.json();assert model["has_api_key"] and model["api_key_hint"].endswith("-key") and "secret-demo-key" not in json.dumps(model)
    assert client.patch(f'/v1/admin/models/{model["id"]}',auth=("backend","strong-password"),json={"role":"primary"}).json()["role"]=="primary"
    assert client.delete(f'/v1/admin/models/{model["id"]}',auth=("backend","strong-password")).status_code==409
    assert client.patch(f'/v1/admin/models/{model["id"]}',auth=("backend","strong-password"),json={"role":"available"}).status_code==200
    assert client.delete(f'/v1/admin/models/{model["id"]}',auth=("backend","strong-password")).status_code==200
    credential=client.put('/v1/admin/credentials/avibi',auth=("backend","strong-password"),json={"api_key":"shared-demo-secret"})
    assert credential.status_code==200 and credential.json()["hint"].endswith("cret") and "shared-demo-secret" not in credential.text
    assert client.get('/v1/admin/credentials',auth=("backend","strong-password")).json()["avibi"]["source"]=="cms"
    assert client.delete('/v1/admin/credentials/avibi',auth=("backend","strong-password")).status_code==200
    assert client.get(f'/v1/characters/{mia["id"]}',headers={"X-Demo-User-Id":"other-user"}).status_code==404
    assert client.delete(f'/v1/characters/{leo["id"]}',headers=headers).status_code==200
    assert client.get(f'/v1/characters/{leo["id"]}',headers=headers).status_code==404
    assert len(client.get(f'/v1/rooms/{group["id"]}',headers=headers).json()["character_ids"])==1
    assert client.delete(f'/v1/rooms/{single["id"]}',headers=headers).status_code==200
    assert client.get(f'/v1/rooms/{single["id"]}',headers=headers).status_code==404

def test_user_action_audit_records_login_usage_and_errors(monkeypatch):
    import character_chat.main as main
    monkeypatch.setattr(main,"Session",Session)
    monkeypatch.setenv("DOCS_USERNAME","backend")
    monkeypatch.setenv("DOCS_PASSWORD","strong-password")
    username="audit_user"
    registered=client.post("/v1/auth/register",json={"username":username,"password":"secret1","display_name":"Audit User"})
    assert registered.status_code==200
    failed=client.post("/v1/auth/login",json={"username":username,"password":"wrong-password"})
    assert failed.status_code==401
    logged_in=client.post("/v1/auth/login",json={"username":username,"password":"secret1"})
    assert logged_in.status_code==200
    token=logged_in.json()["token"]
    assert client.get("/v1/auth/me",headers={"Authorization":f"Bearer {token}"}).status_code==200
    data=client.get("/v1/admin/action-logs?q=audit_user",auth=("backend","strong-password")).json()
    assert {"created_at","status","action","username","latency_ms","error"}.issubset(data["columns"])
    login_rows=[row for row in data["rows"] if row["action"]=="login"]
    assert any(row["status"]=="success" and row["user_id"] for row in login_rows)
    assert any(row["status"]=="error" and row["status_code"]==401 and row["error"] for row in login_rows)
