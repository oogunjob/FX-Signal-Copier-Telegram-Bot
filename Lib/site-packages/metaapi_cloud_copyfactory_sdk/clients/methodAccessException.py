class MethodAccessException(Exception):
    """Exception which indicates that user doesn't have access to a method."""

    def __init__(self, method_name: str, access_type: str = 'api'):
        """Inits the method access exception.

        Args:
            method_name: Name of method.
            access_type: Type of method access.
        """
        if access_type == 'api':
            error_message = f'You can not invoke {method_name} method, because you have connected with API ' + \
                            'access token. Please use account access token to invoke this method.'
        elif access_type == 'account':
            error_message = f'You can not invoke {method_name} method, because you have connected with account ' + \
                            'access token. Please use API access token from https://app.metaapi.cloud/token page ' + \
                            'to invoke this method.'
        else:
            error_message = ''
        super().__init__(error_message)
