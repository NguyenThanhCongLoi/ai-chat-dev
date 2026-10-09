"""Multiplex model content and ready suggestions without blocking on next chunk."""
import concurrent.futures
import os
import queue
import threading


def suggestion_budget():
    try:
        return max(1, min(90, float(os.getenv("SUGGESTION_BUDGET_SECONDS", "12"))))
    except ValueError:
        return 12


def capture_suggestion(future, state):
    if state.get("sent") or not future.done():
        return False
    state["sent"] = True
    try:
        state["result"] = future.result()
    except Exception as exc:
        state["error"] = exc
    return True


def merge_suggestion_stream(upstream, future, state):
    """Keep queue bounded; emit readiness even while upstream next() is blocked."""
    items = queue.Queue(maxsize=16)
    stopped = threading.Event()
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="chat-events")
    def put(value):
        while not stopped.is_set():
            try:
                items.put(value, timeout=.05)
                return
            except queue.Full:
                pass
    def produce():
        iterator = iter(upstream)
        try:
            for item in iterator:
                if stopped.is_set():
                    break
                put(("item", item))
        except Exception as exc:
            put(("error", exc))
        finally:
            try:
                if hasattr(iterator, "close"):
                    iterator.close()
            except Exception as exc:
                put(("error", exc))
            finally:
                put(("end", None))
    pool.submit(produce)
    try:
        while True:
            if capture_suggestion(future, state):
                yield {"_suggestions_ready": True}
            try:
                kind, value = items.get(timeout=.05)
            except queue.Empty:
                continue
            if kind == "end":
                return
            if kind == "error":
                raise value
            yield value
    finally:
        stopped.set()
        pool.shutdown(wait=False, cancel_futures=True)


def post_stream_suggestion_wait():
    """Client wait starts after answer stream completion, independently of model budget."""
    return 2.5
