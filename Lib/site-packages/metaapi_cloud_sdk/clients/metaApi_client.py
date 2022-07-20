from .methodAccessException import MethodAccessException


class MetaApiClient:
    """metaapi.cloud MetaTrader API client."""

    def __init__(self, http_client, token: str, domain: str = 'agiliumtrade.agiliumtrade.ai'):
        """Inits MetaTrader API client instance.

        Args:
            http_client: HTTP client.
            token: Authorization token.
            domain: Domain to connect to, default is agiliumtrade.agiliumtrade.ai.
        """
        self._httpClient = http_client
        self._host = f'https://mt-provisioning-api-v1.{domain}'
        self._token = token

    @property
    def _token_type(self) -> str:
        """Returns type of current token.

        Returns:
            Type of current token.
        """
        if isinstance(self._token, str) and len(self._token.split('.')) == 3:
            return 'api'
        if isinstance(self._token, str) and len(self._token.split('.')) == 1:
            return 'account'
        return ''

    def _is_not_jwt_token(self) -> bool:
        """Checks that current token is not api token.

        Returns:
            Indicator of absence api token.
        """
        return (not isinstance(self._token, str)) or len(self._token.split('.')) != 3

    def _is_not_account_token(self) -> bool:
        """Checks that current token is not account token.

        Returns:
            Indicator of absence account token.
        """
        return (not isinstance(self._token, str)) or len(self._token.split('.')) != 1

    def _handle_no_access_exception(self, method_name):
        """Handles no accessing to the method.

        Args:
            method_name: Name of the method.
        """
        raise MethodAccessException(method_name, self._token_type)
