"""api.documents: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_upload_document(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    @runtime.app.post("/v1/documents")
    def upload_document(
        background: runtime.BackgroundTasks,
        file: runtime.UploadFile = runtime.File(...),
        room_id: str | None = runtime.Form(None),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        filename = file.filename or "document.txt"
        if not filename.lower().endswith(
            (".txt", ".md", ".pdf", ".docx", ".pptx", ".csv", ".xlsx")
        ):
            raise runtime.HTTPException(400, "Unsupported file type")
        data = file.file.read(10_000_001)
        if len(data) > 10_000_000:
            raise runtime.HTTPException(413, "File too large")
        if room_id:
            runtime.owned(db, runtime.Room, room_id, user)
        try:
            runtime.parse_document(filename, data)
        except Exception as exc:
            raise runtime.HTTPException(400, str(exc))
        doc = runtime.Document(
            id=runtime.uid(), user_id=user, filename=filename, status="pending"
        )
        db.add(doc)
        job = runtime.ProcessingJob(
            id=runtime.uid(),
            user_id=user,
            job_type="document_upload",
            status="pending",
            resource_id=doc.id,
            content_preview=filename[:300],
        )
        db.add(job)
        attachment_message = None
        if room_id:
            db.add(
                runtime.RoomDocument(
                    id=runtime.uid(), room_id=room_id, document_id=doc.id
                )
            )
            attachment_message = runtime.Message(
                id=runtime.uid(),
                room_id=room_id,
                sender_type="document",
                character_id=None,
                text=filename,
                sources=runtime.json.dumps(
                    [{"document_id": doc.id}], ensure_ascii=False
                ),
            )
            db.add(attachment_message)
        db.commit()
        background.add_task(runtime.process_document, doc.id, data, filename, job.id)
        result = runtime.document_out(doc)
        if attachment_message:
            result["message_id"] = attachment_message.id
        return result

    runtime.upload_document = upload_document

    @runtime.app.post("/v1/rooms/{room_id}/knowledge")
    def upload_room_knowledge(
        room_id: str,
        background: runtime.BackgroundTasks,
        file: runtime.UploadFile = runtime.File(...),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        """Persistent only for this room's RAG lifetime; never becomes character personality."""
        return runtime.upload_document(background, file, room_id, db, user)

    runtime.upload_room_knowledge = upload_room_knowledge

    @runtime.app.post("/v1/character-sources")
    def upload_character_source(
        background: runtime.BackgroundTasks,
        file: runtime.UploadFile = runtime.File(...),
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        """Temporary source compiled into CharacterSpec and deleted after character creation."""
        return runtime.upload_document(background, file, None, db, user)

    runtime.upload_character_source = upload_character_source

    @runtime.app.post("/v1/documents/from-url")
    def upload_document_url(
        data: runtime.DocumentUrlIn,
        background: runtime.BackgroundTasks,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        try:
            runtime._safe_public_url(data.url)
        except Exception as exc:
            raise runtime.HTTPException(400, str(exc))
        hostname = runtime.urlparse(data.url).hostname or "link"
        filename = (runtime.Path(runtime.urlparse(data.url).path).name or hostname)[
            :180
        ]
        doc = runtime.Document(
            id=runtime.uid(), user_id=user, filename=filename, status="pending"
        )
        db.add(doc)
        db.commit()
        job = runtime.ProcessingJob(
            id=runtime.uid(),
            user_id=user,
            job_type="url_ingestion",
            status="pending",
            resource_id=doc.id,
            content_preview=data.url[:300],
        )
        db.add(job)
        db.commit()
        background.add_task(runtime.process_document_url, doc.id, data.url, job.id)
        return runtime.document_out(doc)

    runtime.upload_document_url = upload_document_url

    def document_out(doc):
        return {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "error": doc.error,
            "created_at": doc.created_at,
        }

    runtime.document_out = document_out

    @runtime.app.get("/v1/documents")
    def documents(
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        attached = {item.document_id for item in db.query(runtime.RoomDocument).all()}
        return [
            runtime.document_out(x)
            for x in db.query(runtime.Document).filter_by(user_id=user).all()
            if x.id not in attached
        ]

    runtime.documents = documents

    @runtime.app.get("/v1/documents/{document_id}")
    def get_document(
        document_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        return runtime.document_out(
            runtime.owned(db, runtime.Document, document_id, user)
        )

    runtime.get_document = get_document

    @runtime.app.delete("/v1/documents/{document_id}")
    def delete_document(
        document_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        doc = runtime.owned(db, runtime.Document, document_id, user)
        links = (
            db.query(runtime.CharacterKnowledge)
            .filter_by(document_id=document_id)
            .all()
        )
        for link in links:
            character = db.get(runtime.Character, link.character_id)
            if character and character.user_id == user:
                character_data = runtime.spec(character)
                character_data.knowledge_document_ids = [
                    item
                    for item in character_data.knowledge_document_ids
                    if item != document_id
                ]
                character.spec = character_data.model_dump_json()
                character.updated_at = runtime.now()
                db.add(
                    runtime.CharacterVersion(
                        id=runtime.uid(), character_id=character.id, spec=character.spec
                    )
                )
            db.delete(link)
        runtime.purge_document_record(db, document_id, force=True)
        db.commit()
        return {"deleted": True, "detached_characters": len(links)}

    runtime.delete_document = delete_document

    @runtime.app.post("/v1/documents/{document_id}/discover-characters")
    def discover(
        document_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        doc = runtime.owned(db, runtime.Document, document_id, user)
        if doc.status != "ready":
            raise runtime.HTTPException(409, "Document is not ready")
        rows = db.query(runtime.DocumentChunk).filter_by(document_id=document_id).all()
        source = "\n".join(c.text for c in rows[:35])[:15000]
        from pydantic import BaseModel

        class CandidateList(BaseModel):
            candidates: list[runtime.DiscoveryCandidate]

        try:
            result = runtime.llm.json(
                [
                    {
                        "role": "user",
                        "content": "Discover fictional characters from this story. Include evidence and relationships. Return up to 10 candidates.\n"
                        + source,
                    }
                ],
                CandidateList,
            )
            return result.model_dump()
        except Exception:
            return {
                "candidates": [
                    c.model_dump()
                    for c in runtime.discover_fallback(
                        [(x.text, runtime.json.loads(x.meta)) for x in rows]
                    )
                ]
            }

    runtime.discover = discover

    @runtime.app.post("/v1/characters/from-document")
    def character_from_document(
        data: runtime.FromDocumentIn,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        doc = runtime.owned(db, runtime.Document, data.document_id, user)
        if doc.status != "ready":
            raise runtime.HTTPException(409, "Document is not ready")
        rows = db.query(runtime.DocumentChunk).filter_by(document_id=doc.id).all()
        filtered = []
        for row in rows:
            meta = runtime.json.loads(row.meta)
            if (
                data.knowledge_cutoff_page is not None
                and meta.get("page", 0) > data.knowledge_cutoff_page
            ):
                continue
            if (
                data.knowledge_cutoff_chapter is not None
                and meta.get("chapter", 0) > data.knowledge_cutoff_chapter
            ):
                continue
            if runtime.re.search(
                r"\b" + runtime.re.escape(data.candidate_name) + r"\b",
                row.text,
                runtime.re.I,
            ):
                filtered.append(row.text)
        context = "\n".join(filtered[:15])[:12000]
        if not context:
            raise runtime.HTTPException(
                400, "Character not found before selected cutoff"
            )
        runtime.enforce_character_policy(
            {"name": data.candidate_name, "story_passages": context}
        )
        _, language_name = runtime.preferred_language(db, user)
        try:
            c = runtime.compile_character(
                f"Write every user-facing field, description and initial greeting in {language_name}. Fictional story character. Use only these passages to derive backstory, personality, motivations, knowledge and speech. Do not use future events.\n{context}",
                data.candidate_name,
                "document",
            )
        except Exception as exc:
            raise runtime.HTTPException(
                503, f"Character compilation unavailable: {exc}"
            )
        c.knowledge_document_ids = []
        c.knowledge_cutoff_page = data.knowledge_cutoff_page
        c.knowledge_cutoff_chapter = data.knowledge_cutoff_chapter
        c.persona_knowledge = list(
            dict.fromkeys(
                [*c.persona_knowledge, *[text[:700] for text in filtered[:6]]]
            )
        )[:12]
        c = runtime.save_character(db, user, c)
        db.query(runtime.DocumentChunk).filter_by(document_id=doc.id).delete()
        db.delete(doc)
        db.commit()
        return c

    runtime.character_from_document = character_from_document
