from .drawdownListenerManager import DrawdownListenerManager
from .drawdownListener import DrawdownListener
from typing import List, TypedDict, Optional, Literal
from ..domain_client import DomainClient
from urllib import parse


class DrawdownTrackerUpdate(TypedDict, total=False):
    """Drawdown tracker configuration update."""
    name: str
    """Drawdown tracker name."""


Period = Literal['day', 'date', 'week', 'week-to-date', 'month', 'month-to-date', 'quarter', 'quarter-to-date',
                 'year', 'year-to-date', 'lifetime']
"""Period length to track drawdown for."""


class NewDrawdownTracker(DrawdownTrackerUpdate, total=False):
    """New drawdown tracker configuration."""
    startBrokerTime: Optional[str]
    """Time to start tracking from in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    endBrokerTime: Optional[str]
    """Time to end tracking at in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    period: Period
    """Period length to track drawdown for."""
    relativeDrawdownThreshold: Optional[float]
    """Relative drawdown threshold after which drawdown event is generated, a fraction of 1."""
    absoluteDrawdownThreshold: Optional[float]
    """Absolute drawdown threshold after which drawdown event is generated, should be greater than 0."""


class DrawdownTrackerId(TypedDict):
    """Drawdown tracker id."""
    id: str
    """Drawdown tracker id."""


class DrawdownTracker(NewDrawdownTracker):
    """Drawdown tracker configuration."""
    _id: str
    """Unique drawdown tracker id."""


class DrawdownEvent(TypedDict, total=False):
    """Drawdown threshold exceeded event model."""
    sequenceNumber: int
    """Event unique sequence number."""
    accountId: str
    """MetaApi account id."""
    trackerId: str
    """Drawdown tracker id."""
    startBrokerTime: str
    """Drawdown tracking period start time in broker timezone, in YYYY-MM-DD HH:mm:ss.SSS format."""
    endBrokerTime: Optional[str]
    """Drawdown tracking period end time in broker timezone, in YYYY-MM-DD HH:mm:ss.SSS format."""
    period: Period
    """Drawdown tracking period."""
    brokerTime: str
    """Drawdown threshold exceeded event time in broker timezone, in YYY-MM-DD HH:mm:ss.SSS format."""
    absoluteDrawdown: float
    """Absolute drawdown value which was observed when the drawdown threshold was exceeded."""
    relativeDrawdown: float
    """Relative drawdown value which was observed when the drawdown threshold was exceeded."""


class DrawdownPeriodStatistics(TypedDict, total=False):
    """Drawdown period statistics."""
    startBrokerTime: str
    """Period start time in broker timezone, in YYYY-MM-DD HH:mm:ss format."""
    endBrokerTime: Optional[str]
    """Period end time in broker timezone, in YYYY-MM-DD HH:mm:ss format."""
    period: Period
    """Period length."""
    initialBalance: float
    """Balance at period start time."""
    maxDrawdownTime: Optional[str]
    """Time max drawdown was observed at in broker timezone, in YYYY-MM-DD HH:mm:ss format"""
    maxAbsoluteDrawdown: Optional[float]
    """The value of maximum absolute drawdown observed."""
    maxRelativeDrawdown: Optional[float]
    """The value of maximum relative drawdown observed."""
    thresholdExceeded: bool
    """The flag indicating that max allowed total drawdown was exceeded."""


class EquityChartItem(TypedDict):
    """Equity chart item."""
    startBrokerTime: str
    """Start time of a chart item as per broker timezone, in YYYY-MM-DD HH:mm:ss format."""
    endBrokerTime: str
    """End time of a chart item as per broker timezone, in YYYY-MM-DD HH:mm:ss format."""
    averageBalance: float
    """Average balance value during the period."""
    minBalance: float
    """Minimum balance value during the period."""
    maxBalance: float
    """Maximum balance value during the period."""
    averageEquity: float
    """Average equity value during the period."""
    minEquity: float
    """Minimum equity value during the period."""
    maxEquity: float
    """Maximum equity value during the period."""


