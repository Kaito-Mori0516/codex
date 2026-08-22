"""Shared acquisition errors for local and AWS runtimes."""


class DataAcquisitionError(RuntimeError):
    """Raised when a remote response cannot be safely consumed."""
