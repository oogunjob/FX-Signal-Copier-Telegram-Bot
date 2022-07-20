class TradeException(Exception):
    """Exception which indicates that a trade has failed."""

    def __init__(self, message: str, numeric_code: int, string_code: str):
        """Inits the timeout exception

        Args:
            message: Exception message.
            numeric_code: Numeric error code.
            string_code: String error code.
        """
        super().__init__(message)
        self.numericCode = numeric_code
        self.stringCode = string_code
