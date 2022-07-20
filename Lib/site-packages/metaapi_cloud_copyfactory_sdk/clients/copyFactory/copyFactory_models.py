from typing_extensions import TypedDict, Literal
from typing import List, Optional
from datetime import datetime
from enum import Enum

CopyFactoryStrategySymbolMapping = TypedDict(
    "CopyFactoryStrategySymbolMapping",
    {
        "from": str,  # Symbol name to convert from.
        "to": str  # Symbol name to convert to.
    }
)
"""CopyFactory strategy symbol mapping."""


class CopyFactoryStrategyIdAndName(TypedDict, total=False):
    """CopyFactory strategy id and name."""
    id: str
    """Unique strategy id."""
    name: str
    """Human-readable strategy name."""


CopyFactoryStrategyStopoutReason = Literal[
    'day-balance-difference', 'date-balance-difference', 'week-balance-difference', 'week-to-date-balance-difference',
    'month-balance-difference', 'month-to-date-balance-difference', 'quarter-balance-difference',
    'quarter-to-date-balance-difference', 'year-balance-difference', 'year-to-date-balance-difference',
    'lifetime-balance-difference', 'day-balance-minus-equity', 'date-balance-minus-equity',
    'week-balance-minus-equity', 'week-to-date-balance-minus-equity', 'month-balance-minus-equity',
    'month-to-date-balance-minus-equity', 'quarter-balance-minus-equity', 'quarter-to-date-balance-minus-equity',
    'year-balance-minus-equity', 'year-to-date-balance-minus-equity', 'lifetime-balance-minus-equity',
    'day-equity-difference', 'date-equity-difference', 'week-equity-difference', 'week-to-date-equity-difference',
    'month-equity-difference', 'month-to-date-equity-difference', 'quarter-equity-difference',
    'quarter-to-date-equity-difference', 'year-equity-difference', 'year-to-date-equity-difference',
    'lifetime-equity-difference']
"""CopyFactory strategy stopout reason."""


class CopyFactoryStrategyStopout(TypedDict, total=False):
    """CopyFactory strategy stopout."""
    strategy: CopyFactoryStrategyIdAndName
    """Strategy which was stopped out."""
    partial: bool
    """Flag indicating that stopout is partial."""
    reason: CopyFactoryStrategyStopoutReason
    """Stopout reason."""
    reasonDescription: str
    """Human-readable description of the stopout reason."""
    closePositions: Optional[bool]
    """Flag indicating if positions should be closed."""
    stoppedAt: datetime
    """Time the strategy was stopped at."""
    stoppedTill: datetime
    """Time the strategy is stopped till."""


class CopyFactoryStrategyEquityCurveFilter(TypedDict, total=False):
    """CopyFactory strategy equity curve filter."""
    period: float
    """Moving average period, must be greater or equal to 1."""
    timeframe: str
    """Moving average granularity, a positive integer followed by time unit, e.g. 2h.
    Allowed units are s, m, h, d and w."""


class CopyFactoryStrategyDrawdownFilter(TypedDict, total=False):
    """CopyFactory strategy drawdown filter."""
    maxDrawdown: float
    """Maximum drawdown value after which action is executed. Drawdown should be configured as a fraction
    of 1, i.e. 0.15 means 15% drawdown value."""
    action: str
    """Action to take when drawdown exceeds maxDrawdown value. include means the trading signal
    will be transmitted only if dd is greater than maxDrawdown value. exclude means the trading signal will be
    transmitted only if dd is less than maxDrawdown value."""


class StrategyId(TypedDict, total=False):
    """Strategy id"""
    id: str
    """Strategy id"""


class CopyFactoryStrategySymbolFilter(TypedDict, total=False):
    """CopyFactory symbol filter."""
    included: List[str]
    """List of symbols copied. Leave the value empty to copy all symbols."""
    excluded: List[str]
    """List of symbols excluded from copying. Leave the value empty to copy all symbols."""


class CopyFactoryStrategyBreakingNewsFilter(TypedDict, total=False):
    """CopyFactory breaking news risk filter."""
    priorities: List[str]
    """List of breaking news priorities to stop trading on, leave empty to disable breaking news filter. One of high,
    medium, low."""
    closePositionTimeGapInMinutes: Optional[float]
    """Time interval specifying when to force close an already open position after breaking news. Default
    value is 60 minutes."""
    openPositionFollowingTimeGapInMinutes: Optional[float]
    """Time interval specifying when it is allowed to open position after calendar news. Default value is
    60 minutes."""


