class TimeoutException(Exception):
    """Exception which indicates a timeout."""

    def __init__(self, message: str):
        """Inits the timeout exception

        Args:
            message: Exception message.
        """
        super().__init__(message)