class EquityTrackingClient:
    """metaapi.cloud RiskManagement equity tracking API client (see https://metaapi.cloud/docs/riskManagement/)"""

    def __init__(self, domain_client: DomainClient):
        """Inits RiskManagement equity tracking API client instance.

        Args:
            domain_client: Domain client.
        """
        self._domainClient = domain_client
        self._drawdownListenerManager = DrawdownListenerManager(domain_client)

    async def create_drawdown_tracker(self, account_id: str, tracker: NewDrawdownTracker) -> 'DrawdownTrackerId':
        """Returns list of transactions on the strategies the current user provides to other users. See
        https://metaapi.cloud/docs/copyfactory/restApi/api/history/getProvidedTransactions/

        Args:
            account_id: Id of the MetaApi account.
            tracker: Drawdown tracker.

        Returns:
            A coroutine resolving with transactions found.
        """
        return await self._domainClient.request_api({
          'url': f'/users/current/accounts/{account_id}/drawdown-trackers',
          'method': 'POST',
          'body': tracker
        })

    async def get_drawdown_trackers(self, account_id: str) -> 'List[DrawdownTracker]':
        """Returns drawdown trackers defined for an account.

        Args:
            account_id: Id of the MetaApi account.

        Returns:
            A coroutine resolving with drawdown trackers.
        """
        return await self._domainClient.request_api({
            'url': f'/users/current/accounts/{account_id}/drawdown-trackers',
            'method': 'GET',
        })

    async def get_drawdown_tracker_by_name(self, account_id: str, name: str) -> DrawdownTracker:
        """Returns drawdown tracker by account and name.

        Args:
            account_id: Id of the MetaApi account.
            name: Tracker name.

        Returns:
            A coroutine resolving with drawdown tracker found.
        """
        return await self._domainClient.request_api({
            'url': f'/users/current/accounts/{account_id}/drawdown-trackers/name/{parse.quote(name)}',
            'method': 'GET',
        })

    async def update_drawdown_tracker(self, account_id: str, id: str, update: DrawdownTrackerUpdate):
        """Updates drawdown tracker.

        Args:
            account_id: Id of the MetaApi account.
            id: Id of the drawdown tracker.
            update: Drawdown tracker update.

        Returns:
            A coroutine resolving when drawdown tracker updated.
        """
        return await self._domainClient.request_api({
            'url': f'/users/current/accounts/{account_id}/drawdown-trackers/{id}',
            'method': 'PUT',
            'body': update
        })

    async def delete_drawdown_tracker(self, account_id: str, id: str):
        """Removes drawdown tracker.

        Args:
            account_id: Id of the MetaApi account.
            id: Id of the drawdown tracker.

        Returns:
            A coroutine resolving when drawdown tracker is removed.
        """
        return await self._domainClient.request_api({
            'url': f'/users/current/accounts/{account_id}/drawdown-trackers/{id}',
            'method': 'DELETE'
        })

    async def get_drawdown_events(self, start_broker_time: str = None, end_broker_time: str = None,
                                  account_id: str = None, tracker_id: str = None, limit: int = None) \
            -> 'List[DrawdownEvent]':
        """Returns drawdown events by broker time range.

        Args:
            start_broker_time: Value of the event time in broker timezone to start loading data from, inclusive,
            in 'YYYY-MM-DD HH:mm:ss.SSS format.
            end_broker_time: Value of the event time in broker timezone to end loading data at, inclusive,
            in 'YYYY-MM-DD HH:mm:ss.SSS format.
            account_id: Id of the MetaApi account.
            tracker_id: Id of the drawdown tracker.
            limit: Pagination limit, default is 1000.

        Returns:
            A coroutine resolving with drawdown events.
        """
        qs = {}
        if start_broker_time is not None:
            qs['startBrokerTime'] = start_broker_time
        if end_broker_time is not None:
            qs['endBrokerTime'] = end_broker_time
        if account_id is not None:
            qs['accountId'] = account_id
        if tracker_id is not None:
            qs['trackerId'] = tracker_id
        if limit is not None:
            qs['limit'] = limit
        return await self._domainClient.request_api({
            'url': '/users/current/drawdown-events/by-broker-time',
            'method': 'GET',
            'params': qs
        })

    def add_drawdown_listener(self, listener: DrawdownListener, account_id: str = None, tracker_id: str = None,
                              sequence_number: int = None) -> str:
        """Adds a drawdown listener and creates a job to make requests.

        Args:
            listener: Drawdown listener.
            account_id: Account id.
            tracker_id: Tracker id.
            sequence_number: Sequence number.

        Returns:
            Listener id.
        """
        return self._drawdownListenerManager.add_drawdown_listener(listener, account_id, tracker_id, sequence_number)

    def remove_drawdown_listener(self, listener_id: str):
        """Removes drawdown listener and cancels the event stream

        Args:
            listener_id: Drawdown listener id.
        """
        self._drawdownListenerManager.remove_drawdown_listener(listener_id)

    async def get_drawdown_statistics(self, account_id: str, tracker_id: str, start_time: str = None,
                                      limit: int = None) -> 'List[DrawdownPeriodStatistics]':
        """Returns account drawdown tracking stats by drawdown tracker id.

        Args:
            account_id: Id of MetaAPI account.
            tracker_id: Id of drawdown tracker.
            start_time: Time to start loading stats from, default is current time. Note that stats is loaded in
            backwards direction.
            limit: Number of records to load, default is 1.

        Returns:
            A coroutine resolving with drawdown statistics.
        """
        qs = {}
        if start_time is not None:
            qs['startTime'] = start_time
        if limit is not None:
            qs['limit'] = limit
        return await self._domainClient.request_api({
            'url': f'/users/current/accounts/{account_id}/drawdown-trackers/{tracker_id}/statistics',
            'method': 'GET',
            'params': qs
        })

    async def get_equity_chart(self, account_id: str, start_time: str = None, end_time: str = None) \
            -> 'List[EquityChartItem]':
        """Returns equity chart by account id.

        Args:
            account_id: MetaApi account id.
            start_time: Starting broker time in YYYY-MM-DD HH:mm:ss format.
            end_time: Ending broker time in YYYY-MM-DD HH:mm:ss format.

        Returns:
            A coroutine resolving with equity chart.
        """
        qs = {}
        if start_time is not None:
            qs['startTime'] = start_time
        if end_time is not None:
            qs['endTime'] = end_time
        return await self._domainClient.request_api({
            'url': f'/users/current/accounts/{account_id}/equity-chart',
            'method': 'GET',
            'params': qs
        })
