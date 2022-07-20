from .clients.httpClient import HttpClient
from .clients.domain_client import DomainClient
from .clients.copyFactory.configuration_client import ConfigurationClient
from .clients.copyFactory.history_client import HistoryClient
from .clients.copyFactory.trading_client import TradingClient
from typing_extensions import TypedDict
from typing import Optional


class RetryOpts(TypedDict):
    retries: Optional[int]
    """Maximum amount of request retries, default value is 5."""
    minDelayInSeconds: Optional[float]
    """Minimum delay in seconds until request retry, default value is 1."""
    maxDelayInSeconds: Optional[float]
    """Maximum delay in seconds until request retry, default value is 30."""


class CopyFactoryOpts(TypedDict):
    """CopyFactory options"""
    domain: Optional[str]
    """Domain to connect to."""
    extendedTimeout: Optional[float]
    """Timeout for extended http requests in seconds."""
    requestTimeout: Optional[float]
    """Timeout for http requests in seconds."""
    retryOpts: Optional[RetryOpts]
    """Options for request retries."""


class CopyFactory:
    """MetaApi CopyFactory copy trading API SDK"""

    def __init__(self, token: str, opts: CopyFactoryOpts = None):
        """Inits CopyFactory class instance.

        Args:
            token: Authorization token.
            opts: Connection options.
        """
        opts: CopyFactoryOpts = opts or {}
        domain = opts['domain'] if 'domain' in opts else 'agiliumtrade.agiliumtrade.ai'
        request_timeout = opts['requestTimeout'] if 'requestTimeout' in opts else 10
        request_extended_timeout = opts['extendedTimeout'] if 'extendedTimeout' in opts else 70
        retry_opts = opts['retryOpts'] if 'retryOpts' in opts else {}
        http_client = HttpClient(request_timeout, request_extended_timeout, retry_opts)
        self._domainClient = DomainClient(http_client, token, domain)
        self._configurationClient = ConfigurationClient(self._domainClient)
        self._historyClient = HistoryClient(self._domainClient)
        self._tradingClient = TradingClient(self._domainClient)

    @property
    def configuration_api(self) -> ConfigurationClient:
        """Returns CopyFactory configuration API.

        Returns:
            Configuration API.
        """
        return self._configurationClient

    @property
    def history_api(self) -> HistoryClient:
        """Returns CopyFactory history API.

        Returns:
            History API.
        """
        return self._historyClient

    @property
    def trading_api(self) -> TradingClient:
        """Returns CopyFactory history API.

        Returns:
            History API.
        """
        return self._tradingClient
