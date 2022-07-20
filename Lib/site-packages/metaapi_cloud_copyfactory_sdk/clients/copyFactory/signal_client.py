from ..domain_client import DomainClient
from .copyFactory_models import CopyFactoryExternalSignalUpdate, CopyFactoryExternalSignalRemove, \
    CopyFactoryTradingSignal
from typing import List
from copy import deepcopy
from ...models import convert_iso_time_to_date, format_request, random_id


class SignalClient:
    """CopyFactory client for signal requests."""

    def __init__(self, account_id: str, host: dict, domain_client: DomainClient):
        """Inits CopyFactory signal client instance.

        Args:
            account_id: Account id.
            host: Host data.
            domain_client: Domain client.
        """
        self._accountId = account_id
        self._domainClient = domain_client
        self._host = host

    @staticmethod
    def generate_signal_id():
        """Generates random signal id.

        Returns:
            Signal id.
        """
        return random_id(8)

    async def get_trading_signals(self) -> 'List[CopyFactoryTradingSignal]':
        """Returns trading signals the subscriber is subscribed to. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/trading/getTradingSignals/

        Returns:
            A coroutine which resolves with signals found.
        """
        opts = {
            'url': f'/users/current/subscribers/{self._accountId}/signals',
            'method': 'GET',
            'headers': {
                'auth-token': self._domainClient.token
            }
        }
        result = await self._domainClient.request_signal(opts, self._host, self._accountId)
        convert_iso_time_to_date(result)
        return result

    async def update_external_signal(self, strategy_id: str, signal_id: str, signal: CopyFactoryExternalSignalUpdate):
        """Updates external signal for a strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/trading/updateExternalSignal/

        Args:
            strategy_id: Strategy id.
            signal_id: External signal id (should be 8 alphanumerical symbols)
            signal: Signal update payload.

        Returns:
            A coroutine which resolves when external signal is updated.
        """
        payload: dict = deepcopy(signal)
        format_request(payload)
        opts = {
            'url': f"/users/current/strategies/{strategy_id}/external-signals/{signal_id}",
            'method': 'PUT',
            'headers': {
                'auth-token': self._domainClient.token
            },
            'body': payload
        }
        return await self._domainClient.request_signal(opts, self._host, self._accountId)

    async def remove_external_signal(self, strategy_id: str, signal_id: str, signal: CopyFactoryExternalSignalRemove):
        """Removes (closes) external signal for a strategy. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/trading/removeExternalSignal/

        Args:
            strategy_id: Strategy id.
            signal_id: External signal id
            signal: Signal removal payload.

        Returns:
            A coroutine which resolves when external signal is removed.
        """
        payload: dict = deepcopy(signal)
        format_request(payload)
        opts = {
            'url': f"/users/current/strategies/{strategy_id}/external-signals/{signal_id}/remove",
            'method': 'POST',
            'headers': {
                'auth-token': self._domainClient.token
            },
            'body': payload
        }
        return await self._domainClient.request_signal(opts, self._host, self._accountId)