class CopyFactoryStrategyCalendarNewsFilter(TypedDict, total=False):
    """CopyFactory calendar news filter."""
    priorities: List[str]
    """List of calendar news priorities to stop trading on, leave empty to disable calendar news filter. One of
    election, high, medium, low."""
    closePositionTimeGapInMinutes: Optional[float]
    """Time interval specifying when to force close an already open position before calendar news. Default
    value is 60 minutes."""
    openPositionPrecedingTimeGapInMinutes: Optional[float]
    """Time interval specifying when it is still allowed to open position before calendar news. Default value
    is 120 minutes."""
    openPositionFollowingTimeGapInMinutes: Optional[float]
    """Time interval specifying when it is allowed to open position after calendar news. Default value is 60
    minutes"""


class CopyFactoryStrategyNewsFilter(TypedDict, total=False):
    """CopyFactory news risk filter."""
    breakingNewsFilter: Optional[CopyFactoryStrategyBreakingNewsFilter]
    """Breaking news filter."""
    calendarNewsFilter: Optional[CopyFactoryStrategyCalendarNewsFilter]
    """Calendar news filter."""


class CopyFactoryStrategyMaxStopLoss(TypedDict, total=False):
    """CopyFactory strategy max stop loss settings."""
    value: float
    """Maximum SL value."""
    units: str
    """SL units. Only pips value is supported at this point."""


CopyFactoryStrategyRiskLimitType = Literal['day', 'date', 'week', 'week-to-date', 'month', 'month-to-date',
                                           'quarter', 'quarter-to-date', 'year', 'year-to-date', 'lifetime']
"""CopyFactory strategy risk limit type."""


CopyFactoryStrategyRiskLimitApplyTo = Literal['balance-difference', 'balance-minus-equity', 'equity-difference']
"""CopyFactory strategy risk limit apply to enum."""


class CopyFactoryStrategyRiskLimit(TypedDict, total=False):
    """CopyFactory risk limit filter."""
    type: CopyFactoryStrategyRiskLimitType
    """Restriction type."""
    applyTo: CopyFactoryStrategyRiskLimitApplyTo
    """Account metric to apply limit to."""
    maxAbsoluteRisk: Optional[float]
    """Max drawdown allowed, measured in account currency."""
    maxRelativeRisk: Optional[float]
    """Max drawdown allowed, expressed as a fraction of 1."""
    closePositions: bool
    """Whether to force close positions when the risk is reached. If value is false then only the new trades will be
    halted, but existing ones will not be closed"""
    startTime: Optional[datetime]
    """Time to start risk tracking from. All previous trades will be ignored. You can use this value to reset
    the filter after stopout event."""


class CopyFactoryStrategyTradeSizeScaling(TypedDict, total=False):
    """CopyFactory strategy trade size scaling settings."""
    mode: str
    """If set to balance, the trade size on strategy subscriber will be scaled according to
    balance to preserve risk. If value is none, then trade size will be preserved irregardless of the subscriber
    balance. If value is contractSize, then trade size will be scaled according to contract size. If fixedVolume is
    set, then trade will be copied with a fixed volume of traceVolume setting. If fixedRisk is set, then each trade
    will be copied with a trade volume set to risk specific fraction of balance as configured by riskFraction setting.
    Note, that in fixedRisk mode trades without a SL are not copied. Default is balance. Allowed values: none,
    contractSize, balance, fixedVolume, fixedRisk."""
    tradeVolume: Optional[float]
    """Fixed trade volume for use with fixedVolume trade size scaling mode."""
    riskFraction: Optional[float]
    """Fixed risk fraction for use with fixedRisk trade size scaling mode."""
    forceTinyTrades: Optional[bool]
    """If set to true, that trades smaller than minVolume - 0.5 * volumeStep will be placed with minVolume volume, in
    spite that they will result in increased trade risk, as long as risk increase is in line with maxRiskCoefficient
    configuration. Othersite such trades will be skipped to avoid taking excessive trade risk. Default is false."""
    maxRiskCoefficient: Optional[float]
    """Sometimes when placing a small trade, the risk taken can exceed the subscription expectation due to volume
    rounding or forcefully placing tiny trades in accordance with forceTinyTrades setting. The maxRiskCoefficient
    setting will act as an extra line of protection to restrict trades if actual risk exceeds the value of expected
    subscription risk multiplied by maxRiskCoefficient. As a result trade volume will be decreased correspondingly or
    trade will be skipped if resulting volume is less than minVolume. Default value is 5, minimum value is 1."""


