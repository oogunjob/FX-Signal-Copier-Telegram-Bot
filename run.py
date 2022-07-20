#!/usr/bin/env python3
import asyncio
import logging
import math
import os

from metaapi_cloud_sdk import MetaApi
from prettytable import PrettyTable
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

# MetaAPI Credentials
API_KEY = os.environ.get("API_KEY")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")

# Telegram Credentials
TOKEN = os.environ.get("TOKEN")
TELEGRAM_USER = os.environ.get("TELEGRAM_USER")

# Heroku Credentials
APP_NAME = os.environ.get("APP_NAME")

# Port number for Telegram bot web hook
PORT = int(os.environ.get('PORT', '8443'))


# Enables logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# allowed FX symbols
SYMBOLS = ['USDCAD', 'EURJPY', 'EURUSD', 'GBPCAD', 'GBPCHF', 'EURCHF', 'USDCHF', 'EURGBP', 'GBPUSD', 'AUDCAD', 'CADCHF', 'NZDJPY', 'NZDUSD', 'NZDCAD', 'GBPCHF', 'AUDUSD', 'GBPJPY', 'USDJPY', 'CHFJPY', 'CADJPY', 'EURCAD', 'AUDJPY', 'EURAUD', 'AUDNZD', 'XAUUSD', 'XAGUSD', 'EURNZD', 'NOW']

# RISK FACTOR
RISK_FACTOR = float(os.environ.get("RISK_FACTOR"))


