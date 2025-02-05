import os
import json
import requests
from deepseek import DeepSeekAPI
from web3 import Web3, Account
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ContextTypes, filters)
from dotenv import load_dotenv

# ------------------------------
# Configuration and Setup
# ------------------------------

load_dotenv()

# Environment variables for secure tokens/keys and provider endpoint
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
WEB3_PROVIDER = os.getenv("WEB3_PROVIDER", "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID")
BUNGEE_API_BASE = "https://api.bungee.exchange"

# Set up OpenAI and Web3 providers
deepseek_client = DeepSeekAPI(DEEPSEEK_API_KEY)
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# In-memory storage for user wallets and pending transactions (use a secure database in production)
user_wallets = {}         # key: Telegram user_id, value: wallet dict {address, private_key}
pending_transactions = {} # key: Telegram user_id, value: transaction details

# ------------------------------
# Wallet Functionality
# ------------------------------

def create_wallet():
    """Generate a new EVM wallet and return the address and private key."""
    account = w3.eth.account.create()
    return account.address, w3.to_hex(account.key)

def import_wallet(private_key: str):
    """Import a wallet from a given private key. Returns the wallet address and validated private key."""
    try:
        account = Account.from_key(private_key)
        return account.address, account.privateKey.hex()
    except Exception as e:
        print(f"Error importing wallet: {e}")
        return None, None

def get_wallet_balance(address: str):
    """Retrieve the balance (in ETH) for the given address."""
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.fromWei(balance_wei, 'ether')
        return balance_eth
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None

# ------------------------------
# NLP Processing using OpenAI
# ------------------------------

import json
import re

def parse_command_nlp(text: str):
    """
    Use OpenAI's language model to parse the user's command.
    Expected keys: action, amount, token, from_chain, to_chain.
    """
    prompt = f"""
Extract the following information from the command below:
- action: either "transfer" or "migrate"
- amount: a numeric value
- token: the token symbol (e.g., DAI, USDC)
- from_chain: source blockchain name (e.g., Ethereum)
- to_chain: destination blockchain name (e.g., Binance Smart Chain)

Command: "{text}"
If any field is missing or ambiguous, return null.

Return the result as a JSON object with keys: action, amount, token, from_chain, to_chain.
"""
    try:
        # print(f"Processing NLP command: {text}")
        print(f"user balance: {deepseek_client.user_balance()}")
        response = deepseek_client.chat_completion(prompt=prompt)
        # print(f"NLP Response: {response}")
        
        # Extract the JSON part from the Markdown code block
        json_match = re.search(r'```json\s*({.*?})\s*```', response, re.DOTALL)
        if not json_match:
            print("No JSON found in the response.")
            return None
        
        # Get the JSON string
        json_str = json_match.group(1)
        
        # Parse the JSON string into a dictionary
        parsed = json.loads(json_str)
        
        # Check if all required keys are present
        if all(key in parsed for key in ["action", "amount", "token", "from_chain", "to_chain"]):
            return parsed
        else:
            print("Missing or ambiguous fields in the parsed response")
            return None
    except Exception as e:
        print(f"Error parsing command via NLP: {e}")
    return None

# ------------------------------
# Bungee API Integration Functions
# ------------------------------