class CopyFactoryStrategySubscription(TypedDict, total=False):
    """CopyFactory strategy subscriptions."""
    strategyId: str
    """Id of the strategy to subscribe to."""
    multiplier: Optional[float]
    """Subscription multiplier, default is 1x."""
    skipPendingOrders: Optional[bool]
    """Flag indicating that pending orders should not be copied. Default is to copy pending orders."""
    closeOnly: Optional[str]
    """Setting which instructs the application not to open new positions. by-symbol means that it is still
    allowed to open new positions with a symbol equal to the symbol of an existing strategy position (can be used to
    gracefully exit strategies trading in netting mode or placing a series of related trades per symbol). immediately
    means to close all positions immediately. One of 'by-position', 'by-symbol', 'immediately'."""
    maxTradeRisk: Optional[float]
    """Max risk per trade, expressed as a fraction of 1. If trade has a SL, the trade size will be adjusted to
    match the risk limit. If not, the trade SL will be applied according to the risk limit."""
    reverse: Optional[bool]
    """Flag indicating that the strategy should be copied in a reverse direction."""
    reduceCorrelations: Optional[str]
    """Setting indicating whether to enable automatic trade correlation reduction. Possible settings are not
    specified (disable correlation risk restrictions), by-strategy (limit correlations for the strategy) or by-account
    (limit correlations for the account)."""
    symbolFilter: Optional[CopyFactoryStrategySymbolFilter]
    """Symbol filter which can be used to copy only specific symbols or exclude some symbols from copying."""
    newsFilter: Optional[CopyFactoryStrategyNewsFilter]
    """News risk filter configuration."""
    riskLimits: Optional[List[CopyFactoryStrategyRiskLimit]]
    """Strategy risk limits. You can configure trading to be stopped once total drawdown generated during
    specific period is exceeded. Can be specified either for balance or equity drawdown."""
    maxStopLoss: Optional[CopyFactoryStrategyMaxStopLoss]
    """Stop loss value restriction."""
    maxLeverage: Optional[float]
    """Setting indicating maximum leverage allowed when opening new positions. Any trade which results in a
    higher leverage will be discarded."""
    symbolMapping: Optional[List[CopyFactoryStrategySymbolMapping]]
    """Defines how symbol name should be changed when trading (e.g. when broker uses symbol names with unusual
    suffixes). By default this setting is disabled and the trades are copied using signal source symbol name."""
    tradeSizeScaling: Optional[CopyFactoryStrategyTradeSizeScaling]
    """Trade size scaling settings. By default the trade size on strategy subscriber side will be scaled according
    to balance to preserve risk."""
    copyStopLoss: Optional[bool]
    """Flag indicating whether stop loss should be copied. Default is to copy stop loss."""
    copyTakeProfit: Optional[bool]
    """Flag indicating whether take profit should be copied. Default is to copy take profit."""
    allowedSides: Optional[List[str]]
    """Trade sides which will be copied. Buy trades only, sell trades only or all trades. Default is to copy
    all trades."""
    minTradeVolume: Optional[float]
    """Minimum trade volume to copy. Trade signals with a smaller volume will not be copied."""
    maxTradeVolume: Optional[float]
    """Maximum trade volume to copy. Trade signals with a larger volume will be copied with maximum volume instead."""
    removed: Optional[bool]
    """Flag indicating that the subscription was scheduled for removal once all subscription positions will be
    closed."""


class CopyFactorySubscriberUpdate(TypedDict, total=False):
    """CopyFactory subscriber update."""
    name: str
    """Account human-readable name."""
    reservedMarginFraction: Optional[float]
    """Fraction of reserved margin to reduce a risk of margin call. Default is to reserve no margin. We
    recommend using maxLeverage setting instead. Specified as a fraction of balance thus the value is usually greater
    than 1."""
    phoneNumbers: Optional[List[str]]
    """Phone numbers to send sms notifications to. Leave empty to receive no sms notifications."""
    minTradeAmount: Optional[float]
    """Value of minimal trade size allowed, expressed in amount of account currency. Can be useful if your
    broker charges a fixed fee per transaction so that you can skip small trades with high broker commission rates.
    Default is 0."""
    closeOnly: Optional[str]
    """Setting which instructs the application not to open new positions. by-symbol means that it is still
    allowed to open new positions with a symbol equal to the symbol of an existing strategy position (can be used to
    gracefully exit strategies trading in netting mode or placing a series of related trades per symbol). immediately
    means to close all positions immediately. One of 'by-position', 'by-symbol', 'immediately'."""
    riskLimits: Optional[List[CopyFactoryStrategyRiskLimit]]
    """Account risk limits. You can configure trading to be stopped once total drawdown generated during
    specific period is exceeded. Can be specified either for balance or equity drawdown."""
    maxLeverage: Optional[float]
    """Setting indicating maxumum leverage allowed when opening a new positions. Any trade which results in a
    higher leverage will be discarded."""
    copyStopLoss: Optional[bool]
    """Flag indicating whether stop loss should be copied. Default is to copy stop loss."""
    copyTakeProfit: Optional[bool]
    """Flag indicating whether take profit should be copied. Default is to copy take profit."""
    allowedSides: Optional[List[str]]
    """Trade sides which will be copied. Buy trades only, sell trades only or all trades. Default is to copy
    all trades."""
    minTradeVolume: Optional[float]
    """Minimum trade volume to copy. Trade signals with a smaller volume will not be copied."""
    maxTradeVolume: Optional[float]
    """Maximum trade volume to copy. Trade signals with a larger volume will be copied with maximum volume instead."""
    subscriptions: List[CopyFactoryStrategySubscription]
    """Strategy subscriptions."""


