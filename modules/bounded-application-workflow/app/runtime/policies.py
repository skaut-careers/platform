class RetryPolicy:
    """Decide whether a failed attempt should be retried."""

    def __init__(
        self,
        *,
        retryable: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self._retryable = retryable

    def should_retry(self, exc: Exception) -> bool:
        return isinstance(exc, self._retryable)
