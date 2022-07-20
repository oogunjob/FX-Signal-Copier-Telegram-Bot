# FX Signal Copier Telegram Bot 💻💸

This Telegram bot allow users to enter trades directly from Telegram and get a detailed look at risk to reward ratio with profit, loss, and calculated lot size. You are able to change specific settings such as allowed symbols, risk factor, and more from your personalized Python script and enviornement variables.

The FX Signal Copier Telegram Bot makes use of the MetaAPI cloud forex trading API for MetaTrader 4 and MetaTrader 5 to create a connection to a user's MetaTrader account in order to gather information such as account balance, open positions and permissions to enter and close trades.

Official REST and websocket API documentation for MetaAPI: https://metaapi.cloud/docs/client/

This bot is deployed using Heroku.

# Demonstration

YouTube Video Showing Demonstration Will Be Coming Soon

# Installation ⚒️

Prerequisites:

- Python 3 or higher (https://www.python.org/downloads/)
- Git (https://git-scm.com/downloads)
- MetaAPI Account (https://app.metaapi.cloud/sign-up)
- Heroku Account (https://signup.heroku.com/)
- Heroku CLI 

**(For Window Users: it is recommended to use Git Bash terminal for installation)**

1. Create or open a folder on your local machine and create a Python Virtual Environment
```bash
mkdir telegram_bot
cd telegram_bot
python3 -m venv fx_telegram_bot
```

2. Activate virtual enviornment
```bash
Linux/MacOS: source fx_telegram_bot/bin/activate
Windows: source fx_telegram_bot/Scripts/activate
```