class CopyFactorySubscriber(CopyFactorySubscriberUpdate):
    """CopyFactory subscriber model."""
    _id: str
    """Id of the MetaApi account to copy trades to."""


class CopyFactoryStrategyCommissionScheme(TypedDict, total=False):
    """CopyFactory strategy commission scheme."""
    type: str
    """Commission type. One of flat-fee, lots-traded, lots-won, amount-traded, amount-won, high-water-mark."""
    billingPeriod: str
    """Billing period. One of week, month, quarter."""
    commissionRate: float
    """Commission rate. Should be greater than or equal to zero if commission type is flat-fee, lots-traded or
    lots-won, should be greater than or equal to zero and less than or equal to 1 if commission type is amount-traded,
    amount-won, high-water-mark."""


class CopyFactoryStrategyMagicFilter(TypedDict, total=False):
    """CopyFactory strategy magic filter."""
    included: List[str]
    """List of magics (expert ids) or magic ranges copied. Leave the value empty to copy all magics."""
    excluded: List[str]
    """List of magics (expert ids) or magic ranges excluded from copying. Leave the value empty to copy all magics."""


class CopyFactoryStrategyTimeSettings(TypedDict, total=False):
    """CopyFactory strategy time settings."""
    lifetimeInHours: Optional[float]
    """Position lifetime. Default is to keep positions open up to 90 days."""
    openingIntervalInMinutes: Optional[float]
    """Time interval to copy new positions. Default is to let 1 minute for the position to get copied. If
    position were not copied during this time, the copying will not be retried anymore."""


class StrategyTelegramPublishingSettings(TypedDict, total=False):
    """Telegram publishing settings."""
    token: str
    """Telegram bot API token."""
    chatId: str
    """Telegram chatId to publish signals to. It can reference either a public channel (e.g. @myChannel),
    private channel (works by chat id only) or a user (works by chatId only). Note that in order to publish signals
    to a channel bot must be an admin of the channel."""
    template: str
    """Telegram message template. A substring of ${description} will be replaced with a signal description. Other
    variables you can use: ${operation}, ${orderId}, ${side}, ${type}, ${volume}, ${symbol}, ${openPrice},
    ${stopLoss}, ${takeProfit}."""


class StrategyTelegramSettings(TypedDict, total=False):
    """Strategy Telegram integration settings."""
    publishing: StrategyTelegramPublishingSettings
    """Telegram publishing settings."""


