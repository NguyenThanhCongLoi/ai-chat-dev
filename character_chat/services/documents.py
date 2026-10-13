"""services.documents: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_process_document(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def process_document(document_id, data, filename, job_id=None):
        with runtime.Session() as db:
            doc = db.get(runtime.Document, document_id)
            if not doc:
                return
            doc.status = "processing"
            db.commit()
            job = db.get(runtime.ProcessingJob, job_id) if job_id else None
            if job:
                job.status = "processing"
                job.updated_at = runtime.now()
                db.commit()
            try:
                sections = runtime.parse_document(filename, data)
                runtime.ensure_safe_content(*(text for text, _ in sections))
                runtime.save_chunks(db, document_id, sections)
                source = "\n".join(text for text, _ in sections)[:12000]
                try:
                    overview = runtime.llm.chat(
                        [
                            {
                                "role": "system",
                                "content": "Analyze the uploaded document for retrieval. Give a compact factual overview, main topics, important entities and useful question types. Do not invent facts.",
                            },
                            {"role": "user", "content": source},
                        ],
                        temperature=0.2,
                        max_tokens=350,
                    )
                    db.add(
                        runtime.DocumentChunk(
                            id=runtime.uid(),
                            document_id=document_id,
                            text=overview,
                            meta=runtime.json.dumps(
                                {"kind": "llm_overview"}, ensure_ascii=False
                            ),
                        )
                    )
                except Exception:
                    pass
                doc.status = "ready"
                if job:
                    job.status = "completed"
                    job.updated_at = runtime.now()
            except Exception as exc:
                doc.status = "failed"
                doc.error = str(exc)[:500]
                if job:
                    job.status = "failed"
                    job.error = str(exc)[:500]
                    job.updated_at = runtime.now()
            db.commit()

    runtime.process_document = process_document

    def _safe_public_url(url: str):
        parsed = runtime.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Link phải dùng http hoặc https")
        if parsed.username or parsed.password:
            raise ValueError("Link không được chứa thông tin đăng nhập")
        for result in runtime.socket.getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        ):
            address = runtime.ipaddress.ip_address(result[4][0])
            if not address.is_global:
                raise ValueError("Link nội bộ không được hỗ trợ")

    runtime._safe_public_url = _safe_public_url

    def _download_public_document(url, limit=10_000_000):
        # Validate every destination BEFORE requesting it, including redirects.
        with runtime.httpx.Client(
            timeout=30,
            follow_redirects=False,
            headers={"User-Agent": "CharacterChat/1.0"},
        ) as client:
            for _ in range(6):
                runtime._safe_public_url(str(url))
                with client.stream("GET", url) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("Redirect missing destination")
                        url = response.url.join(location)
                        continue
                    response.raise_for_status()
                    parts = []
                    size = 0
                    for chunk in response.iter_bytes(chunk_size=65536):
                        size += len(chunk)
                        if size > limit:
                            raise ValueError("N?i dung t? link v??t qu? 10 MB")
                        parts.append(chunk)
                    return response, b"".join(parts)
        raise ValueError("Too many redirects")

    runtime._download_public_document = _download_public_document

    def process_document_url(document_id, url, job_id=None):
        with runtime.Session() as db:
            doc = db.get(runtime.Document, document_id)
            if not doc:
                return
            doc.status = "processing"
            db.commit()
            job = db.get(runtime.ProcessingJob, job_id) if job_id else None
            if job:
                job.status = "processing"
                job.updated_at = runtime.now()
                db.commit()
            try:
                response, data = runtime._download_public_document(url)
                content_type = response.headers.get("content-type", "").lower()
                suffix = runtime.Path(
                    runtime.urlparse(str(response.url)).path
                ).suffix.lower()
                if "pdf" in content_type:
                    suffix = ".pdf"
                elif "wordprocessingml" in content_type:
                    suffix = ".docx"
                elif "text/html" in content_type:
                    from html.parser import HTMLParser

                    class TextExtractor(HTMLParser):
                        def __init__(self):
                            super().__init__()
                            self.parts = []
                            self.skip = 0

                        def handle_starttag(self, tag, attrs):
                            if tag in ("script", "style", "noscript"):
                                self.skip += 1

                        def handle_endtag(self, tag):
                            if tag in ("script", "style", "noscript") and self.skip:
                                self.skip -= 1

                        def handle_data(self, text):
                            if not self.skip and text.strip():
                                self.parts.append(text.strip())

                    parser = TextExtractor()
                    parser.feed(
                        data.decode(response.encoding or "utf-8", errors="replace")
                    )
                    data = "\n".join(parser.parts).encode("utf-8")
                    suffix = ".txt"
                if suffix not in (
                    ".txt",
                    ".md",
                    ".pdf",
                    ".docx",
                    ".pptx",
                    ".csv",
                    ".xlsx",
                ):
                    suffix = ".txt"
                sections = runtime.parse_document("source" + suffix, data)
                runtime.ensure_safe_content(*(text for text, _ in sections))
                runtime.save_chunks(db, document_id, sections)
                doc.status = "ready"
                if job:
                    job.status = "completed"
                    job.updated_at = runtime.now()
            except Exception as exc:
                doc.status = "failed"
                doc.error = str(exc)[:500]
                if job:
                    job.status = "failed"
                    job.error = str(exc)[:500]
                    job.updated_at = runtime.now()
            db.commit()

    runtime.process_document_url = process_document_url
