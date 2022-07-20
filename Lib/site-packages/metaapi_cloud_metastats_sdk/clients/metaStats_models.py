from typing_extensions import TypedDict
from typing import Optional, List


class CurrencySummaryHistoryDayMetrics(TypedDict):
    """Profit from trading a currency pair in one trading day."""
    date: str
    """Date of trading day, in broker timezone, YYYY-MM-DD format."""
    totalProfit: float
    """Total profit at the end of the day."""
    totalPips: Optional[float]
    """Total pips of trading day."""
    shortProfit: Optional[float]
    """Total profit of short trades per day."""
    longProfit: Optional[float]
    """Total profit of long trades per day."""
    shortPips: Optional[float]
    """Total pips of short trades per day."""
    longPips: Optional[float]
    """Total pips of long trades per day."""


class CurrencySummaryTotalMetrics(TypedDict):
    """Provides general data of this currency trading."""
    profit: float
    """Cumulative profit of this currency trading."""
    trades: int
    """The number of all trades with this currency."""
    pips: Optional[float]
    """Cumulative pips of this currency trading."""
    wonTrades: Optional[int]
    """The number of winning trades with this currency."""
    lostTrades: Optional[int]
    """The number of losing trades with this currency."""
    wonTradesPercent: Optional[float]
    """Percentage of winning trades with this currency."""
    lostTradesPercent: Optional[float]
    """Percentage of losing trades with this currency."""


class CurrencySummaryTradeMetrics(TypedDict):
    """Provides profit and number of trades in specific trade and currency."""
    profit: float
    """Cumulative profit of this currency trading."""
    trades: int
    """The number of all trades with this currency."""
    pips: Optional[float]
    """Cumulative pips of this currency trading."""


class CurrencySummaryMetrics(TypedDict):
    """Provides statistics on winning and losing trades indicating the amount in the context of long and
    short positions. Statistics is given for all currency pairs, for which positions were opened."""
    currency: str
    """Trading currency pair."""
    history: List[CurrencySummaryHistoryDayMetrics]
    """History of trading a currency pair per trading days."""
    total: CurrencySummaryTotalMetrics
    """General data (such as profit, number of trades) about trading a specific currency pair."""
    short: Optional[CurrencySummaryTradeMetrics]
    """Profit and number of trades of short trades in a specific currency."""
    long: Optional[CurrencySummaryTradeMetrics]
    """Profit and number of trades of long trades in a specific currency."""


class PeriodMetrics(TypedDict):
    """Provides statistics for one trade period compared to the results for the previous period."""
    profit: Optional[float]
    """Cumulative profit of this period."""
    pips: Optional[float]
    """Cumulative pips of this period."""
    lots: Optional[float]
    """Cumulative lots of this period."""
    gain: Optional[float]
    """Gain of this period."""
    trades: Optional[int]
    """The number of trades of this period."""
    wonTradesPercent: Optional[float]
    """Percentage of winning trades of this period."""
    profitDifference: Optional[float]
    """Difference in profit with the previous period."""
    pipsDifference: Optional[float]
    """Difference in pips with the previous period."""
    lotsDifference: Optional[float]
    """Difference in lots with the previous period."""
    gainDifference: Optional[float]
    """Difference in gain with the previous period."""
    tradesDifference: Optional[int]
    """Difference in the number of trades with the previous period."""
    wonTradesPercentDifference: Optional[float]
    """Difference in percentage of winning trades with the previous period."""


class Periods(TypedDict):
    """Provides statistics for today, this week, this month, this year."""
    today: Optional[PeriodMetrics]
    """Trade information for today."""
    thisWeek: Optional[PeriodMetrics]
    """Trade information for this week."""
    thisMonth: Optional[PeriodMetrics]
    """Trade information for this month."""
    thisYear: Optional[PeriodMetrics]
    """Trade information for this year."""


class DailyGrowthMetrics(TypedDict):
    """Provides each profit received from the volume of trade and changes in balance, total accumulated income and
    existing account drawdown by day."""
    date: str
    """Date of trading day in broker timezone, YYYY-MM-DD format."""
    profit: Optional[float]
    """Cumulative profit per day."""
    pips: Optional[float]
    """Cumulative pips per day."""
    lots: Optional[float]
    """Cumulative lots per day."""
    gains: Optional[float]
    """Cumulative gains per day."""
    totalProfit: float
    """Total profit in this day end."""
    totalGains: float
    """Total gains in this day end."""
    balance: float
    """Balance in this day end."""
    drawdownPercentage: Optional[float]
    """Percentage of balance drawdown in this day end."""
    drawdownProfit: Optional[float]
    """Maximum registered balance drawdown in basic currency during this day."""