class CopyFactoryStrategyUpdate(TypedDict, total=False):
    """CopyFactory strategy update."""
    name: str
    """Strategy human-readable name."""
    description: str
    """Longer strategy human-readable description."""
    accountId: str
    """Id of the MetaApi account providing the strategy."""
    skipPendingOrders: Optional[bool]
    """Flag indicating that pending orders should not be copied. Default is to copy pending orders"""
    commissionScheme: Optional[CopyFactoryStrategyCommissionScheme]
    """Commission scheme allowed by this strategy."""
    maxTradeRisk: Optional[float]
    """Max risk per trade, expressed as a fraction of 1. If trade has a SL, the trade size will be adjusted to
    match the risk limit. If not, the trade SL will be applied according to the risk limit."""
    reverse: Optional[bool]
    """Flag indicating that the strategy should be copied in a reverse direction."""
    reduceCorrelations: Optional[str]
    """Setting indicating whether to enable automatic trade correlation reduction. Possible settings are not
    specified (disable correlation risk restrictions), by-strategy (limit correlations for the strategy) or by-account
    (limit correlations for the account)."""
    symbolFilter: Optional[CopyFactoryStrategySymbolFilter]
    """Symbol filters which can be used to copy only specific symbols or exclude some symbols from copying."""
    newsFilter: Optional[CopyFactoryStrategyNewsFilter]
    """News risk filter configuration."""
    riskLimits: Optional[List[CopyFactoryStrategyRiskLimit]]
    """Strategy risk limits. You can configure trading to be stopped once total drawdown generated during
    specific period is exceeded. Can be specified either for balance or equity drawdown."""
    maxStopLoss: Optional[CopyFactoryStrategyMaxStopLoss]
    """Stop loss value restriction."""
    maxLeverage: Optional[float]
    """Max leverage risk restriction. All trades resulting in a leverage value higher than specified will
    be skipped."""
    symbolMapping: Optional[List[CopyFactoryStrategySymbolMapping]]
    """Defines how symbol name should be changed when trading (e.g. when broker uses symbol names with unusual
    suffixes). By default this setting is disabled and the trades are copied using signal source symbol name."""
    tradeSizeScaling: Optional[CopyFactoryStrategyTradeSizeScaling]
    """Trade size scaling settings. By default the trade size on strategy subscriber side will be scaled according
    to balance to preserve risk."""
    copyStopLoss: Optional[bool]
    """Flag indicating whether stop loss should be copied. Default is to copy stop loss."""
    copyTakeProfit: Optional[bool]
    """Flag indicating whether take profit should be copied. Default is to copy take profit."""
    allowedSides: Optional[List[str]]
    """Trade sides which will be copied. Buy trades only, sell trades only or all trades. Default is to copy
    all trades."""
    minTradeVolume: Optional[float]
    """Minimum trade volume to copy. Trade signals with a smaller volume will not be copied."""
    maxTradeVolume: Optional[float]
    """Maximum trade volume to copy. Trade signals with a larger volume will be copied with maximum volume instead."""
    magicFilter: Optional[CopyFactoryStrategyMagicFilter]
    """Magic (expert id) filter."""
    equityCurveFilter: Optional[CopyFactoryStrategyEquityCurveFilter]
    """Filter which permits the trades only if account equity is greater than balance moving average."""
    drawdownFilter: Optional[CopyFactoryStrategyDrawdownFilter]
    """Master account strategy drawdown filter."""
    symbolsTraded: Optional[List[str]]
    """Symbols traded by this strategy. Specifying the symbols will improve trade latency on first trades made by
    strategy. If you do not specify this setting the application will monitor the strategy trades and detect the
    symbols automatically over time."""
    telegram: Optional[StrategyTelegramSettings]
    """Telegram publishing settings."""
    timeSettings: Optional[CopyFactoryStrategyTimeSettings]
    """Settings to manage copying timeframe and position lifetime. Default is to copy position within 1 minute from
    being opened at source and let the position to live for up to 90 days."""


class CopyFactoryStrategy(CopyFactoryStrategyUpdate, total=False):
    """CopyFactory provider strategy"""
    _id: str
    """Unique strategy id."""
    platformCommissionRate: float
    """Commission rate the platform charges for strategy copying, applied to commissions charged by provider. This
    commission applies only to accounts not managed directly by provider. Should be fraction of 1."""
    closeOnRemovalMode: Optional[str]
    """Position close mode on strategy or subscription removal. Preserve means that positions will not be closed and
    will not be managed by CopyFactory. close-gracefully-by-position means that positions will continue to be managed
    by CopyFactory, but only close signals will be copied. close-gracefully-by-symbol means that positions will
    continue to be managed by CopyFactory, but only close signals will be copied or signals to open positions for the
    symbols which already have positions opened. close-immediately means that all positions will be closed immediately.
    Default is close-immediately. This field can be changed via remove portfolio member API only. One of preserve,
    close-gracefully-by-position, close-gracefully-by-symbol, close-immediately."""


class CopyFactorySubscriberOrProviderUser(TypedDict, total=False):
    """CopyFactory provider or subscriber user"""
    id: str
    """Profile id."""
    name: str
    """User name."""
    strategies: List[CopyFactoryStrategyIdAndName]
    """Array of strategy IDs provided by provider or subscribed to by subscriber."""


class CopyFactoryTransactionMetrics(TypedDict, total=False):
    """Trade copying metrics such as slippage and latencies."""
    tradeCopyingLatency: Optional[float]
    """Trade copying latency, measured in milliseconds based on transaction time provided by broker."""
    tradeCopyingSlippageInBasisPoints: Optional[float]
    """Trade copying slippage, measured in basis points (0.01 percent) based on transaction price provided by broker."""
    tradeCopyingSlippageInAccountCurrency: Optional[float]
    """Trade copying slippage, measured in account currency based on transaction price provided by broker."""
    mtAndBrokerSignalLatency: Optional[float]
    """Trade signal latency introduced by broker and MT platform, measured in milliseconds."""
    tradeAlgorithmLatency: Optional[float]
    """Trade algorithm latency introduced by CopyFactory servers, measured in milliseconds."""
    mtAndBrokerTradeLatency: Optional[float]
    """Trade latency for a copied trade introduced by broker and MT platform, measured in milliseconds"""


