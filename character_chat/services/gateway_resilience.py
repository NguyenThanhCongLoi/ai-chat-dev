"""services.gateway_resilience: domain-specific application implementation.

Dependencies are injected through the shared application runtime; no global
application import or hidden startup work occurs here. Exported helpers keep the
existing worker/test integration points. Each binder preserves registration order.
"""

from types import ModuleType


def bind_model_circuit_remaining(runtime: ModuleType) -> None:
    """Register these implementations against the supplied application runtime."""

    def model_circuit_remaining(model):
        with runtime.MODEL_CIRCUIT_LOCK:
            return max(
                0, runtime.MODEL_CIRCUIT.get(model, 0) - runtime.time.monotonic()
            )

    runtime.model_circuit_remaining = model_circuit_remaining

    def record_model_failure(model, error):
        if runtime.re.search(
            r"timeout|timed out|handshake|disconnect|connect|HTTP (?:408|5\d\d)|Gateway HTTP (?:408|5\d\d)",
            str(error),
            runtime.re.I,
        ):
            with runtime.MODEL_CIRCUIT_LOCK:
                runtime.MODEL_CIRCUIT[model] = runtime.time.monotonic() + 30

    runtime.record_model_failure = record_model_failure

    def record_model_success(model):
        with runtime.MODEL_CIRCUIT_LOCK:
            runtime.MODEL_CIRCUIT.pop(model, None)

    runtime.record_model_success = record_model_success

    def bounded_remote_chunks(remote_stream, deadline):
        """Bound both direct and Modal streams, releasing upstream responses on exit."""
        iterator = iter(remote_stream)
        pool = runtime.concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = None

        def close_iterator(_=None):
            try:
                if hasattr(iterator, "close"):
                    iterator.close()
            except Exception:
                pass

        def pull_next():
            try:
                return True, next(iterator)
            except StopIteration:
                return False, None

        try:
            while True:
                remaining = deadline - runtime.time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Assistant total response time budget exhausted")
                future = pool.submit(pull_next)
                try:
                    has_value, value = future.result(timeout=remaining)
                except runtime.concurrent.futures.TimeoutError as exc:
                    future.cancel()
                    raise TimeoutError(
                        "Assistant total response time budget exhausted"
                    ) from exc
                if not has_value:
                    return
                yield value
        finally:
            if future is not None and not future.done():
                future.add_done_callback(close_iterator)
            else:
                close_iterator()
            pool.shutdown(wait=False, cancel_futures=True)

    runtime.bounded_remote_chunks = bounded_remote_chunks
