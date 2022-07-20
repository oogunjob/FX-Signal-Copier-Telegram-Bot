from ..metaApi_client import MetaApiClient
from ..domain_client import DomainClient
from ...models import random_id
from .stopout_listener import StopoutListener
import asyncio


class StopoutListenerManager(MetaApiClient):
    """Stopout event listener manager."""

    def __init__(self, domain_client: DomainClient):
        """Inits stopout listener manager instance.

        Args:
            domain_client: Domain client.
        """
        super().__init__(domain_client)
        self._domainClient = domain_client
        self._stopoutListeners = {}
        self._errorThrottleTime = 1

    @property
    def stopout_listeners(self):
        """Returns the dictionary of stopout listeners.

        Returns:
            Dictionary of stopout listeners.
        """
        return self._stopoutListeners

    def add_stopout_listener(self, listener: StopoutListener, account_id: str = None, strategy_id: str = None,
                             sequence_number: int = None) -> str:
        """Adds a stopout listener.

        Args:
            listener: Stopout listener.
            account_id:  Account id.
            strategy_id: Strategy id.
            sequence_number: Event sequence number.

        Returns:
            Stopout listener id.
        """
        listener_id = random_id(10)
        self._stopoutListeners[listener_id] = listener
        asyncio.create_task(self._start_stopout_event_job(listener_id, listener, account_id, strategy_id,
                                                          sequence_number))
        return listener_id

    def remove_stopout_listener(self, listener_id: str):
        """Removes stopout listener by id.

        Args:
            listener_id: listener id.
        """
        if listener_id in self._stopoutListeners:
            del self._stopoutListeners[listener_id]

    async def _start_stopout_event_job(self, listener_id: str, listener: StopoutListener, account_id: str = None,
                                       strategy_id: str = None, sequence_number: int = None):
        throttle_time = self._errorThrottleTime
        while listener_id in self._stopoutListeners:
            opts = {
                'url': '/users/current/stopouts/stream',
                'method': 'GET',
                'qs': {
                    'previousSequenceNumber': sequence_number,
                    'subscriberId': account_id,
                    'strategyId': strategy_id,
                    'limit': 1000
                },
                'headers': {
                    'auth-token': self._token
                },
            }
            try:
                packets = await self._domainClient.request_copyfactory(opts, True)
                await listener.on_stopout(packets)
                throttle_time = self._errorThrottleTime
                if listener_id in self._stopoutListeners and len(packets):
                    sequence_number = packets[-1]['sequenceNumber']
            except Exception as err:
                await asyncio.sleep(throttle_time)
                throttle_time = min(throttle_time * 2, 30)