class CopyFactoryTransaction(TypedDict, total=False):
    """CopyFactory transaction."""
    id: str
    """Transaction id."""
    type: str
    """Transaction type (one of DEAL_TYPE_BUY, DEAL_TYPE_SELL, DEAL_TYPE_BALANCE, DEAL_TYPE_CREDIT, DEAL_TYPE_CHARGE,
    DEAL_TYPE_CORRECTION, DEAL_TYPE_BONUS, DEAL_TYPE_COMMISSION, DEAL_TYPE_COMMISSION_DAILY,
    DEAL_TYPE_COMMISSION_MONTHLY, DEAL_TYPE_COMMISSION_AGENT_DAILY, DEAL_TYPE_COMMISSION_AGENT_MONTHLY,
    DEAL_TYPE_INTEREST, DEAL_TYPE_BUY_CANCELED, DEAL_TYPE_SELL_CANCELED, DEAL_DIVIDEND, DEAL_DIVIDEND_FRANKED,
    DEAL_TAX). See https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties#enum_deal_type."""
    time: datetime
    """Transaction time."""
    subscriberId: str
    """CopyFactory subscriber id."""
    symbol: Optional[str]
    """Symbol traded."""
    subscriberUser: CopyFactorySubscriberOrProviderUser
    """Strategy subscriber."""
    demo: bool
    """Demo account flag."""
    providerUser: CopyFactorySubscriberOrProviderUser
    """Strategy provider."""
    strategy: CopyFactoryStrategyIdAndName
    """Strategy."""
    positionId: Optional[str]
    """Source position id."""
    slavePositionId: Optional[str]
    """Slave position id."""
    improvement: float
    """High-water mark strategy balance improvement."""
    providerCommission: float
    """Provider commission."""
    platformCommission: float
    """Platform commission."""
    incomingProviderCommission: Optional[float]
    """Commission paid by provider to underlying providers."""
    incomingPlatformCommission: Optional[float]
    """Platform commission paid by provider to underlying providers."""
    quantity: Optional[float]
    """Trade volume."""
    lotPrice: Optional[float]
    """Trade lot price."""
    tickPrice: Optional[float]
    """Trade tick price."""
    amount: Optional[float]
    """Trade amount."""
    commission: Optional[float]
    """Trade commission."""
    swap: float
    """Trade swap."""
    profit: float
    """Trade profit."""
    metrics: Optional[CopyFactoryTransactionMetrics]
    """Trade copying metrics such as slippage and latencies. Measured selectively for copied trades"""


class CopyFactoryPortfolioStrategyMember(TypedDict, total=False):
    """Portfolio strategy member."""
    strategyId: str
    """Member strategy id."""
    multiplier: float
    """Copying multiplier (weight in the portfolio)."""
    skipPendingOrders: Optional[bool]
    """Flag indicating that pending orders should not be copied. Default is to copy pending orders."""
    maxTradeRisk: Optional[float]
    """Max risk per trade, expressed as a fraction of 1. If trade has a SL, the trade size will be adjusted
    to match the risk limit. If not, the trade SL will be applied according to the risk limit."""
    reverse: Optional[bool]
    """Flag indicating that the strategy should be copied in a reverse direction."""
    reduceCorrelations: Optional[str]
    """Setting indicating whether to enable automatic trade correlation reduction. Possible settings are
    not specified (disable correlation risk restrictions), by-strategy (limit correlations for the strategy) or
    by-account (limit correlations for the account)."""
    symbolFilter: Optional[CopyFactoryStrategySymbolFilter]
    """Symbol filters which can be used to copy only specific symbols or exclude some symbols from copying."""
    newsFilter: Optional[CopyFactoryStrategyNewsFilter]
    """News risk filter configuration."""
    riskLimits: Optional[List[CopyFactoryStrategyRiskLimit]]
    """Strategy risk limits. You can configure trading to be stopped once total drawdown generated during
    specific period is exceeded. Can be specified either for balance or equity drawdown."""
    maxStopLoss: Optional[CopyFactoryStrategyMaxStopLoss]
    """Stop loss value restriction."""
    maxLeverage: Optional[float]
    """Max leverage risk restriction. All trades resulting in a leverage value higher than specified will be
    skipped."""
    symbolMapping: Optional[List[CopyFactoryStrategySymbolMapping]]
    """Defines how symbol name should be changed when trading (e.g. when broker uses symbol names with unusual
    suffixes). By default this setting is disabled and the trades are copied using signal source symbol name."""
    tradeSizeScaling: Optional[CopyFactoryStrategyTradeSizeScaling]
    """Trade size scaling settings. By default the trade size on strategy subscriber side will be scaled according
    to balance to preserve risk."""
    copyStopLoss: Optional[bool]
    """Flag indicating whether stop loss should be copied. Default is to copy stop loss."""
    copyTakeProfit: Optional[bool]
    """Flag indicating whether take profit should be copied. Default is to copy take profit."""
    allowedSides: Optional[List[str]]
    """Trade sides which will be copied. Buy trades only, sell trades only or all trades. Default is to copy
    all trades."""
    minTradeVolume: Optional[float]
    """Minimum trade volume to copy. Trade signals with a smaller volume will not be copied."""
    maxTradeVolume: Optional[float]
    """Maximum trade volume to copy. Trade signals with a larger volume will be copied with maximum volume instead."""
    closeOnRemovalMode: Optional[str]
    """Position close mode on strategy or subscription removal. Preserve means that positions will not be closed and
    will not be managed by CopyFactory. close-gracefully-by-position means that positions will continue to be managed
    by CopyFactory, but only close signals will be copied. close-gracefully-by-symbol means that positions will
    continue to be managed by CopyFactory, but only close signals will be copied or signals to open positions for the
    symbols which already have positions opened. close-immediately means that all positions will be closed immediately.
    Default is close-immediately. This field can be changed via remove portfolio member API only. One of preserve,
    close-gracefully-by-position, close-gracefully-by-symbol, close-immediately."""


