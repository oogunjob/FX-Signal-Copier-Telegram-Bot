class TimeoutException(Exception):
    """Exception which indicates that MetaTrader terminal did not start yet. You need to wait until account is
    connected and retry.
    """

    def __init__(self, message: str):
        """Inits the timeout exception

        Args:
            message: Exception message.
        """
        super().__init__(message)