def get_quote(from_chain, to_chain, token, amount):
    """
    Retrieve a quote for the cross-chain migration using the Bungee API.
    See the QuoteController_getQuote endpoint in the documentation.
    """
    url = f"{BUNGEE_API_BASE}/quote"
    params = {
        "fromChain": from_chain,
        "toChain": to_chain,
        "token": token,
        "amount": amount
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error calling Bungee API (get_quote): {e}")
        return None

def start_migration(route_data):
    """
    Initiate the migration using the ActiveRoutesController_startActiveRoute endpoint.
    Ensure that route_data has been reviewed by the user.
    """
    url = f"{BUNGEE_API_BASE}/activeRoute/start"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(route_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error starting migration: {e}")
        return None

# ------------------------------
# Telegram Bot Handlers
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the AI Cross-Chain Migration Assistant with Wallet Integration!\n\n"
        "You can manage an EVM-compatible wallet directly here.\n"
        "Commands:\n"
        "/createwallet - Create a new wallet\n"
        "/importwallet <private_key> - Import an existing wallet\n"
        "/wallet - Show your wallet details and balance\n\n"
        "To migrate assets, send a command like: 'Transfer 100 DAI from Ethereum to Binance Smart Chain'."
    )

async def create_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    address, private_key = create_wallet()
    user_wallets[user_id] = {"address": address, "private_key": private_key}
    await update.message.reply_text(
        f"New wallet created!\nAddress: {address}\nPrivate Key: {private_key}\n\n"
        "Keep your private key secure and do not share it with anyone."
    )

async def import_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Please provide your private key. Usage: /importwallet <private_key>")
        return
    private_key = args[0]
    address, valid_key = import_wallet(private_key)
    if address:
        user_wallets[user_id] = {"address": address, "private_key": valid_key}
        await update.message.reply_text(
            f"Wallet imported successfully!\nAddress: {address}\n"
            "Keep your private key secure and do not share it with anyone."
        )
    else:
        await update.message.reply_text("Failed to import wallet. Please check your private key and try again.")

async def wallet_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    wallet = user_wallets.get(user_id)
    if not wallet:
        await update.message.reply_text("No wallet found. Use /createwallet or /importwallet to set up your wallet.")
        return
    balance = get_wallet_balance(wallet["address"])
    await update.message.reply_text(
        f"Your Wallet Details:\nAddress: {wallet['address']}\nBalance: {balance} ETH"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # Process the cross-chain migration command using NLP.
    command_data = parse_command_nlp(text)
    if not command_data:
        await update.message.reply_text("Sorry, I couldn't understand that command. Please try again with a clearer instruction.")
        return

    # Retrieve a quote from the Bungee API.
    quote = get_quote(command_data["from_chain"], command_data["to_chain"],
                      command_data["token"], command_data["amount"])
    if not quote:
        await update.message.reply_text("Failed to retrieve a quote. Please verify your command details and try again.")
        return

    # Check if the user has a wallet and if it is funded (for demonstration, we check ETH balance).
    wallet = user_wallets.get(user_id)
    if not wallet:
        await update.message.reply_text("Please set up your wallet first using /createwallet or /importwallet.")
        return

    balance = get_wallet_balance(wallet["address"])
    if balance is None or balance <= 0:
        await update.message.reply_text("Your wallet balance is insufficient. Please deposit funds into your wallet first.")
        return

    # Build a transaction preview with details for safety confirmation.
    preview_message = (
        f"**Transaction Preview**\n"
        f"Action: {command_data['action'].capitalize()}\n"
        f"Amount: {command_data['amount']} {command_data['token']}\n"
        f"From: {command_data['from_chain']}\n"
        f"To: {command_data['to_chain']}\n\n"
        f"Your Wallet Address: {wallet['address']}\n"
        f"Wallet Balance: {balance} ETH\n\n"
        f"**Quote Details:**\n{json.dumps(quote, indent=2)}\n\n"
        "Please review these details carefully. "
        "Press Confirm to proceed or Cancel to abort."
    )

    # Save the pending transaction details for this user.
    pending_transactions[user_id] = {
        "command_data": command_data,
        "quote": quote,
        "wallet": wallet
    }

    # Inline keyboard for confirmation.
    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data="confirm"),
         InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(preview_message, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in pending_transactions:
        await query.edit_message_text("No pending transaction found. Please start over.")
        return

    if query.data == "cancel":
        pending_transactions.pop(user_id, None)
        await query.edit_message_text("Transaction cancelled.")
    elif query.data == "confirm":
        pending = pending_transactions.pop(user_id)
        # Optionally, re-check the wallet balance or add further safety checks here.
        route_response = start_migration(pending["quote"])
        if route_response:
            await query.edit_message_text(f"Migration started successfully:\n{json.dumps(route_response, indent=2)}")
        else:
            await query.edit_message_text("Failed to start migration. Please try again later.")

# ------------------------------
# Main Entry Point
# ------------------------------

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Wallet management commands.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("createwallet", create_wallet_handler))
    application.add_handler(CommandHandler("importwallet", import_wallet_handler))
    application.add_handler(CommandHandler("wallet", wallet_details_handler))
    
    # Cross-chain migration command.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