class CopyFactoryPortfolioStrategyUpdate(TypedDict, total=False):
    """Portfolio strategy update."""
    name: str
    """Strategy human-readable name."""
    description: str
    """Longer strategy human-readable description."""
    members: List[CopyFactoryPortfolioStrategyMember]
    """Array of portfolio members."""
    commissionScheme: Optional[CopyFactoryStrategyCommissionScheme]
    """Commission scheme allowed by this strategy. By default monthly billing period with no commission is being
    used."""
    skipPendingOrders: Optional[bool]
    """Flag indicating that pending orders should not be copied. Default is to copy pending orders."""
    maxTradeRisk: Optional[float]
    """Max risk per trade, expressed as a fraction of 1. If trade has a SL, the trade size will be adjusted
    to match the risk limit. If not, the trade SL will be applied according to the risk limit."""
    reverse: Optional[bool]
    """Flag indicating that the strategy should be copied in a reverse direction."""
    reduceCorrelations: Optional[str]
    """Setting indicating whether to enable automatic trade correlation reduction. Possible settings are not
    specified (disable correlation risk restrictions), by-strategy (limit correlations for the strategy) or by-account
    (limit correlations for the account)."""
    symbolFilter: Optional[CopyFactoryStrategySymbolFilter]
    """Symbol filters which can be used to copy only specific symbols or exclude some symbols from copying."""
    newsFilter: Optional[CopyFactoryStrategyNewsFilter]
    """News risk filter configuration."""
    riskLimits: Optional[List[CopyFactoryStrategyRiskLimit]]
    """Strategy risk limits. You can configure trading to be stopped once total drawdown generated during
    specific period is exceeded. Can be specified either for balance or equity drawdown."""
    maxStopLoss: Optional[CopyFactoryStrategyMaxStopLoss]
    """Stop loss value restriction."""
    maxLeverage: Optional[float]
    """Max leverage risk restriction. All trades resulting in a leverage value higher than specified will be
    skipped."""
    symbolMapping: Optional[List[CopyFactoryStrategySymbolMapping]]
    """Defines how symbol name should be changed when trading (e.g. when broker uses symbol names with unusual
    suffixes). By default this setting is disabled and the trades are copied using signal source symbol name."""
    tradeSizeScaling: Optional[CopyFactoryStrategyTradeSizeScaling]
    """Trade size scaling settings. By default the trade size on strategy subscriber side will be scaled according
    to balance to preserve risk."""
    copyStopLoss: Optional[bool]
    """Flag indicating whether stop loss should be copied. Default is to copy stop loss."""
    copyTakeProfit: Optional[bool]
    """Flag indicating whether take profit should be copied. Default is to copy take profit."""
    allowedSides: Optional[List[str]]
    """Trade sides which will be copied. Buy trades only, sell trades only or all trades. Default is to copy
    all trades."""
    minTradeVolume: Optional[float]
    """Minimum trade volume to copy. Trade signals with a smaller volume will not be copied."""
    maxTradeVolume: Optional[float]
    """Maximum trade volume to copy. Trade signals with a larger volume will be copied with maximum volume instead."""