class MonthlyAnalyticCurrencyMetrics(TypedDict):
    """Currency pair trading information for monthly analysis."""
    currency: str
    """Currency pair."""
    averageHoldingTimeLongsInMilliseconds: Optional[float]
    """Average holding time of long trades."""
    averageHoldingTimeShortsInMilliseconds: Optional[float]
    """Average holding time of short trades."""
    rewardToRiskRatio: float
    """The difference between reward and risk, where the lesser is always one. So 0 means
    reward:risk=1:1, 2 means 3:1, -0.5 means 1:1.5."""
    popularityPercent: float
    """The percentage of popularity of this currency this month."""


class MonthlyAnalyticsMetrics(TypedDict):
    """Monthly analysis of trading on this account."""
    date: str
    """Date of trading month in broker timezone, YYYY-MM format."""
    profit: Optional[float]
    """Cumulative profit per month."""
    pips: Optional[float]
    """Cumulative pips per month."""
    lots: Optional[float]
    """Cumulative lots per month."""
    gains: Optional[float]
    """Cumulative gains per month."""
    trades: Optional[int]
    """The number of trades of this month."""
    currencies: Optional[List[MonthlyAnalyticCurrencyMetrics]]
    """List of currency pair trading informations for monthly analysis."""


class TradeByTimeMetrics(TypedDict):
    """Opening/closing deals by days of the week or by hours of the day."""
    date: str
    """Date of trading month in broker timezone, YYYY-MM format."""
    profit: float
    """The total profit of the trades at this time."""
    shortProfit: Optional[float]
    """The total profit of short trades at this time."""
    longProfit: Optional[float]
    """The total profit of long trades at this time."""
    wonProfit: Optional[float]
    """The total profit of winning trades at this time."""
    lostProfit: Optional[float]
    """The total profit of losing trades at this time."""
    pips: Optional[float]
    """The total pips of the trades at this time."""
    shortPips: Optional[float]
    """The total pips of short trades at this time."""
    longPips: Optional[float]
    """The total pips of long trades at this time."""
    wonPips: Optional[float]
    """The total pips of winning trades at this time."""
    lostPips: Optional[float]
    """The total pips of losing trades at this time."""
    lots: float
    """Cumulative lots of trades at this time."""
    gains: float
    """Cumulative gains of trades at this time."""
    shortGains: Optional[float]
    """Cumulative gains of short trades at this time."""
    longGains: Optional[float]
    """Cumulative gains of long trades at this time."""
    wonGains: Optional[float]
    """Cumulative gains of winning trades at this time."""
    lostGains: Optional[float]
    """Cumulative gains of losing trades at this time."""
    trades: int
    """The number of all trades at this time."""
    shortTrades: Optional[int]
    """The number of short trades at this time."""
    longTrades: Optional[int]
    """The number of long trades at this time."""
    wonTrades: Optional[int]
    """The number of winning trades at this time."""
    lostTrades: Optional[int]
    """The number of losing trades at this time."""
    shortTradesPercent: Optional[float]
    """Percentage of short trades at this time."""
    longTradesPercent: Optional[float]
    """Percentage of long trades at this time."""
    wonTradesPercent: Optional[float]
    """Percentage of winning trades at this time."""
    lostTradesPercent: Optional[float]
    """Percentage of losing trades at this time."""
    hour: Optional[int]
    """Day hour (only for by hour case)', within 0-23."""
    day: Optional[int]
    """Weekday number (only for by day case), within 0-6."""


class RiskOfRuinMetrics(TypedDict):
    """Risk of ruin of balance metrics."""
    lossSize: float
    """Loss size of balance."""
    probabilityOfLoss: float
    """Probability of loss shows the risk of losing a particular part of the balance."""
    consecutiveLosingTrades: float
    """The number of losing trades that must be entered sequentially in order for this part of the
    balance to be lost."""


class OneTradeDurationMetrics(TypedDict):
    """Metrics of one trade duration."""
    gains: List[float]
    """List of gains for this duration."""
    profits: List[float]
    """List of profits for this duration."""
    lots: List[float]
    """List of lots for this duration."""
    pips: Optional[List[float]]
    """List of pips for this duration."""
    durationInMinutes: float
    """Duration of trades in minutes."""


class TradeDurationMetrics(TypedDict):
    """Metrics for each duration of trades."""
    won: Optional[List[OneTradeDurationMetrics]]
    """Metrics of winning trades."""
    lost: Optional[List[OneTradeDurationMetrics]]
    """Metrics of losing trades."""


