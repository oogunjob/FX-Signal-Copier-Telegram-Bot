from ..clients.metaApi.synchronizationListener import SynchronizationListener, HealthStatus
from .reservoir.reservoir import Reservoir
from .models import MetatraderSymbolPrice, date, string_format_error
from typing_extensions import TypedDict
import asyncio
from datetime import datetime
import functools
from random import uniform
from ..logger import LoggerManager


class ConnectionHealthStatus(TypedDict):
    """Connection health status."""
    connected: bool
    """Flag indicating successful connection to API server."""
    connectedToBroker: bool
    """Flag indicating successful connection to broker."""
    quoteStreamingHealthy: bool
    """Flag indicating that quotes are being streamed successfully from the broker."""
    synchronized: bool
    """Flag indicating a successful synchronization."""
    healthy: bool
    """Flag indicating overall connection health status."""
    message: str
    """Health status message."""


class ConnectionHealthMonitor(SynchronizationListener):
    """Tracks connection health status."""

    def __init__(self, connection):
        """Inits the monitor.

        Args:
            connection: MetaApi connection instance.
        """
        super().__init__()
        self._connection = connection
        self._priceUpdatedAt = None

        async def update_quote_health_job():
            while True:
                await asyncio.sleep(uniform(1, 60))
                self._update_quote_health_status()

        async def measure_uptime_job():
            while True:
                await asyncio.sleep(uniform(1, 60))
                self._measure_uptime()

        self._quotesHealthy = False
        self._offset = 0
        self._minQuoteInterval = 60
        self._updateQuoteHealthStatusInterval = asyncio.create_task(update_quote_health_job())
        self._measureUptimeInterval = asyncio.create_task(measure_uptime_job())
        self._serverHealthStatus = {}
        self._uptimeReservoirs = {
            '5m': Reservoir(300, 5 * 60 * 1000),
            '1h': Reservoir(600, 60 * 60 * 1000),
            '1d': Reservoir(24 * 60, 24 * 60 * 60 * 1000),
            '1w': Reservoir(24 * 7, 7 * 24 * 60 * 60 * 1000),
        }
        self._logger = LoggerManager.get_logger('ConnectionHealthMonitor')

    def stop(self):
        """Stops health monitor."""
        self._logger.debug(f'{self._connection.account.id}: Stopping the monitor')
        self._updateQuoteHealthStatusInterval.cancel()
        self._measureUptimeInterval.cancel()

    async def on_symbol_price_updated(self, instance_index: str, price: MetatraderSymbolPrice):
        """Invoked when a symbol price was updated.

        Args:
            instance_index: Index of an account instance connected.
            price: Updated MetaTrader symbol price.
        """
        try:
            broker_timestamp = date(price['brokerTime']).timestamp()
            self._priceUpdatedAt = datetime.now()
            self._offset = self._priceUpdatedAt.timestamp() - broker_timestamp

        except Exception as err:
            self._logger.error(f'{self._connection.account.id}: Failed to update quote streaming health '
                               f'status on price update ' + string_format_error(err))

    async def on_health_status(self, instance_index: str, status: HealthStatus):
        """Invoked when a server-side application health status is received from MetaApi.

        Args:
            instance_index: Index of an account instance connected.
            status: Server-side application health status.

        Returns:
            A coroutine which resolves when the asynchronous event is processed.
        """
        self._serverHealthStatus[str(instance_index)] = status

    async def on_disconnected(self, instance_index: str):
        """Invoked when connection to MetaTrader terminal terminated.

        Args:
            instance_index: Index of an account instance connected.

        Returns:
             A coroutine which resolves when the asynchronous event is processed.
        """
        if str(instance_index) in self._serverHealthStatus:
            del self._serverHealthStatus[str(instance_index)]

    @property
    def server_health_status(self) -> HealthStatus:
        """Returns server-side application health status.

        Returns:
            Server-side application health status.
        """
        result = None
        for s in self._serverHealthStatus:
            if not result:
                result = s
            else:
                for field in list(s.keys()):
                    result[field] = result[field] if field in result else s[field]
        return result or {}

    @property
    def health_status(self) -> ConnectionHealthStatus:
        """Returns health status.

        Returns:
            Connection health status.
        """
        status = {
            'connected': self._connection.terminal_state.connected,
            'connectedToBroker': self._connection.terminal_state.connected_to_broker,
            'quoteStreamingHealthy': self._quotesHealthy,
            'synchronized': self._connection.synchronized
        }
        status['healthy'] = status['connected'] and status['connectedToBroker'] and \
            status['quoteStreamingHealthy'] and status['synchronized']
        if status['healthy']:
            message = 'Connection to broker is stable. No health issues detected.'
        else:
            message = 'Connection is not healthy because '
            reasons = []
            if not status['connected']:
                reasons.append('connection to API server is not established or lost')
            if not status['connectedToBroker']:
                reasons.append('connection to broker is not established or lost')
            if not status['synchronized']:
                reasons.append('local terminal state is not synchronized to broker')
            if not status['quoteStreamingHealthy']:
                reasons.append('quotes are not streamed from the broker properly')
            message = message + functools.reduce(lambda a, b: a + ' and ' + b, reasons) + '.'
        status['message'] = message
        return status

    @property
    def uptime(self) -> dict:
        """Returns uptime in percents measured over specific periods of time.

        Returns:
            Uptime in percents measured over specific periods of time.
        """
        uptime = {}
        for key in self._uptimeReservoirs:
            e: Reservoir = self._uptimeReservoirs[key]
            uptime[key] = e.get_statistics()['average']
        return uptime

    def _measure_uptime(self):
        try:
            for key in self._uptimeReservoirs:
                r = self._uptimeReservoirs[key]
                r.push_measurement(100 if (
                    self._connection.terminal_state.connected and self._connection.terminal_state.connected_to_broker
                    and self._connection.synchronized and self._quotesHealthy) else 0)
        except Exception as err:
            self._logger.error(f'failed to measure uptime for account {self._connection.account.id} '
                               f'{string_format_error(err)}')

    def _update_quote_health_status(self):
        try:
            server_date_time = datetime.fromtimestamp(datetime.now().timestamp() - self._offset)
            server_time = server_date_time.strftime('%H:%M:%S.%f')
            day_of_week = server_date_time.isoweekday()
            days_of_week = {
                '1': 'MONDAY',
                '2': 'TUESDAY',
                '3': 'WEDNESDAY',
                '4': 'THURSDAY',
                '5': 'FRIDAY',
                '6': 'SATURDAY',
                '7': 'SUNDAY'
            }
            in_quote_session = False
            if not self._priceUpdatedAt:
                self._priceUpdatedAt = datetime.now()
            if (not self._connection.subscribed_symbols) or (not len(self._connection.subscribed_symbols)):
                self._priceUpdatedAt = datetime.now()
            for symbol in self._connection.subscribed_symbols:
                specification = self._connection.terminal_state.specification(symbol) or {}
                quote_sessions_list = (specification['quoteSessions'] if 'quoteSessions' in specification else [])
                quote_sessions = quote_sessions_list[days_of_week[str(day_of_week)]] if \
                    days_of_week[str(day_of_week)] in quote_sessions_list else []
                for session in quote_sessions:
                    if session['from'] <= server_time <= session['to']:
                        in_quote_session = True
            self._quotesHealthy = (not len(self._connection.subscribed_symbols)) or (not in_quote_session) or \
                                  ((datetime.now().timestamp() - self._priceUpdatedAt.timestamp()) <
                                   self._minQuoteInterval)
        except Exception as err:
            self._logger.error(f'failed to update quote streaming health status for account '
                               f'{self._connection.account.id} {string_format_error(err)}')