class CopyFactoryPortfolioStrategy(CopyFactoryPortfolioStrategyUpdate, total=False):
    """Portfolio strategy, i.e. the strategy which includes a set of other strategies."""
    _id: str
    """Unique strategy id."""
    platformCommissionRate: float
    """Commission rate the platform charges for strategy copying, applied to commissions charged by provider. This
    commission applies only to accounts not managed directly by provider. Should be fraction of 1."""
    closeOnRemovalMode: Optional[str]
    """Position close mode on strategy or subscription removal. Preserve means that positions will not be closed and
    will not be managed by CopyFactory. close-gracefully-by-position means that positions will continue to be managed
    by CopyFactory, but only close signals will be copied. close-gracefully-by-symbol means that positions will
    continue to be managed by CopyFactory, but only close signals will be copied or signals to open positions for the
    symbols which already have positions opened. close-immediately means that all positions will be closed immediately.
    Default is close-immediately. This field can be changed via remove portfolio member API only. One of preserve,
    close-gracefully-by-position, close-gracefully-by-symbol, close-immediately."""


class LogLevel(Enum):
    """Log level."""
    INFO = 'INFO'
    WARN = 'WARN'
    ERROR = 'ERROR'


class CopyFactoryUserLogMessage(TypedDict, total=False):
    """Trade copying user log record."""
    time: datetime
    """Log record time."""
    symbol: Optional[str]
    """Symbol traded."""
    strategyId: Optional[str]
    """Id of the strategy event relates to."""
    strategyName: Optional[str]
    """Name of the strategy event relates to."""
    positionId: Optional[str]
    """Position id event relates to."""
    side: Optional[str]
    """Side of the trade event relates to. One of buy, sell, close."""
    type: Optional[str]
    """Type of the trade event relates to. One of market, limit, stop."""
    openPrice: Optional[float]
    """Open price for limit and stop orders."""
    level: LogLevel
    """Log level. One of INFO, WARN, ERROR."""
    message: str
    """Log message."""


class CopyFactoryExternalSignalUpdate(TypedDict, total=False):
    """CopyFactory external signal update payload."""
    symbol: str
    """Trade symbol."""
    type: str
    """Trade type (one of POSITION_TYPE_BUY, POSITION_TYPE_SELL, ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT,
    ORDER_TYPE_BUY_STOP, ORDER_TYPE_SELL_STOP)."""
    time: datetime
    """Time the signal was emitted at."""
    updateTime: Optional[datetime]
    """Last time of the signal update."""
    volume: float
    """Volume traded."""
    magic: Optional[float]
    """Expert advisor id"""
    stopLoss: Optional[float]
    """Stop loss price."""
    takeProfit: Optional[float]
    """Take profit price."""
    openPrice: Optional[float]
    """Pending order open price."""


class CopyFactoryExternalSignalRemove(TypedDict, total=False):
    """CopyFactory external signal remove payload."""
    time: datetime
    """The time signal was removed (closed) at."""


class CopyFactoryTradingSignal(TypedDict, total=False):
    """CopyFactory trading signal."""
    strategy: CopyFactoryStrategyIdAndName
    """Strategy the signal arrived from."""
    positionId: str
    """Id of the position the signal was generated from."""
    time: datetime
    """Signal time."""
    symbol: str
    """Symbol traded."""
    type: str
    """Type of the trade (one of market, limit, stop)."""
    side: str
    """Side of the trade (one of buy, sell, close)."""
    openPrice: Optional[float]
    """Open price for limit and stop orders."""
    stopLoss: Optional[float]
    """Stop loss price."""
    takeProfit: Optional[float]
    """Take profit price."""
    signalVolume: float
    """The signal volume."""
    subscriberVolume: float
    """The volume already open on subscriber side."""
    subscriberProfit: float
    """The total profit of the position on subscriber side."""
    closeAfter: datetime
    """The time the signal will be automatically closed at."""
    closeOnly: Optional[bool]
    """Flag indicating that only closing side of this signal will be copied."""


class CopyFactoryCloseInstructions(TypedDict, total=False):
    """CopyFactory close instructions"""
    mode: Optional[str]
    """Position close mode on strategy or subscription removal. Preserve means that positions will not be closed and
    will not be managed by CopyFactory. close-gracefully-by-position means that positions will continue to be managed
    by CopyFactory, but only close signals will be copied. close-gracefully-by-symbol means that positions will
    continue to be managed by CopyFactory, but only close signals will be copied or signals to open positions for the
    symbols which already have positions opened. close-immediately means that all positions will be closed immediately.
    Default is close-immediately (one of 'preserve', 'close-gracefully-by-position', 'close-gracefully-by-symbol',
    'close-immediately')."""
    removeAfter: Optional[datetime]
    """Time to force remove object after. The object will be removed after this time, even if positions are not yet
    closed fully. Default is current date plus 30 days. Can not be less than 30 days or greater than current date plus
    90 days. The setting is ignored when a subscription is being removed."""
