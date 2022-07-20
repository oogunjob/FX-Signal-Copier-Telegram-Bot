from .clients.httpClient import HttpClient, RetryOpts
from .clients.metaStats_client import MetaStatsClient
from .clients.domain_client import DomainClient
from typing_extensions import TypedDict
from typing import Optional
import traceback


class ConnectionOptions(TypedDict):
    """Connection options."""
    requestTimeout: Optional[float]
    """Request timeout in seconds, default is 60."""
    domain: Optional[str]
    """Request domain, default 'agiliumtrade.agiliumtrade.ai.'"""
    retryOpts: Optional[RetryOpts]
    """Retry options."""


class MetaStats:
    """MetaStats API SDK."""

    def __init__(self, token: str, opts: ConnectionOptions = None):
        """Inits MetaStats class instance.

        Args:
            token: Authorization token.
            opts: Connection options.
        """
        opts: ConnectionOptions = opts or {}
        http_client = HttpClient(opts['requestTimeout'] if 'requestTimeout' in opts else None,
                                 opts['retryOpts'] if 'retryOpts' in opts else None)
        domain_client = DomainClient(http_client, token, opts['domain'] if 'domain' in opts else None)
        self._metaStatsClient = MetaStatsClient(domain_client)

    @property
    def get_metrics(self):
        """Returns the get_metrics MetaStatsClient method bound to the MetaStatsClient instance.

        Returns:
            get_metrics MetaStatsClient method.
        """
        return self._metaStatsClient.get_metrics

    @property
    def get_account_trades(self):
        """Returns the get_account_trades MetaStatsClient method bound to the MetaStatsClient instance.

        Returns:
            get_account_trades MetaStatsClient method.
        """
        return self._metaStatsClient.get_account_trades

    @property
    def get_account_open_trades(self):
        """Returns the get_account_open_trades MetaStatsClient method bound to the MetaStatsClient instance.

        Returns:
            get_account_open_trades MetaStatsClient method.
        """
        return self._metaStatsClient.get_account_open_trades

    @staticmethod
    def format_error(err: Exception):
        """Formats and outputs metaApi errors with additional information.

        Args:
            err: Exception to process.
        """
        error = {'name': err.__class__.__name__, 'message': err.args[0]}
        if hasattr(err, 'status_code'):
            error['status_code'] = err.status_code
        if err.__class__.__name__ == 'ValidationException':
            error['details'] = err.details
        if err.__class__.__name__ == 'TooManyRequestsException':
            error['metadata'] = err.metadata
        error['trace'] = traceback.format_exc()
        return error
