class DomainError(Exception):
    """An error the client can act on: a stable code, a message for people, the field it concerns."""

    def __init__(self, code: str, message: str, status: int = 422, field: str | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.field = field
        super().__init__(message)
