from datetime import datetime
from typing_extensions import TypedDict
from typing import List, Optional
import iso8601
import random
import string
import pytz
import re
import traceback
import json
import asyncio


def date(date_time: str or float or int) -> datetime:
    """Parses a date string into a datetime object."""
    if isinstance(date_time, float) or isinstance(date_time, int):
        return datetime.fromtimestamp(max(date_time, 100000)).astimezone(pytz.utc)
    else:
        return iso8601.parse_date(date_time)


def format_date(date: datetime) -> str:
    """Converts date to format compatible with JS"""
    return date.astimezone(pytz.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def random_id(length: int = 32) -> str:
    """Generates a random id of 32 symbols."""
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def convert_iso_time_to_date(packet):
    for field in packet:
        value = packet[field]
        if isinstance(value, str) and re.search('time|Time', field) and not \
                re.search('brokerTime|BrokerTime', field):
            packet[field] = date(value)
        if isinstance(value, list):
            for item in value:
                convert_iso_time_to_date(item)
        if isinstance(value, dict):
            convert_iso_time_to_date(value)
    if packet and 'timestamps' in packet:
        for field in packet['timestamps']:
            packet['timestamps'][field] = date(packet['timestamps'][field])
    if packet and 'type' in packet and packet['type'] == 'prices':
        if 'prices' in packet:
            for price in packet['prices']:
                if 'timestamps' in price:
                    for field in price['timestamps']:
                        if isinstance(price['timestamps'][field], str):
                            price['timestamps'][field] = date(price['timestamps'][field])


def format_error(err: Exception or any):
    """Formats and outputs metaApi errors with additional information.

    Args:
        err: Exception to process.
    """
    error = {'name': err.__class__.__name__, 'message': err if isinstance(err, str) or err is None else (
        err.args[0] if len(err.args) else None)}
    if hasattr(err, 'status_code'):
        error['status_code'] = err.status_code
    if err.__class__.__name__ == 'ValidationException':
        error['details'] = err.details
    if err.__class__.__name__ == 'TradeException':
        error['string_code'] = err.stringCode
    if err.__class__.__name__ == 'TooManyRequestsException':
        error['metadata'] = err.metadata
    error['trace'] = traceback.format_exc()
    return error


def string_format_error(err: Exception or any):
    """Outputs error information in string format.

    Args:
        err: Exception to process.

    Return:
        Error information in string format.
    """
    return json.dumps(format_error(err))


async def promise_any(coroutines):
    exception_task = None
    while len(coroutines):
        done, coroutines = await asyncio.wait(coroutines, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if not exception_task and task.exception():
                exception_task = task
            else:
                for wait_task in coroutines:
                    wait_task.cancel()
                return task.result()

    return exception_task.result()


class G1Encoder(json.JSONEncoder):
    """A JSON encoder used to encode cloud-g1 account terminal data."""
    def iterencode(self, obj, _one_shot=False):
        if isinstance(obj, datetime):
            yield '"' + format_date(obj) + '"'
        elif isinstance(obj, bool):
            if obj:
                yield 'true'
            else:
                yield 'false'
        elif isinstance(obj, float):
            yield format(obj, '.8f')
        elif isinstance(obj, dict):
            last_index = len(obj) - 1
            yield '{'
            i = 0
            for key, value in obj.items():
                yield '"' + key + '":'
                for chunk in G1Encoder.iterencode(self, value):
                    yield chunk
                if i != last_index:
                    yield ","
                i += 1
            yield '}'
        elif isinstance(obj, list):
            last_index = len(obj) - 1
            yield "["
            for i, o in enumerate(obj):
                for chunk in G1Encoder.iterencode(self, o):
                    yield chunk
                if i != last_index:
                    yield ","
            yield "]"
        elif isinstance(obj, str):
            yield '"' + obj.replace('\\', '\\\\').replace('/', '\\/') + '"'
        else:
            for chunk in json.JSONEncoder.iterencode(self, obj):
                yield chunk


class G2Encoder(json.JSONEncoder):
    """A JSON encoder used to encode cloud-g2 account terminal data."""
    def iterencode(self, obj, _one_shot=False):
        if isinstance(obj, datetime):
            yield '"' + format_date(obj) + '"'
        elif isinstance(obj, bool):
            if obj:
                yield 'true'
            else:
                yield 'false'
        elif isinstance(obj, float):
            result = format(obj, '.8f')
            while result[-1] in ['0', '.']:
                result = result[:-1]
            yield result
        elif isinstance(obj, dict):
            last_index = len(obj) - 1
            yield '{'
            i = 0
            for key, value in obj.items():
                yield '"' + key + '":'
                for chunk in G2Encoder.iterencode(self, value):
                    yield chunk
                if i != last_index:
                    yield ","
                i += 1
            yield '}'
        elif isinstance(obj, list):
            last_index = len(obj) - 1
            yield "["
            for i, o in enumerate(obj):
                for chunk in G2Encoder.iterencode(self, o):
                    yield chunk
                if i != last_index:
                    yield ","
            yield "]"
        else:
            for chunk in json.JSONEncoder.iterencode(self, obj):
                yield chunk


class MetatraderAccountInformation(TypedDict, total=False):
    """MetaTrader account information (see https://metaapi.cloud/docs/client/models/metatraderAccountInformation/)"""

    platform: str
    """Platform id (mt4 or mt5)"""
    broker: str
    """Broker name."""
    currency: str
    """Account base currency ISO code."""
    server: str
    """Broker server name."""
    balance: float
    """Account balance."""
    equity: float
    """Account liquidation value."""
    margin: float
    """Used margin."""
    freeMargin: float
    """Free margin."""
    leverage: float
    """Account leverage coefficient."""
    marginLevel: float
    """Margin level calculated as % of equity/margin."""
    tradeAllowed: bool
    """Flag indicating that trading is allowed."""
    investorMode: Optional[bool]
    """Flag indicating that investor password was used (supported for g2 only)."""
    marginMode: str
    """Margin calculation mode, one of ACCOUNT_MARGIN_MODE_EXCHANGE, ACCOUNT_MARGIN_MODE_RETAIL_NETTING,
    ACCOUNT_MARGIN_MODE_RETAIL_HEDGING."""
    name: str
    """Account owner name."""
    login: int
    """Account login."""
    credit: float
    """Account credit in the deposit currency."""


class StopLossThreshold(TypedDict):
    """Stop loss threshold."""

    threshold: float
    """Price threshold relative to position open price, interpreted according to units field value."""
    stopLoss: float
    """Stop loss value, interpreted according to units and basePrice field values."""


class ThresholdTrailingStopLoss(TypedDict, total=False):
    """Threshold trailing stop loss configuration."""

    thresholds: List[StopLossThreshold]
    """Stop loss thresholds."""
    units: Optional[str]
    """Threshold stop loss units. ABSOLUTE_PRICE means the that the value of stop loss threshold fields contain a
    final threshold & stop loss value. RELATIVE* means that the threshold fields value contains relative threshold &
    stop loss values, expressed either in price, points, pips, account currency or balance percentage. Default is
    ABSOLUTE_PRICE. One of ABSOLUTE_PRICE, RELATIVE_PRICE, RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY,
    RELATIVE_BALANCE_PERCENTAGE."""
    stopPriceBase: Optional[str]
    """Defines the base price to calculate SL relative to for POSITION_MODIFY and pending order requests. Default is
    OPEN_PRICE. One of CURRENT_PRICE, OPEN_PRICE."""


class DistanceTrailingStopLoss(TypedDict, total=False):
    """Distance trailing stop loss configuration."""

    distance: Optional[float]
    """SL distance relative to current price, interpreted according to units field value."""
    units: Optional[str]
    """Distance trailing stop loss units. RELATIVE_* means that the distance field value contains relative stop loss
    expressed either in price, points, pips, account currency or balance percentage. Default is RELATIVE_PRICE. One of
    RELATIVE_PRICE, RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY, RELATIVE_BALANCE_PERCENTAGE"""


class TrailingStopLoss(TypedDict, total=False):
    """Distance trailing stop loss configuration."""

    distance: Optional[DistanceTrailingStopLoss]
    """Distance trailing stop loss configuration. If both distance and threshold TSL are set, then the resulting SL
    will be the one which is closest to the current price."""
    threshold: Optional[ThresholdTrailingStopLoss]
    """Threshold trailing stop loss configuration. If both distance and threshold TSL are set, then the resulting SL
    will be the one which is closest to the current price."""


class MetatraderPosition(TypedDict, total=False):
    """MetaTrader position"""

    id: int
    """Position id (ticket number)."""
    type: str
    """Position type (one of POSITION_TYPE_BUY, POSITION_TYPE_SELL)."""
    symbol: str
    """Position symbol."""
    magic: int
    """Position magic number, identifies the EA which opened the position."""
    time: datetime
    """Time position was opened at."""
    brokerTime: str
    """Time position was opened at, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    updateTime: datetime
    """Last position modification time."""
    openPrice: float
    """Position open price."""
    currentPrice: float
    """Current price."""
    currentTickValue: float
    """Current tick value."""
    stopLoss: Optional[float]
    """Optional position stop loss price."""
    takeProfit: Optional[float]
    """Optional position take profit price."""
    trailingStopLoss: Optional[TrailingStopLoss]
    """Distance trailing stop loss configuration."""
    volume: float
    """Position volume."""
    profit: float
    """Position cumulative profit, including unrealized profit resulting from currently open position part (except
    swap and commissions) and realized profit resulting from partially closed position part and including swap and
    commissions."""
    realizedProfit: float
    """Profit of the already closed part, including commissions and swap (realized and unrealized)."""
    unrealizedProfit: float
    """Profit of the part of the position which is not yet closed, excluding swap and commissions."""
    swap: float
    """Position cumulative swap, including both swap from currently open position part (unrealized
    swap) and swap from partially closed position part (realized swap)."""
    realizedSwap: float
    """Swap from partially closed position part."""
    unrealizedSwap: float
    """Swap resulting from currently open position part."""
    commission: float
    """Total position commissions, resulting both from currently open and closed position parts."""
    realizedCommission: float
    """Position realized commission, resulting from partially closed position part."""
    unrealizedCommission: float
    """Position unrealized commission, resulting from currently open position part."""
    comment: Optional[str]
    """Optional position comment. The sum of the line lengths of the comment and the clientId
    must be less than or equal to 26. For more information see https://metaapi.cloud/docs/client/clientIdUsage/"""
    clientId: Optional[str]
    """Optional client-assigned id. The id value can be assigned when submitting a trade and
    will be present on position, history orders and history deals related to the trade. You can use this field to bind
    your trades to objects in your application and then track trade progress. The sum of the line lengths of the
    comment and the clientId must be less than or equal to 26. For more information see
    https://metaapi.cloud/docs/client/clientIdUsage/"""
    reason: str
    """Position opening reason. One of POSITION_REASON_CLIENT, POSITION_REASON_EXPERT, POSITION_REASON_MOBILE,
    POSITION_REASON_WEB, POSITION_REASON_UNKNOWN. See
    https://www.mql5.com/en/docs/constants/tradingconstants/positionproperties#enum_position_reason"""
    accountCurrencyExchangeRate: Optional[float]
    """Current exchange rate of account currency into account base currency (USD if you did not override it)."""
    brokerComment: Optional[str]
    """Current comment value on broker side (possibly overriden by the broker)."""


class MetatraderOrder(TypedDict, total=False):
    """MetaTrader order"""

    id: int
    """Order id (ticket number)."""
    type: str
    """Order type (one of ORDER_TYPE_SELL, ORDER_TYPE_BUY, ORDER_TYPE_BUY_LIMIT,
    ORDER_TYPE_SELL_LIMIT, ORDER_TYPE_BUY_STOP, ORDER_TYPE_SELL_STOP). See
    https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type"""
    state: str
    """Order state one of (ORDER_STATE_STARTED, ORDER_STATE_PLACED, ORDER_STATE_CANCELED,
    ORDER_STATE_PARTIAL, ORDER_STATE_FILLED, ORDER_STATE_REJECTED, ORDER_STATE_EXPIRED, ORDER_STATE_REQUEST_ADD,
    ORDER_STATE_REQUEST_MODIFY, ORDER_STATE_REQUEST_CANCEL). See
    https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_state"""
    magic: int
    """Order magic number, identifies the EA which created the order."""
    time: datetime
    """Time order was created at."""
    brokerTime: str
    """Time position was opened at, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    doneTime: Optional[datetime]
    """Optional time order was executed or canceled at. Will be specified for completed orders only."""
    doneBrokerTime: Optional[str]
    """Time order was executed or canceled at, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format. Will be specified
    for completed orders only"""
    symbol: str
    """Order symbol."""
    openPrice: float
    """Order open price (market price for market orders, limit price for limit orders or stop price for stop orders)."""
    stopLimitPrice: Optional[float]
    """The limit order price for the StopLimit order."""
    currentPrice: Optional[float]
    """Current price, filled for pending orders only. Not filled for history orders."""
    stopLoss: Optional[float]
    """Optional order stop loss price."""
    takeProfit: Optional[float]
    """Optional order take profit price."""
    trailingStopLoss: Optional[TrailingStopLoss]
    """Distance trailing stop loss configuration."""
    volume: float
    """Order requested quantity."""
    currentVolume: float
    """Order remaining quantity, i.e. requested quantity - filled quantity."""
    positionId: str
    """Order position id. Present only if the order has a position attached to it."""
    comment: Optional[str]
    """Optional order comment. The sum of the line lengths of the comment and the clientId
    must be less than or equal to 26. For more information see https://metaapi.cloud/docs/client/clientIdUsage/"""
    brokerComment: Optional[str]
    """Current comment value on broker side (possibly overriden by the broker)."""
    clientId: Optional[str]
    """Optional client-assigned id. The id value can be assigned when submitting a trade and
    will be present on position, history orders and history deals related to the trade. You can use this field to bind
    your trades to objects in your application and then track trade progress. The sum of the line lengths of the
    comment and the clientId must be less than or equal to 26. For more information see
    https://metaapi.cloud/docs/client/clientIdUsage/"""
    platform: str
    """Platform id (mt4 or mt5)."""
    reason: str
    """Order opening reason. One of ORDER_REASON_CLIENT, ORDER_REASON_MOBILE, ORDER_REASON_WEB,
    ORDER_REASON_EXPERT, ORDER_REASON_SL, ORDER_REASON_TP, ORDER_REASON_SO, ORDER_REASON_UNKNOWN. See
    https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_reason."""
    fillingMode: str
    """Order filling mode. One of ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN. See
    https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type_filling."""
    expirationType: str
    """Order expiration type. One of ORDER_TIME_GTC, ORDER_TIME_DAY, ORDER_TIME_SPECIFIED, ORDER_TIME_SPECIFIED_DAY.
    See https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type_time"""
    expirationTime: datetime
    """Optional order expiration time."""
    accountCurrencyExchangeRate: Optional[float]
    """Current exchange rate of account currency into account base currency (USD if you did not override it)."""
    closeByPositionId: Optional[str]
    """Identifier of an opposite position used for closing by order ORDER_TYPE_CLOSE_BY"""


class MetatraderHistoryOrders(TypedDict):
    """MetaTrader history orders search query response."""

    historyOrders: List[MetatraderOrder]
    """Array of history orders returned."""
    synchronizing: bool
    """Flag indicating that history order initial synchronization is still in progress
    and thus search results may be incomplete"""


class MetatraderDeal(TypedDict, total=False):
    """MetaTrader deal"""

    id: str
    """Deal id (ticket number)"""
    type: str
    """Deal type (one of DEAL_TYPE_BUY, DEAL_TYPE_SELL, DEAL_TYPE_BALANCE, DEAL_TYPE_CREDIT,
    DEAL_TYPE_CHARGE, DEAL_TYPE_CORRECTION, DEAL_TYPE_BONUS, DEAL_TYPE_COMMISSION, DEAL_TYPE_COMMISSION_DAILY,
    DEAL_TYPE_COMMISSION_MONTHLY, DEAL_TYPE_COMMISSION_AGENT_DAILY, DEAL_TYPE_COMMISSION_AGENT_MONTHLY,
    DEAL_TYPE_INTEREST, DEAL_TYPE_BUY_CANCELED, DEAL_TYPE_SELL_CANCELED, DEAL_DIVIDEND, DEAL_DIVIDEND_FRANKED,
    DEAL_TAX). See https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties#enum_deal_type"""
    entryType: str
    """Deal entry type (one of DEAL_ENTRY_IN, DEAL_ENTRY_OUT, DEAL_ENTRY_INOUT,
    DEAL_ENTRY_OUT_BY). See https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties#enum_deal_entry"""
    symbol: Optional[str]
    """Optional symbol deal relates to."""
    magic: Optional[int]
    """Optional deal magic number, identifies the EA which initiated the deal."""
    time: datetime
    """Time the deal was conducted at."""
    brokerTime: str
    """Time the deal was conducted at, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    volume: Optional[float]
    """Optional deal volume."""
    price: Optional[float]
    """Optional, the price the deal was conducted at."""
    commission: Optional[float]
    """Optional deal commission."""
    swap: Optional[float]
    """Optional deal swap."""
    profit: float
    """Deal profit."""
    positionId: Optional[str]
    """Optional id of position the deal relates to."""
    orderId: Optional[str]
    """Optional id of order the deal relates to."""
    comment: Optional[str]
    """Optional deal comment. The sum of the line lengths of the comment and the clientId
    must be less than or equal to 26. For more information see https://metaapi.cloud/docs/client/clientIdUsage/"""
    brokerComment: Optional[str]
    """Current comment value on broker side (possibly overriden by the broker)."""
    clientId: Optional[str]
    """Optional client-assigned id. The id value can be assigned when submitting a trade and will be present on
    position, history orders and history deals related to the trade. You can use this field to bind your trades
    to objects in your application and then track trade progress. The sum of the line lengths of the comment and
    the clientId must be less than or equal to 26. For more information see
    https://metaapi.cloud/docs/client/clientIdUsage/"""
    platform: str
    """Platform id (mt4 or mt5)."""
    reason: Optional[str]
    """Optional deal execution reason. One of DEAL_REASON_CLIENT, DEAL_REASON_MOBILE, DEAL_REASON_WEB,
    DEAL_REASON_EXPERT, DEAL_REASON_SL, DEAL_REASON_TP, DEAL_REASON_SO, DEAL_REASON_ROLLOVER, DEAL_REASON_VMARGIN,
    DEAL_REASON_SPLIT, DEAL_REASON_UNKNOWN. See
    https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties#enum_deal_reason."""
    accountCurrencyExchangeRate: Optional[float]
    """Current exchange rate of account currency into account base currency (USD if you did not override it)."""
    stopLoss: Optional[float]
    """Deal stop loss. For MT5 opening deal this is the SL of the order opening the position. For MT4 deals or MT5
    closing deal this is the last known position SL."""
    takeProfit: Optional[float]
    """Deal take profit. For MT5 opening deal this is the TP of the order opening the position. For MT4 deals or MT5
    closing deal this is the last known position TP."""


class MetatraderDeals(TypedDict):
    """MetaTrader history deals search query response"""

    deals: List[MetatraderDeal]
    """Array of history deals returned."""
    synchronizing: bool
    """Flag indicating that deal initial synchronization is still in progress
    and thus search results may be incomplete."""


MetatraderSession = TypedDict(
    "MetatraderSession",
    {
        "from": str,  # Session start time, in hh.mm.ss.SSS format.
        "to": str  # Session end time, in hh.mm.ss.SSS format.
    }
)
"""Metatrader trade or quote session"""


class MetatraderSessions(TypedDict, total=False):
    """Metatrader trade or quote session container, indexed by weekday."""
    SUNDAY: Optional[List[MetatraderSession]]
    """Array of sessions for SUNDAY."""
    MONDAY: Optional[List[MetatraderSession]]
    """Array of sessions for MONDAY."""
    TUESDAY: Optional[List[MetatraderSession]]
    """Array of sessions for TUESDAY."""
    WEDNESDAY: Optional[List[MetatraderSession]]
    """Array of sessions for WEDNESDAY."""
    THURSDAY: Optional[List[MetatraderSession]]
    """Array of sessions for THURSDAY."""
    FRIDAY: Optional[List[MetatraderSession]]
    """Array of sessions for FRIDAY."""
    SATURDAY: Optional[List[MetatraderSession]]
    """Array of sessions for SATURDAY."""


class MetatraderSymbolSpecification(TypedDict, total=False):
    """MetaTrader symbol specification. Contains symbol specification (see
    https://metaapi.cloud/docs/client/models/metatraderSymbolSpecification/)"""

    symbol: str
    """Symbol (e.g. a currency pair or an index)."""
    tickSize: float
    """Tick size"""
    minVolume: float
    """Minimum order volume for the symbol."""
    maxVolume: float
    """Maximum order volume for the symbol."""
    volumeStep: float
    """Order volume step for the symbol."""
    fillingModes: List[str]
    """List of allowed order filling modes. Can contain ORDER_FILLING_FOK, ORDER_FILLING_IOC or both.
    See https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#symbol_filling_mode for more
    details."""
    executionMode: str
    """Deal execution mode. Possible values are SYMBOL_TRADE_EXECUTION_REQUEST, SYMBOL_TRADE_EXECUTION_INSTANT,
    SYMBOL_TRADE_EXECUTION_MARKET, SYMBOL_TRADE_EXECUTION_EXCHANGE. See
    https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#enum_symbol_trade_execution for more
    details."""
    contractSize: float
    """Trade contract size."""
    quoteSessions: MetatraderSessions
    """Quote sessions, indexed by day of week."""
    tradeSessions: MetatraderSessions
    """Trade sessions, indexed by day of week."""
    tradeMode: Optional[str]
    """Order execution type. Possible values are SYMBOL_TRADE_MODE_DISABLED, SYMBOL_TRADE_MODE_LONGONLY,
    SYMBOL_TRADE_MODE_SHORTONLY, SYMBOL_TRADE_MODE_CLOSEONLY, SYMBOL_TRADE_MODE_FULL. See
    https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#enum_symbol_trade_mode for more
    details."""
    bondAccruedInterest: Optional[float]
    """Accrued interest – accumulated coupon interest, i.e. part of the coupon interest calculated in proportion to
    the number of days since the coupon bond issuance or the last coupon interest payment."""
    bondFaceValue: Optional[float]
    """Face value – initial bond value set by the issuer."""
    optionStrike: Optional[float]
    """The strike price of an option. The price at which an option buyer can buy (in a Call option) or sell (in a
    Put option) the underlying asset, and the option seller is obliged to sell or buy the appropriate amount of the
    underlying asset."""
    optionPriceSensivity: Optional[float]
    """Option/warrant sensitivity shows by how many points the price of the option's underlying asset should change so
    that the price of the option changes by one point."""
    liquidityRate: Optional[float]
    """Liquidity Rate is the share of the asset that can be used for the margin."""
    initialMargin: float
    """Initial margin means the amount in the margin currency required for opening a position with the volume of one
    lot. It is used for checking a client's assets when he or she enters the market."""
    maintenanceMargin: float
    """The maintenance margin. If it is set, it sets the margin amount in the margin currency of the symbol, charged
    from one lot. It is used for checking a client's assets when his/her account state changes. If the maintenance
    margin is equal to 0, the initial margin is used."""
    hedgedMargin: float
    """Contract size or margin value per one lot of hedged positions (oppositely directed positions of one symbol).
    Two margin calculation methods are possible for hedged positions. The calculation method is defined by the broker"""
    hedgedMarginUsesLargerLeg: Optional[bool]
    """Calculating hedging margin using the larger leg (Buy or Sell)."""
    marginCurrency: str
    """Margin currency."""
    priceCalculationMode: str
    """Contract price calculation mode. One of SYMBOL_CALC_MODE_UNKNOWN, SYMBOL_CALC_MODE_FOREX,
    SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE, SYMBOL_CALC_MODE_FUTURES, SYMBOL_CALC_MODE_CFD, SYMBOL_CALC_MODE_CFDINDEX,
    SYMBOL_CALC_MODE_CFDLEVERAGE, SYMBOL_CALC_MODE_EXCH_STOCKS, SYMBOL_CALC_MODE_EXCH_FUTURES,
    SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS, SYMBOL_CALC_MODE_EXCH_BONDS, SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX,
    SYMBOL_CALC_MODE_EXCH_BONDS_MOEX, SYMBOL_CALC_MODE_SERV_COLLATERAL. See
    https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#enum_symbol_calc_mode for more
    details."""
    baseCurrency: str
    """Base currency."""
    profitCurrency: Optional[str]
    """Profit currency."""
    swapMode: str
    """Swap calculation model. Allowed values are SYMBOL_SWAP_MODE_DISABLED,
    SYMBOL_SWAP_MODE_POINTS, SYMBOL_SWAP_MODE_CURRENCY_SYMBOL, SYMBOL_SWAP_MODE_CURRENCY_MARGIN,
    SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT, SYMBOL_SWAP_MODE_INTEREST_CURRENT, SYMBOL_SWAP_MODE_INTEREST_OPEN,
    SYMBOL_SWAP_MODE_REOPEN_CURRENT, SYMBOL_SWAP_MODE_REOPEN_BID. See
    https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#enum_symbol_swap_mode for more
    details."""
    swapLong: Optional[float]
    """Long swap value."""
    swapShort: Optional[float]
    """Short swap value."""
    swapRollover3Days: str
    """Day of week to charge 3 days swap rollover. Allowed values are SUNDAY, MONDAY, TUESDAY, WEDNESDAY, THURSDAY,
    FRIDAY, SATURDAY, NONE."""
    allowedExpirationModes: List[str]
    """Allowed order expiration modes. Allowed values are SYMBOL_EXPIRATION_GTC, SYMBOL_EXPIRATION_DAY,
    SYMBOL_EXPIRATION_SPECIFIED, SYMBOL_EXPIRATION_SPECIFIED_DAY.
    See https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#symbol_expiration_mode for more
    details."""
    allowedOrderTypes: List[str]
    """Allowed order types. Allowed values are SYMBOL_ORDER_MARKET, SYMBOL_ORDER_LIMIT, SYMBOL_ORDER_STOP,
    SYMBOL_ORDER_STOP_LIMIT, SYMBOL_ORDER_SL, SYMBOL_ORDER_TP, SYMBOL_ORDER_CLOSEBY. See
    https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#symbol_order_mode for more details."""
    orderGTCMode: str
    """If the expirationMode property is set to SYMBOL_EXPIRATION_GTC (good till canceled), the expiration of pending
    orders, as well as of Stop Loss/Take Profit orders should be additionally set using this enumeration. Allowed
    values are SYMBOL_ORDERS_GTC, SYMBOL_ORDERS_DAILY, SYMBOL_ORDERS_DAILY_EXCLUDING_STOPS. See
    https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#enum_symbol_order_gtc_mode for more
    details."""
    digits: int
    """Digits after a decimal point."""
    point: float
    """Point size."""
    path: Optional[str]
    """Path in the symbol tree."""
    description: str
    """Symbol description."""
    startTime: Optional[datetime]
    """Date of the symbol trade beginning (usually used for futures)."""
    expirationTime: Optional[datetime]
    """Date of the symbol trade end (usually used for futures)."""
    pipSize: Optional[float]
    """Size of a pip. Pip size is defined for spot and CFD symbols only."""
    stopsLevel: float
    """Minimal indention in points from the current close price to place stop orders."""
    freezeLevel: float
    """Distance to freeze trade operations in points."""


class MetatraderSymbolPrice(TypedDict):
    """MetaTrader symbol price. Contains current price for a symbol (see
    https://metaapi.cloud/docs/client/models/metatraderSymbolPrice/)"""

    symbol: str
    """Symbol (e.g. a currency pair or an index)."""
    bid: float
    """Bid price."""
    ask: float
    """Ask price."""
    profitTickValue: float
    """Tick value for a profitable position."""
    lossTickValue: float
    """Tick value for a loosing position."""
    accountCurrencyExchangeRate: float
    """Current exchange rate of account currency into account base currency (USD if you did not override it)."""
    time: datetime
    """Quote time."""
    brokerTime: str
    """Quote time, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""


class MetatraderTradeResponse(TypedDict):
    """MetaTrader trade response."""

    numericCode: int
    """Numeric response code, see https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes and
    https://book.mql4.com/appendix/errors. Response codes which indicate success are 0, 10008-10010, 10025. The rest
    codes are errors."""
    stringCode: str
    """String response code, see https://www.mql5.com/en/docs/constants/errorswarnings/enum_trade_return_codes and
    https://book.mql4.com/appendix/errors. Response codes which indicate success are ERR_NO_ERROR,
    TRADE_RETCODE_PLACED, TRADE_RETCODE_DONE, TRADE_RETCODE_DONE_PARTIAL, TRADE_RETCODE_NO_CHANGES. The rest codes are
    errors."""
    message: str
    """Human-readable response message."""
    orderId: str
    """Order id which was created/modified during the trade."""
    positionId: str
    """Position id which was modified during the trade."""


class TradeOptions(TypedDict, total=False):
    """Common trade options."""

    comment: Optional[str]
    """Optional order comment. The sum of the line lengths of the comment and the clientId must be less than or equal
    to 26. For more information see https://metaapi.cloud/docs/client/clientIdUsage/"""
    clientId: Optional[str]
    """Optional client-assigned id. The id value can be assigned when submitting a trade and will be present on
    position, history orders and history deals related to the trade. You can use this field to bind your trades to
    objects in your application and then track trade progress. The sum of the line lengths of the comment and the
    clientId must be less than or equal to 26. For more information see
    https://metaapi.cloud/docs/client/clientIdUsage/"""
    magic: Optional[str]
    """Magic (expert id) number. If not set default value specified in account entity will be used."""
    slippage: Optional[int]
    """Optional slippage in points. Should be greater or equal to zero. In not set, default value specified in
    account entity will be used. Slippage is ignored if execution mode set to SYMBOL_TRADE_EXECUTION_MARKET in
    symbol specification. Not used for close by orders."""


class MarketTradeOptions(TradeOptions, total=False):
    """Market trade options."""

    fillingModes: Optional[List[str]]
    """Optional allowed filling modes in the order of priority. Default is to allow all filling modes and prefer
    ORDER_FILLING_FOK over ORDER_FILLING_IOC. See
    https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type_filling for extra
    explanation."""


class CreateMarketTradeOptions(MarketTradeOptions, total=False):
    """Create market trade options."""

    trailingStopLoss: Optional[TrailingStopLoss]
    """Distance trailing stop loss configuration."""
    stopPriceBase: Optional[str]
    """Defines the base price to calculate SL/TP relative to for pending order requests. Default is CURRENT_PRICE,
    one of CURRENT_PRICE."""


class ExpirationOptions(TypedDict, total=False):
    """Pending order expiration settings."""

    type: str
    """Pending order expiration type. See
    https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type_time for the list of
    possible options. MetaTrader4 platform supports only ORDER_TIME_SPECIFIED expiration type. One of ORDER_TIME_GTC,
    ORDER_TIME_DAY, ORDER_TIME_SPECIFIED, ORDER_TIME_SPECIFIED_DAY."""
    time: Optional[datetime]
    """Optional pending order expiration time. Ignored if expiration type is not one of ORDER_TIME_DAY or
    ORDER_TIME_SPECIFIED."""


class PendingTradeOptions(TradeOptions):
    """Pending order trade options."""

    expiration: Optional[ExpirationOptions]
    """Optional pending order expiration settings. See Pending order expiration settings section."""
    trailingStopLoss: Optional[TrailingStopLoss]
    """Distance trailing stop loss configuration."""
    stopPriceBase: Optional[str]
    """Defines the base price to calculate SL/TP relative to for *_MODIFY and pending order requests. STOP_PRICE means
    the SL/TP is relative to previous SL/TP value. Default is OPEN_PRICE, one of CURRENT_PRICE, OPEN_PRICE."""
    openPriceUnits: Optional[str]
    """Open price units. ABSOLUTE_PRICE means the that the value of openPrice field is a final open price value.
    RELATIVE* means that the openPrice field value contains relative open price expressed either in price, points,
    pips, account currency or balance percentage. Default is ABSOLUTE_PRICE. One of ABSOLUTE_PRICE, RELATIVE_PRICE,
    RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY, RELATIVE_BALANCE_PERCENTAGE."""


class StopLimitPendingTradeOptions(PendingTradeOptions, total=False):
    """Options for creating a stop limit pending order."""

    openPriceBase: Optional[str]
    """Defines the base price to calculate open price relative to for ORDER_MODIFY and pending order requests. Default
    is CURRENT_PRICE for pending orders or STOP_LIMIT_PRICE for stop limit orders. One of CURRENT_PRICE, OPEN_PRICE,
    STOP_LIMIT_PRICE."""
    stopLimitPriceUnits: Optional[str]
    """Stop limit price units. ABSOLUTE_PRICE means the that the value of stopLimitPrice field is a final stop limit
    price value. RELATIVE* means that the stopLimitPrice field value contains relative stop limit price expressed
    either in price, points, pips, account currency or balance percentage. Default is ABSOLUTE_PRICE. One of
    ABSOLUTE_PRICE, RELATIVE_PRICE, RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY, RELATIVE_BALANCE_PERCENTAGE."""


class ModifyOrderOptions(TypedDict, total=False):
    """Options for modifying orders."""

    trailingStopLoss: Optional[TrailingStopLoss]
    """Distance trailing stop loss configuration."""
    stopPriceBase: Optional[str]
    """Defines the base price to calculate SL/TP relative to for *_MODIFY and pending order requests. STOP_PRICE means
    the SL/TP is relative to previous SL/TP value. Default is OPEN_PRICE, one of CURRENT_PRICE, OPEN_PRICE,
    STOP_PRICE."""
    openPriceUnits: Optional[str]
    """Open price units. ABSOLUTE_PRICE means the that the value of openPrice field is a final open price value.
    RELATIVE* means that the openPrice field value contains relative open price expressed either in price, points,
    pips, account currency or balance percentage. Default is ABSOLUTE_PRICE. One of ABSOLUTE_PRICE, RELATIVE_PRICE,
    RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY, RELATIVE_BALANCE_PERCENTAGE."""
    openPriceBase: Optional[str]
    """Defines the base price to calculate open price relative to for ORDER_MODIFY and pending order requests. Default
    is CURRENT_PRICE for pending orders or STOP_LIMIT_PRICE for stop limit orders. One of CURRENT_PRICE, OPEN_PRICE,
    STOP_LIMIT_PRICE."""
    stopLimitPriceUnits: Optional[str]
    """Stop limit price units. ABSOLUTE_PRICE means the that the value of stopLimitPrice field is a final stop limit
    price value. RELATIVE* means that the stopLimitPrice field value contains relative stop limit price expressed
    either in price, points, pips, account currency or balance percentage. Default is ABSOLUTE_PRICE. One of
    ABSOLUTE_PRICE, RELATIVE_PRICE, RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY, RELATIVE_BALANCE_PERCENTAGE."""
    stopLimitPriceBase: Optional[str]
    """Defines the base price to calculate stop limit price relative to for ORDER_MODIFY requests. One of
    CURRENT_PRICE, STOP_LIMIT_PRICE."""


class ValidationDetails(TypedDict, total=False):
    """Object to supply additional information for validation exceptions."""
    parameter: str
    """Name of invalid parameter."""
    value: Optional[str]
    """Entered invalid value."""
    message: str
    """Error message."""


class ExceptionMessage(TypedDict, total=False):
    """A REST API response that contains an exception message"""
    id: int
    """Error id"""
    error: str
    """Error name"""
    numericCode: Optional[int]
    """Numeric error code"""
    stringCode: Optional[str]
    """String error code"""
    message: str
    """Human-readable error message"""
    details: Optional[List[ValidationDetails]]
    """Additional information about error. Used to supply validation error details."""


class MarketDataSubscription(TypedDict, total=False):
    """Market data subscription."""
    type: str
    """Subscription type, one of quotes, candles, ticks, or marketDepth."""
    timeframe: Optional[str]
    """When subscription type is candles, defines the timeframe according to which the candles must be generated.
    Allowed values for MT5 are 1m, 2m, 3m, 4m, 5m, 6m, 10m, 12m, 15m, 20m, 30m, 1h, 2h, 3h,
    4h, 6h, 8h, 12h, 1d, 1w, 1mn. Allowed values for MT4 are 1m, 5m, 15m 30m, 1h, 4h, 1d, 1w, 1mn."""
    intervalInMilliseconds: Optional[float]
    """Defines how frequently the terminal will stream data to client. If not set, then the value configured in
    account will be used."""


class MarketDataUnsubscription(TypedDict):
    """Market data subscription."""
    type: str
    """Subscription type, one of quotes, candles, ticks, or marketDepth."""


class MetatraderCandle(TypedDict):
    """MetaTrader candle."""
    symbol: str
    """Symbol (e.g. currency pair or an index)."""
    timeframe: str
    """Timeframe candle was generated for, e.g. 1h. One of 1m, 2m, 3m, 4m, 5m, 6m, 10m, 12m, 15m, 20m, 30m, 1h, 2h,
    3h, 4h, 6h, 8h, 12h, 1d, 1w, 1mn."""
    time: datetime
    """Candle opening time."""
    brokerTime: str
    """Candle opening time, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    open: float
    """Open price."""
    high: float
    """High price."""
    low: float
    """Low price."""
    close: float
    """Close price."""
    tickVolume: float
    """Tick volume, i.e. number of ticks inside the candle."""
    spread: float
    """Spread in points."""
    volume: float
    """Trade volume."""


class MetatraderTick(TypedDict, total=False):
    """MetaTrader tick data."""
    symbol: str
    """Symbol (e.g. a currency pair or an index)."""
    time: datetime
    """Time."""
    brokerTime: str
    """Candle opening time, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    bid: Optional[float]
    """Bid price."""
    ask: Optional[float]
    """Ask price."""
    last: Optional[float]
    """Last deal price."""
    volume: float
    """Volume for the current last deal price."""
    side: str
    """Side is tick a result of buy or sell deal, one of buy or sell."""


class MetatraderBookEntry(TypedDict):
    """MetaTrader order book entry."""
    type: str
    """Entry type, one of BOOK_TYPE_SELL, BOOK_TYPE_BUY, BOOK_TYPE_SELL_MARKET, BOOK_TYPE_BUY_MARKET."""
    price: float
    """Price."""
    volume: float
    """Volume."""


class MetatraderBook(TypedDict):
    """MetaTrader order book."""
    symbol: str
    """Symbol (e.g. a currency pair or an index)."""
    time: datetime
    """Time."""
    brokerTime: str
    """Candle opening time, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    book: List[MetatraderBookEntry]
    """List of order book entries."""


class StopOptions(TypedDict):
    """Stop options."""
    value: float
    """Stop (SL or TP) value."""
    units: str
    """Stop units. ABSOLUTE_PRICE means the that the value of value field is a final stop value.
    RELATIVE_* means that the value field value contains relative stop expressed either in price, points, pips, account
    currency or balance percentage. Default is ABSOLUTE_PRICE. Allowed values are ABSOLUTE_PRICE, RELATIVE_PRICE,
    RELATIVE_POINTS, RELATIVE_PIPS, RELATIVE_CURRENCY, RELATIVE_BALANCE_PERCENTAGE."""


class ServerTime(TypedDict, total=False):
    """Current server time (see https://metaapi.cloud/docs/client/models/serverTime/)."""
    time: datetime
    """Current server time."""
    brokerTime: str
    """Current broker time, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    lastQuoteTime: Optional[datetime]
    """Last quote time."""
    lastQuoteBrokerTime: Optional[str]
    """Last quote time, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""


class QuoteTime(TypedDict):
    """Quote time."""
    time: datetime
    """Quote time."""
    brokerTime: str
    """Quote time in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""


class Margin(TypedDict, total=False):
    """Margin required to open a trade (see https://metaapi.cloud/docs/client/models/margin/)."""
    margin: Optional[float]
    """Margin required to open a trade. If margin can not be calculated, then this field is not defined."""


class MarginOrder(TypedDict, total=False):
    """Contains order to calculate margin for (see https://metaapi.cloud/docs/client/models/marginOrder/)."""
    symbol: str
    """Order symbol."""
    type: str
    """Order type, one of ORDER_TYPE_BUY or ORDER_TYPE_SELL."""
    volume: float
    """Order volume, must be greater than 0."""
    openPrice: float
    """Order open price, must be greater than 0."""