class TradeDurationDiagramColumnCollectionMetrics(TypedDict):
    """Collection of metrics of trades in the current column for the diagram."""
    gains: List[float]
    """List of gains."""
    profits: List[float]
    """List of profits."""
    lots: List[float]
    """List of lots."""
    pips: Optional[List[float]]
    """List of pips."""


class TradeDurationDiagramColumnMetrics(TypedDict):
    """Information column about the duration of trades for the diagram."""
    durations: float
    """The number of durations in this column."""
    trades: int
    """The number of trades in this column."""
    name: str
    """Name of this column, one of 'seconds', 'minutes', 'hours', 'days', 'weeks', 'months'."""
    minDurationInSeconds: float
    """Minimum trade duration in this column in seconds."""
    maxDurationInSeconds: Optional[float]
    """Maximum trade duration in this column in seconds."""
    won: Optional[TradeDurationDiagramColumnCollectionMetrics]
    """Collection of metrics of winning trades in this column."""
    lost: Optional[TradeDurationDiagramColumnCollectionMetrics]
    """Collection of metrics of losing trades in this column."""


class Metrics(TypedDict):
    """Trading statistics metrics."""
    inclusive: Optional[bool]
    """Indicates whether open positions are included in the metrics, "False" means that there are no open positions.
    Only for a request with includeOpenPositions=True."""
    balance: float
    """Money on the account, not accounting for the results of currently open positions."""
    highestBalanceDate: Optional[str]
    """Date of maximum balance that have ever been on the account, in broker timezone, YYYY-MM-DD HH:mm:ss.SSS
    format."""
    highestBalance: Optional[float]
    """Maximum balance that have ever been on the account."""
    equity: float
    """The result (current amount) of all positions, including opened."""
    margin: float
    """Current value of margin."""
    freeMargin: float
    """Current value of free margin."""
    marginLevel: Optional[float]
    """Current value of margin level."""
    trades: float
    """Total number of closed positions on the account."""
    withdrawals: Optional[float]
    """Total amount withdrawn from the deposit."""
    averageTradeLengthInMilliseconds: Optional[float]
    """Average trade length (time from open to close) in milliseconds."""
    bestTrade: Optional[float]
    """The best profit from one trade that has ever been on the account."""
    worstTrade: Optional[float]
    """The worst profit from one trade that has ever been on the account."""
    bestTradePips: Optional[float]
    """The best pips from one trade that has ever been on the account."""
    worstTradePips: Optional[float]
    """The worst pips from one trade that has ever been on the account."""
    bestTradeDate: Optional[str]
    """Date of the best profit from one trade that have ever been on the account, in broker timezone,
    YYYY-MM-DD HH:mm:ss.SSS format."""
    bestTradePipsDate: Optional[str]
    """Date of the best pips from one trade that have ever been on the account, in broker timezone,
    YYYY-MM-DD HH:mm:ss.SSS format."""
    worstTradeDate: Optional[str]
    """Date of the worst profit from one trade that have ever been on the account, in broker timezone,
    YYYY-MM-DD HH:mm:ss.SSS format."""
    worstTradePipsDate: Optional[str]
    """Date of the worst pips from one trade that have ever been on the account, in broker timezone,
    YYYY-MM-DD HH:mm:ss.SSS format."""
    cagr: Optional[float]
    """Compound annual growth rate."""
    commissions: Optional[float]
    """Commissions charged by the broker for the entire period."""
    dailyGain: Optional[float]
    """Compound daily rate of return."""
    monthlyGain: Optional[float]
    """Compound monthly rate of return."""
    equityPercent: Optional[float]
    """Percentage of current equity to balance."""
    expectancy: Optional[float]
    """The average expected profitability of one trade in basic currency."""
    expectancyPips: Optional[float]
    """The average expected profitability of one trade in pips."""
    gain: Optional[float]
    """Time-weighted rate of return."""
    geometricHoldingPeriodReturn: Optional[float]
    """Geometric holding period return."""
    interest: Optional[float]
    """Cumulative interest and swap for the entire period."""
    longTrades: Optional[int]
    """The number of long trades."""
    shortTrades: Optional[int]
    """The number of long trades."""
    longWonTrades: Optional[int]
    """The number of long winning trades."""
    shortWonTrades: Optional[int]
    """The number of short winning trades."""
    longWonTradesPercent: Optional[float]
    """Percentage of long winning trades."""
    shortWonTradesPercent: Optional[float]
    """Percentage of short winning trades."""
    maxDrawdown: Optional[float]
    """Percentage of maximum drawdown of balance during the entire trading history."""
    mar: Optional[float]
    """Mar ratio."""
    lots: Optional[float]
    """Total volume of trades."""
    pips: Optional[float]
    """Cumulative price units."""
    profit: float
    """The total yield of closed positions for the entire period (total result)."""
    deposits: float
    """Cumulative deposit for the entire period."""
    absoluteGain: Optional[float]
    """Simple deposit increase without regard to reinvestment."""
    profitFactor: Optional[float]
    """The amount yielded by winning trades divided by the amount of losses yielded by losing trades. Result in range
    0 - Infinity means: `0` - only loss, `1` - profit equals to loss, `Infinity` - only profit."""
    sharpeRatio: Optional[float]
    """Average return earned in excess of the risk-free rate per unit of volatility. It is calculated if there are at
    least 30 closed deals in the history."""
    sortinoRatio: Optional[float]
    """Differentiates harmful volatility from total overall volatility. It is calculated if there are at least 30
    closed deals in the history."""
    standardDeviationProfit: Optional[float]
    """Statistical measure of volatility shows how much variation or dispersion. It is calculated if there are at
    least 30 closed deals in the history."""
    kurtosisProfit: Optional[float]
    """A statistical measure that is used to describe profit distribution. It is calculated if there are at least
    30 closed deals in the history."""
    averageHoldingPeriodReturn: Optional[float]
    """Average holding period return. It is calculated if there are at least 30 closed deals in the history."""
    averageWin: Optional[float]
    """Average win in basic currency."""
    averageWinPips: Optional[float]
    """Average win in pips."""
    averageLoss: Optional[float]
    """Average loss in basic currency."""
    averageLossPips: Optional[float]
    """Average loss in pips."""
    wonTradesPercent: Optional[float]
    """Percentage of winning trades."""
    lostTradesPercent: Optional[float]
    """Percentage of losing trades."""
    zScore: Optional[float]
    """Ability of a trading system to generate wins and losses in streaks. It is calculated if there are at least 30
    closed deals in the history."""
    probability: Optional[float]
    """Probability that a profit will be followed by a profit and a loss by a loss."""
    daysSinceTradingStarted: Optional[float]
    """The number of days that have passed since the opening of the first trade"""
    currencySummary: Optional[List[CurrencySummaryMetrics]]
    """Currency trading summary."""
    dailyGrowth: Optional[List[DailyGrowthMetrics]]
    """Daily gain shows the change in account profitability on trading days."""
    monthlyAnalytics: Optional[List[MonthlyAnalyticsMetrics]]
    """Monthly analysis of trading on this account."""
    closeTradesByWeekDay: Optional[List[TradeByTimeMetrics]]
    """Closing deals by days of the week."""
    openTradesByHour: Optional[List[TradeByTimeMetrics]]
    """Opening deals by hour of the day."""
    periods: Optional[Periods]
    """Trading stats for a few periods compared to the results for the previous period."""
    riskOfRuin: Optional[List[RiskOfRuinMetrics]]
    """Risk of ruin of balance."""
    tradeDuration: Optional[TradeDurationMetrics]
    """Metrics for each duration of trades."""
    tradeDurationDiagram: Optional[List[TradeDurationDiagramColumnMetrics]]
    """List of information columns about the duration of trades for the diagram."""


