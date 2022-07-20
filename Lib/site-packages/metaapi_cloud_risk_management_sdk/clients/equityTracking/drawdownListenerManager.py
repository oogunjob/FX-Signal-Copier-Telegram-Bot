from ..domain_client import DomainClient
from ...models import random_id
from .drawdownListener import DrawdownListener
import asyncio


class DrawdownListenerManager:
    """Drawdown event listener manager."""

    def __init__(self, domain_client: DomainClient):
        """Inits drawdown listener manager instance.

        Args:
            domain_client: Domain client.
        """
        self._domainClient = domain_client
        self._drawdownListeners = {}
        self._errorThrottleTime = 1

    @property
    def drawdown_listeners(self):
        """Returns the dictionary of drawdown listeners.

        Returns:
            Dictionary of drawdown listeners.
        """
        return self._drawdownListeners

    def add_drawdown_listener(self, listener: DrawdownListener, account_id: str = None, tracker_id: str = None,
                              sequence_number: int = None) -> str:
        """Adds a drawdown listener.

        Args:
            listener: Drawdown listener.
            account_id: Account id.
            tracker_id: Tracker id.
            sequence_number: Event sequence number.

        Returns:
            Drawdown listener id.
        """
        listener_id = random_id(10)
        self._drawdownListeners[listener_id] = listener
        asyncio.create_task(self._start_drawdown_event_job(listener_id, listener, account_id, tracker_id,
                                                           sequence_number))
        return listener_id

    def remove_drawdown_listener(self, listener_id: str):
        """Removes drawdown listener by id.

        Args:
            listener_id: Listener id.
        """
        if listener_id in self._drawdownListeners:
            del self._drawdownListeners[listener_id]

    async def _start_drawdown_event_job(self, listener_id: str, listener: DrawdownListener, account_id: str = None,
                                        tracker_id: str = None, sequence_number: int = None):
        throttle_time = self._errorThrottleTime
        while listener_id in self._drawdownListeners:
            opts = {
                'url': '/users/current/drawdown-events/stream',
                'method': 'GET',
                'qs': {
                    'previousSequenceNumber': sequence_number,
                    'accountId': account_id,
                    'trackerId': tracker_id,
                    'limit': 1000
                },
            }
            try:
                packets = await self._domainClient.request_api(opts, True)
                for packet in packets:
                    await listener.on_drawdown(packet)
                throttle_time = self._errorThrottleTime
                if listener_id in self._drawdownListeners and len(packets):
                    sequence_number = packets[-1]['sequenceNumber']
            except Exception as err:
                await asyncio.sleep(throttle_time)
                throttle_time = min(throttle_time * 2, 30)
