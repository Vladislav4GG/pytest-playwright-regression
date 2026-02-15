import time
from typing import Callable, Iterable

def wait_any(predicates: Iterable[Callable[[], bool]], *, timeout_ms: int = 60000, poll_ms: int = 200) -> int:
    """
    Returns index of the first predicate that becomes True.
    Raises TimeoutError if none become True in time.
    """
    deadline = time.time() + timeout_ms / 1000
    preds = list(predicates)

    last_err = None
    while time.time() < deadline:
        for i, p in enumerate(preds):
            try:
                if p():
                    return i
            except Exception as e:
                last_err = e
        time.sleep(poll_ms / 1000)

    raise TimeoutError(f"None of predicates became true within {timeout_ms} ms. Last error: {last_err}")