class Trade(TypedDict):
    """Historical trade."""
    _id: str
    """Historical trade id."""
    accountId: str
    """MetaApi account id."""
    volume: float
    """Trade volume."""
    durationInMinutes: float
    """Trade duration in minutes."""
    profit: float
    """Trade profit."""
    gain: float
    """Trade gain."""
    success: str
    """Trade success."""
    openTime: str
    """Time the trade was opened at in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    type: str
    """Trade type"""
    symbol: Optional[str]
    """Symbol the trade relates to."""
    closeTime: Optional[str]
    """Time the trade was closed at in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    openPrice: Optional[float]
    """Trade opening price."""
    closePrice: Optional[float]
    """Trade closing price."""
    pips: Optional[float]
    """The number of pips earned (positive) or lost (negative) in this trade."""


class OpenTrade(TypedDict):
    """Open trade."""
    _id: str
    """Historical trade id."""
    accountId: str
    """MetaApi account id."""
    volume: float
    """Trade volume."""
    durationInMinutes: float
    """Trade duration in minutes."""
    profit: float
    """Trade profit."""
    gain: float
    """Trade gain."""
    success: str
    """Trade success."""
    openTime: str
    """Time the trade was opened at in broker timezone, YYYY-MM-DD HH:mm:ss.SSS format."""
    type: str
    """Trade type"""
    symbol: Optional[str]
    """Symbol the trade relates to."""
    openPrice: Optional[float]
    """Trade opening price."""
    pips: Optional[float]
    """The number of pips earned (positive) or lost (negative) in this trade."""
