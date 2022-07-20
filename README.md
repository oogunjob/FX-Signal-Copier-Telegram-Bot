# FX Signal Copier Telegram Bot 💻💸

This Telegram bot allow users to enter trades directly from Telegram and get a detailed look at risk to reward ratio with profit, loss, and calculated lot size. You are able to change specific settings such as allowed symbols, risk factor, and more from your personalized Python script and enviornement variables.

The FX Signal Copier Telegram Bot makes use of the MetaAPI cloud forex trading API for MetaTrader 4 and MetaTrader 5 to create a connection to a user's MetaTrader account in order to gather information such as account balance, open positions and permissions to enter and close trades.

Official REST and websocket API documentation for MetaAPI: https://metaapi.cloud/docs/client/

This bot is deployed using Heroku.

# Demonstration

YouTube Video Showing Demonstration Will Be Coming Soon

# Installation ⚒️

Prerequisites:
- Telegram Account 
- Python 3 or higher (https://www.python.org/downloads/)
- Git (https://git-scm.com/downloads)
- MetaAPI Account (https://app.metaapi.cloud/sign-up)
- Heroku Account (https://signup.heroku.com/)
- Heroku CLI (https://devcenter.heroku.com/articles/heroku-cli#pre-requisites)

**(For Window Users: It is recommended to use a Git Bash terminal for installation)**

**1. Create a Telegram Bot**

Start a conversation with @BotFather on Telegram and create a new bot with a unique name. Save the given API token.

**2. Create or open a folder on your local machine and create a Python Virtual Environment**
```bash
mkdir telegram_bot
cd telegram_bot
python3 -m venv fx_telegram_bot
```

**3. Activate virtual enviornment**
```bash
Linux/MacOS: source fx_telegram_bot/bin/activate
Windows: source fx_telegram_bot/Scripts/activate
```

**4. Install pip packages**
```bash
pip install metaapi_cloud_sdk prettytable python-telegram-bot
```

**5. Clone FX Signal Copier Telegram Bot to enviornment**
```bash
git clone https://github.com/oogunjob/FX-Signal-Copier-Telegram-Bot.git
```

**6. Set Up Heroku App**

Navigate to Heroku web app and create a new application with a unique name. Upon creation, go to app settings and navigate to **Config Vars**. Add the following enviornment variables (case-sensitive) for key and value excluding quotes.

|Key  | Value |
| ------------- | ------------- |
| TOKEN  | "INSERT TELEGRAM BOT API TOKEN HERE"  |
| APP_NAME  | "https://[INSERT NAME OF APP HERE].herokuapp.com/"  |
| TELEGRAM_USER  | "INSERT TELEGRAM USERNAME HERE"  |
| API_KEY  | "INSERT META API TOKEN HERE (https://app.metaapi.cloud/token)"  |
| ACCOUNT_ID  | "INSERT META API ACCOUNT ID HERE"  |
| RISK_FACTOR  | "INSERT PERCENTAGE OF RISK PER TRADE HERE IN DECIMAL FORM, ex: 5% = 0.05"  |

**6. Deploy Heroku App**

Return to terminal and log in to Heroku app to initialize repository and deploy.
```bash
heroku login
git init
heroku git:remote -a "INSERT NAME OF APP HERE"
git commit -am "first deployment"
git push heroku master
```

**Congratulations!** 🥳 If you followed these steps correctly, you should now be able to open a conversation with your bot on Telegram and calculate trade risks along with placing trades. For help on how to use the bot, send the /help command for bot instructions and example trades.