def ParseSignal(signal: str) -> dict:
    """Starts process of parsing signal and entering trade on MT4 account.

    Args:
        signal: trading signal

    Returns:
        a dictionary that contains trade signal information
    """

    # converts message to list of strings for parsing
    signal = signal.splitlines()
    signal = [line.rstrip() for line in signal]

    trade = {}

    # determines the order type of the trade
    if('Buy Limit'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Buy Limit'

    elif('Sell Limit'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Sell Limit'

    elif('Buy Stop'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Buy Stop'

    elif('Sell Stop'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Sell Stop'

    elif('Buy'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Buy'
    
    elif('Sell'.lower() in signal[0].lower()):
        trade['OrderType'] = 'Sell'
    
    # returns an empty dictionary if an invalid order type was given
    else:
        return {}

    # extracts symbol from trade signal
    trade['Symbol'] = (signal[0].split())[-1].upper()
    
    # checks if the symbol is valid, if not, returns an empty dictionary
    if(trade['Symbol'] not in SYMBOLS):
        return {}
    
    # checks wheter or not to convert entry to float because of market exectution option ("NOW")
    if(trade['OrderType'] == 'Buy' or trade['OrderType'] == 'Sell'):
        trade['Entry'] = (signal[1].split())[-1]
    
    else:
        trade['Entry'] = float((signal[1].split())[-1])
    
    trade['StopLoss'] = float((signal[2].split())[-1])
    trade['TP'] = [float((signal[3].split())[-1])]

    # checks if there's a fourth line and parses it for TP2
    if(len(signal) > 4):
        trade['TP'].append(float(signal[4].split()[-1]))
    
    # adds risk factor to trade
    trade['RiskFactor'] = RISK_FACTOR

    return trade


def GetTradeInformation(update: Update, trade: dict, balance: float) -> None:
    """Calculates information from given trade including stop loss and take profit in pips, posiition size, and potential loss/profit.

    Args:
        update: update from Telegram
        trade: dictionary that stores trade information
        balance: current balance of the MT4 account
    """

    # calculates the stop loss in pips
    if(str(trade['Entry']).index('.') >= 3):
        multiplier = 0.01
    else:
        multiplier = 0.0001

    # calculates the stop loss in pips
    stopLossPips = abs(round((trade['StopLoss'] - trade['Entry']) / multiplier))

    # calculates the position size using stop loss and RISK FACTOR
    trade['PositionSize'] = math.floor(((balance * trade['RiskFactor']) / stopLossPips) / 10 * 100) / 100

    # calculates the take profit(s) in pips
    takeProfitPips = []
    for takeProfit in trade['TP']:
        takeProfitPips.append(abs(round((takeProfit - trade['Entry']) / multiplier)))

    # creates table with trade information
    table = CreateTable(trade, balance, stopLossPips, takeProfitPips)
    
    # sends user trade information and calcualted risk
    update.effective_message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)

    return


def CreateTable(trade: dict, balance: float, stopLossPips: int, takeProfitPips: int) -> PrettyTable:
    """Creates PrettyTable object to display trade information to user.

    Args:
        trade: dictionary that stores trade information
        balance: current balance of the MT4 account
        stopLossPips: the difference in pips from stop loss price to entry price

    Returns:
        a Pretty Table object that contains trade information
    """

    # creates prettytable object
    table = PrettyTable()
    
    table.title = 'Trade Information'
    table.field_names = ["Key", "Value"]
    table.align["Key"] = "l"  
    table.align["Value"] = "r" 

    table.add_row(['{} Limit'.format(trade['OrderType']) , trade['Symbol']])
    table.add_row(['Entry\n', trade['Entry']])

    table.add_row(['Stop Loss', '{} pips'.format(stopLossPips)])

    for count, takeProfit in enumerate(takeProfitPips):
        table.add_row([f'Take Profit {count + 1}', f'{takeProfit} pips'])

    table.add_row(['\nRisk Factor', '\n{:,.0f} %'.format(trade['RiskFactor'] * 100)])
    table.add_row(['Position Size', trade['PositionSize']])
    
    table.add_row(['\nCurrent Balance', '\n$ {:,.2f}'.format(balance)])
    table.add_row(['Potential Loss', '$ {:,.2f}'.format(round((trade['PositionSize'] * 10) * stopLossPips, 2))])

    # total potential profit from trade
    totalProfit = 0

    for count, takeProfit in enumerate(takeProfitPips):
        profit = round((trade['PositionSize'] * 10 * (1 / len(takeProfitPips))) * takeProfit, 2)
        table.add_row([f'Potential Profit {count + 1}', '$ {:,.2f}'.format(profit)])
        
        # sums potential profit from each take profit target
        totalProfit += profit

    table.add_row(['\nTotal Profit', '\n$ {:,.2f}'.format(totalProfit)])

    return table


async def ConnectMT4(update: Update, trade: dict):
    """Attempts connection to MetaAPI and MT4 to place trade.

    Args:
        update: update from Telegram
        trade: dictionary that stores trade information

    Returns:
        A coroutine that confirms that the connection to MetaAPI/MT4 and trade placement were successful
    """

    # creates connection to MetaAPI
    api = MetaApi(API_KEY)
    
    try:
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        initial_state = account.state
        deployed_states = ['DEPLOYING', 'DEPLOYED']

        if initial_state not in deployed_states:
            #  wait until account is deployed and connected to broker
            logger.info('Deploying account')
            await account.deploy()

        logger.info('Waiting for API server to connect to broker ...')
        await account.wait_connected()

        # connect to MetaApi API
        connection = account.get_rpc_connection()
        await connection.connect()

        # wait until terminal state synchronized to the local state
        logger.info('Waiting for SDK to synchronize to terminal state ...')
        await connection.wait_synchronized()

        # obtains account information from MT4 server
        account_information = await connection.get_account_information()

        update.effective_message.reply_text("Successfully connected to MT4!\nCalculating trade risk ... 🤔")

        # checks if the order is a market execution to get the current price of symbol
        if(trade['Entry'] == 'NOW'):
            price = await connection.get_symbol_price(symbol=trade['Symbol'])

            # uses bid price if the order type is a buy
            if(trade['OrderType'] == 'Buy'):
                trade['Entry'] = float(price['bid'])

            # uses ask price if the order type is a sell
            if(trade['OrderType'] == 'Sell'):
                trade['Entry'] = float(price['ask'])

        # produces a table with trade information
        GetTradeInformation(update, trade, account_information['balance'])

        # enters trade on to MT4 account
        update.effective_message.reply_text("Entering trade on MT4 Account ... 👨🏾‍💻")
            
        try:
            # executes buy market execution order
            if(trade['OrderType'] == 'Buy'):
                for takeProfit in trade['TP']:
                    result = await connection.create_market_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)

            # executes buy limit order
            elif(trade['OrderType'] == 'Buy Limit'):
                for takeProfit in trade['TP']:
                    result = await connection.create_limit_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

            # executes buy stop order
            elif(trade['OrderType'] == 'Buy Stop'):
                for takeProfit in trade['TP']:
                    result = await connection.create_stop_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

            # executes sell market execution order
            elif(trade['OrderType'] == 'Sell'):
                for takeProfit in trade['TP']:
                    result = await connection.create_market_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)

            # executes sell limit order
            elif(trade['OrderType'] == 'Sell Limit'):
                for takeProfit in trade['TP']:
                    result = await connection.create_limit_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

            # executes sell stop order
            elif(trade['OrderType'] == 'Sell Stop'):
                for takeProfit in trade['TP']:
                    result = await connection.create_stop_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)
            
            # sends success message to user
            update.effective_message.reply_text("Trade entered successfully! 💰")
            
            # prints success message to console
            logger.info('\nTrade entered successfully!')
            logger.info('Result Code: {}\n'.format(result['stringCode']))
        
        except Exception as error:
            logger.info(f"\nTrade failed with error: {error}\n")
            update.effective_message.reply_text(f"There was an issue 😕\n\nError Message:\n{error}")
    
    except Exception as error:
        logger.error(f'Error: {error}')
        update.effective_message.reply_text(f"There was an issue with the connection 😕\n\nError Message:\n{error}")
    
    return


def welcome(update: Update, context) -> None:
    """Sends welcome message to user.

    Args:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    welcome_message = "Welcome to the FX Signal Copier Telegram Bot! 💻💸\n\nYou can use this bot to enter trades directly from Telegram and get a detailed look at your risk to reward ratio with profit, loss, and calculated lot size. You are able to change specific settings such as allowed symbols, risk factor, and more from your personalized Python script.\n\nUse the /help command to view example trades."
    
    # sends messages to user
    update.effective_message.reply_text(welcome_message)

    return


def start(update: Update, context) -> None:
    """Starts process of parsing signal and entering trade on MT4 account.

    Args:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    # validates that the user is correct
    if(not(update.effective_message.chat.username == TELEGRAM_USER)):
        update.effective_message.reply_text("You are not authorized to use this bot! 🙅🏽‍♂️")
        return

    try: 
        # parses signal from Telegram message
        trade = ParseSignal(update.effective_message.text)
        
        # checks if there was an issue with parsing the trade
        if(not(trade)):
            raise Exception('Invalid Trade')

        update.effective_message.reply_text("Trade Successfully Parsed! 🥳\nConnecting to MT4 ... (May take a while) ⏰")

        # attempts connection to MT4 and places trade
        asyncio.run(ConnectMT4(update, trade))
    
    except Exception as error:
        logger.error(f'Error: {error}')
        errorMessage = f"There was an error parsing this trade 😕\n\nError: {error}\n\nPlease re-enter trade with this format:\n\nBUY/SELL SYMBOL\nEntry \nSL \nTP "
        update.effective_message.reply_text(errorMessage)

    return


def help(update: Update, context) -> None:
    """Sends a help message when the command /help is issued

    Args:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    help_message = "This bot is used to automatically enter trades onto your MT4 account directly from Telegram. To begin, ensure that you are authorized to use this bot by adjusting your Python script or enviornment variables. You can then proceed by entering a trade.\n\nThis bot support all trade order types (Market Execution, Limit, and Stop)\n\nAfter an extended period away from the bot, please be sure to re-enter the start command to restart the connection to your MT4 account."
    trade_example = "Example Trades 💴:\n\n"
    market_execution_example = "Market Execution:\nBUY GBPUSD\nEntry NOW\nSL 1.14336\nTP 1.28930\nTP 1.29845\n\n"
    limit_example = "Limit Execution:\nBUY LIMIT GBPUSD\nEntry 1.14480\nSL 1.14336\nTP 1.28930\n\n"
    note = "You are able to enter up to two take profits. If two are entered, both trades will use half of the position size, and one will use TP1 while the other uses TP2.\n\nNote: Use 'NOW' as the entry to enter a market execution trade."

    # sends messages to user
    update.effective_message.reply_text(help_message)
    update.effective_message.reply_text(trade_example + market_execution_example + limit_example + note)

    return


def error(update: Update, context) -> None:
    """Logs Errors caused by updates.

    Args:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """

    logger.warning('Update "%s" caused error "%s"', update, context.error)

    return


def main() -> None:
    """Runs the Telegram bot."""

    updater = Updater(TOKEN, use_context=True)

    # get the dispatcher to register handlers
    dp = updater.dispatcher

    # message handler
    dp.add_handler(CommandHandler("start", welcome))

    # help command handler
    dp.add_handler(CommandHandler("help", help))

    # message handler
    dp.add_handler(MessageHandler(Filters.text, start))

    # log all errors
    dp.add_error_handler(error)
    
    # listens for incoming updates
    updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN, webhook_url=APP_NAME + TOKEN)
    updater.idle()

    return


if __name__ == '__main__':
    main()
