from ..clients.metaApi.latencyListener import LatencyListener, ResponseTimestamps, SymbolPriceTimestamps, \
    UpdateTimestamps, TradeTimestamps
from .reservoir.statisticalReservoir import StatisticalReservoir
from .reservoir.reservoir import Reservoir
from typing import Dict


class LatencyMonitor(LatencyListener):
    """Responsible for monitoring MetaApi application latencies."""

    def __init__(self):
        """Inits latency monitor instance."""
        super().__init__()
        self._tradeReservoirs = {
            'clientLatency': self._initialize_reservoirs(),
            'serverLatency': self._initialize_reservoirs(),
            'brokerLatency': self._initialize_reservoirs()
        }
        self._updateReservoirs = {
            'clientLatency': self._initialize_reservoirs(),
            'serverLatency': self._initialize_reservoirs(),
            'brokerLatency': self._initialize_reservoirs()
        }
        self._priceReservoirs = {
            'clientLatency': self._initialize_reservoirs(),
            'serverLatency': self._initialize_reservoirs(),
            'brokerLatency': self._initialize_reservoirs()
        }
        self._requestReservoirs = {
            'branch': True
        }

    async def on_response(self, account_id: str, type: str, timestamps: ResponseTimestamps):
        """Invoked with latency information when application receives a response to RPC request.

        Args:
            account_id: Account id.
            type: Request type.
            timestamps: Request timestamps object containing latency information.

        Returns:
            A coroutine which resolves when latency information is processed."""
        if type not in self._requestReservoirs:
            self._requestReservoirs[type] = {
                'branch': True,
                'clientLatency': self._initialize_reservoirs(),
                'serverLatency': self._initialize_reservoirs()
            }
        if 'serverProcessingStarted' in timestamps and 'serverProcessingFinished' in timestamps:
            server_latency = timestamps['serverProcessingFinished'].timestamp() - \
                timestamps['serverProcessingStarted'].timestamp()
            self._save_measurement(self._requestReservoirs[type]['serverLatency'], server_latency)

        if 'clientProcessingStarted' in timestamps and 'clientProcessingFinished' in timestamps and \
                'serverProcessingStarted' in timestamps and 'serverProcessingFinished' in timestamps:
            server_latency = timestamps['serverProcessingFinished'].timestamp() - \
                timestamps['serverProcessingStarted'].timestamp()
            client_latency = timestamps['clientProcessingFinished'].timestamp() - \
                timestamps['clientProcessingStarted'].timestamp() - server_latency
            self._save_measurement(self._requestReservoirs[type]['clientLatency'], client_latency)

    @property
    def request_latencies(self) -> Dict:
        """Returns request processing latencies.

        Returns:
            Request processing latencies.
        """
        return self._construct_latencies_recursively(self._requestReservoirs)

    async def on_symbol_price(self, account_id: str, symbol: str, timestamps: SymbolPriceTimestamps):
        """Invoked with latency information when application receives symbol price update event.

        Args:
            account_id: Account id.
            symbol: Price symbol.
            timestamps: Timestamps object containing latency information about price streaming.

        Returns:
            A coroutine which resolves when latency information is processed.
        """
        if 'eventGenerated' in timestamps and 'serverProcessingStarted' in timestamps:
            broker_latency = timestamps['serverProcessingStarted'].timestamp() - \
                             timestamps['eventGenerated'].timestamp()
            self._save_measurement(self._priceReservoirs['brokerLatency'], broker_latency)
        if 'serverProcessingStarted' in timestamps and 'serverProcessingFinished' in timestamps:
            server_latency = timestamps['serverProcessingFinished'].timestamp() - \
                             timestamps['serverProcessingStarted'].timestamp()
            self._save_measurement(self._priceReservoirs['serverLatency'], server_latency)
        if 'serverProcessingFinished' in timestamps and 'clientProcessingFinished' in timestamps:
            client_latency = timestamps['clientProcessingFinished'].timestamp() - \
                             timestamps['serverProcessingFinished'].timestamp()
            self._save_measurement(self._priceReservoirs['clientLatency'], client_latency)

    @property
    def price_latencies(self) -> Dict:
        """Returns price streaming latencies.

        Returns:
            Price streaming latencies.
        """
        return self._construct_latencies_recursively(self._priceReservoirs)

    async def on_update(self, account_id: str, timestamps: UpdateTimestamps):
        """Invoked with latency information when application receives update event.

        Args:
            account_id: Account id.
            timestamps: Timestamps object containing latency information about update streaming.

        Returns:
            A coroutine which resolves when latency information is processed."""
        if 'eventGenerated' in timestamps and 'serverProcessingStarted' in timestamps:
            broker_latency = timestamps['serverProcessingStarted'].timestamp() - \
                             timestamps['eventGenerated'].timestamp()
            self._save_measurement(self._updateReservoirs['brokerLatency'], broker_latency)
        if 'serverProcessingStarted' in timestamps and 'serverProcessingFinished' in timestamps:
            server_latency = timestamps['serverProcessingFinished'].timestamp() - \
                             timestamps['serverProcessingStarted'].timestamp()
            self._save_measurement(self._updateReservoirs['serverLatency'], server_latency)
        if 'serverProcessingFinished' in timestamps and 'clientProcessingFinished' in timestamps:
            client_latency = timestamps['clientProcessingFinished'].timestamp() - \
                             timestamps['serverProcessingFinished'].timestamp()
            self._save_measurement(self._updateReservoirs['clientLatency'], client_latency)

    @property
    def update_latencies(self) -> Dict:
        """Returns update streaming latencies.

        Returns:
            Update streaming latencies.
        """
        return self._construct_latencies_recursively(self._updateReservoirs)

    async def on_trade(self, account_id: str, timestamps: TradeTimestamps):
        """Invoked with latency information when application receives trade response.

        Args:
            account_id: Account id.
            timestamps: Timestamps object containing latency information about a trade.

        Returns:
            A coroutine which resolves when latency information is processed."""
        if 'clientProcessingStarted' in timestamps and 'serverProcessingStarted' in timestamps:
            client_latency = timestamps['serverProcessingStarted'].timestamp() - \
                             timestamps['clientProcessingStarted'].timestamp()
            self._save_measurement(self._tradeReservoirs['clientLatency'], client_latency)
        if 'serverProcessingStarted' in timestamps and 'tradeStarted' in timestamps:
            server_latency = timestamps['tradeStarted'].timestamp() - \
                             timestamps['serverProcessingStarted'].timestamp()
            self._save_measurement(self._tradeReservoirs['serverLatency'], server_latency)
        if 'tradeStarted' in timestamps and 'tradeExecuted' in timestamps:
            broker_latency = timestamps['tradeExecuted'].timestamp() - \
                             timestamps['tradeStarted'].timestamp()
            self._save_measurement(self._tradeReservoirs['brokerLatency'], broker_latency)

    @property
    def trade_latencies(self) -> Dict:
        """Returns trade latencies.

        Returns:
            Trade latencies.
        """
        return self._construct_latencies_recursively(self._tradeReservoirs)

    def _save_measurement(self, reservoirs, client_latency: float):
        client_latency = int(client_latency * 1000)
        for key in reservoirs:
            e = reservoirs[key]
            if key == 'branch':
                continue
            e['percentiles'].push_measurement(client_latency)
            e['reservoir'].push_measurement(client_latency)

    def _construct_latencies_recursively(self, reservoirs):
        result = {}
        for key in reservoirs:
            e = reservoirs[key]
            if key == 'branch':
                continue
            result[key] = self._construct_latencies_recursively(e) if ('branch' in e and e['branch']) else {
                'p50': e['percentiles'].get_percentile(50),
                'p75': e['percentiles'].get_percentile(75),
                'p90': e['percentiles'].get_percentile(90),
                'p95': e['percentiles'].get_percentile(95),
                'p98': e['percentiles'].get_percentile(98),
                'avg': e['reservoir'].get_statistics()['average'],
                'count': e['reservoir'].get_statistics()['count'],
                'min': e['reservoir'].get_statistics()['min'],
                'max': e['reservoir'].get_statistics()['max']
            }
        return result

    def _initialize_reservoirs(self):
        return {
            'branch': True,
            '1h': {
                'percentiles': StatisticalReservoir(1000, 60 * 60 * 1000),
                'reservoir': Reservoir(60, 60 * 60 * 1000)
            },
            '1d': {
                'percentiles': StatisticalReservoir(1000, 24 * 60 * 60 * 1000),
                'reservoir': Reservoir(60, 24 * 60 * 60 * 1000)
            },
            '1w': {
                'percentiles': StatisticalReservoir(1000, 7 * 24 * 60 * 60 * 1000),
                'reservoir': Reservoir(60, 7 * 24 * 60 * 60 * 1000)
            },
        }
