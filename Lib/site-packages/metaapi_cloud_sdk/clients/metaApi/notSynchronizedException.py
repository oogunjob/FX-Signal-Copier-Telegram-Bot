class NotSynchronizedException(Exception):
    """Exception which indicates that MetaApi MetaTrader account was not synchronized yet. See
    https://metaapi.cloud/docs/client/websocket/synchronizationMode/ for more details"""

    def __init__(self, message: str):
        """Inits the exception.

        Args:
            message: Exception message.
        """
        super().__init__(message)
