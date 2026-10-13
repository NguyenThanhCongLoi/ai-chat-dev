"""api.tasks: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_memory_out(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def memory_out(m):
        return {
            "id": m.id,
            "type": m.type,
            "content": m.content,
            "importance": m.importance,
            "visibility": m.visibility,
            "pinned": bool(m.pinned),
            "created_at": m.created_at,
        }

    runtime.memory_out = memory_out

    def daily_task_out(task):
        return {
            "id": task.id,
            "title": task.title,
            "domain": task.domain,
            "status": task.status,
            "priority": task.priority,
            "notes": task.notes,
            "due_at": task.due_at,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    runtime.daily_task_out = daily_task_out

    @runtime.app.get("/v1/daily-tasks")
    def daily_tasks(
        status_filter: str | None = None,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        query = db.query(runtime.DailyTask).filter_by(user_id=user)
        if status_filter:
            query = query.filter_by(status=status_filter)
        return [
            runtime.daily_task_out(x)
            for x in query.order_by(
                runtime.DailyTask.priority.desc(), runtime.DailyTask.created_at
            ).all()
        ]

    runtime.daily_tasks = daily_tasks

    @runtime.app.post("/v1/daily-tasks")
    def create_daily_task(
        data: runtime.DailyTaskIn,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        try:
            runtime.ensure_safe_content(data.title, data.notes)
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        task = runtime.DailyTask(id=runtime.uid(), user_id=user, **data.model_dump())
        db.add(task)
        db.commit()
        return runtime.daily_task_out(task)

    runtime.create_daily_task = create_daily_task

    @runtime.app.patch("/v1/daily-tasks/{task_id}")
    def patch_daily_task(
        task_id: str,
        data: runtime.DailyTaskPatch,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        task = runtime.owned(db, runtime.DailyTask, task_id, user)
        changes = data.model_dump(exclude_unset=True)
        try:
            runtime.ensure_safe_content(changes)
        except ValueError as exc:
            raise runtime.HTTPException(400, str(exc))
        for key, value in changes.items():
            setattr(task, key, value)
        task.updated_at = runtime.now()
        db.commit()
        return runtime.daily_task_out(task)

    runtime.patch_daily_task = patch_daily_task

    @runtime.app.delete("/v1/daily-tasks/{task_id}")
    def delete_daily_task(
        task_id: str,
        db: runtime.DBSession = runtime.Depends(runtime.db_session),
        user: str = runtime.Depends(runtime.current_user),
    ):
        db.delete(runtime.owned(db, runtime.DailyTask, task_id, user))
        db.commit()
        return {"deleted": True}

    runtime.delete_daily_task = delete_daily_task
