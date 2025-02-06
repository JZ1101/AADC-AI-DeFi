import os
from deepseek import DeepSeekAPI
from web3 import Web3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from dotenv import load_dotenv
from packages.wallet import create_wallet, import_wallet, get_wallet_balance
from packages.nlp import parse_command_nlp
from packages.bungee import get_quote, CHAIN_IDS, get_token_address, execute_transaction

# ------------------------------
# Configuration and Setup
# ------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
WEB3_PROVIDER = os.getenv("WEB3_PROVIDER", "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID")
BUNGEE_API_KEY = os.getenv("BUNGEE_API_KEY")
# Set the base URL for the Socket (Bungee) API v2
BASE_URL = "https://api.socket.tech/v2"

# Set up DeepSeek and Web3 providers
deepseek_client = DeepSeekAPI(DEEPSEEK_API_KEY)
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# In-memory storage for user wallets and pending transactions (use a secure database in production)
user_wallets = {}         # key: Telegram user_id, value: wallet dict {address, private_key}
pending_transactions = {} # key: Telegram user_id, value: transaction details

# ------------------------------
# Telegram Bot Handlers (same as original)
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the AI Cross-Chain Migration Assistant with Wallet Integration!\n\n"
        "You can manage an EVM-compatible wallet directly here.\n"
        "Commands:\n"
        "/createwallet - Create a new wallet\n"
        "/importwallet <private_key> - Import an existing wallet\n"
        "/wallet - Show your wallet details and balance\n\n"
        "To migrate assets, send a command like: 'Transfer 100 USDC from Ethereum to Binance Smart Chain'."
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

    # Process command with NLP
    command_data = parse_command_nlp(text)
    if not command_data:
        await update.message.reply_text("❌ Couldn't understand command. Try: 'Transfer 100 USDC from Ethereum to Binance Smart Chain'")
        return

    # Extract command data
    from_chain_name = command_data.get("from_chain")
    to_chain_name = command_data.get("to_chain")
    from_token_symbol = command_data.get("from_token")
    to_token_symbol = command_data.get("to_token")
    amount = command_data.get("amount")

    # Validate chain names
    from_chain_id = CHAIN_IDS.get(from_chain_name)
    to_chain_id = CHAIN_IDS.get(to_chain_name)
    if not from_chain_id or not to_chain_id:
        await update.message.reply_text("❌ Invalid chain name. Supported chains: Ethereum, Binance Smart Chain, Polygon, Avalanche, Arbitrum, Optimism, Base.")
        return

    # Fetch token addresses from the registry
    try:
        from_token_address = get_token_address(from_chain_id, from_token_symbol)
        to_token_address = get_token_address(to_chain_id, to_token_symbol)
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return

    # Get user wallet address
    user_wallet = user_wallets.get(user_id, {}).get("address")
    if not user_wallet:
        await update.message.reply_text("⚠️ Please create/import a wallet first!")
        return

    print(f"Migration request: {from_chain_name} -> {to_chain_name} | {amount} {from_token_symbol} -> {to_token_symbol}")
    print(f"From Token Address: {from_token_address}")
    print(f"To Token Address: {to_token_address}")
    print(f"User Wallet: {user_wallet}")
    print(f"Command Data: {command_data}")

    # Get Bungee quote
    try:
        quote = get_quote(
            from_chain_id=from_chain_id,
            from_token_address=from_token_address,
            to_chain_id=to_chain_id,
            to_token_address=to_token_address,
            from_amount=amount,
            user_address=user_wallet,
            unique_routes_per_bridge=True,
            sort="output",
            single_tx_only=True
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to get migration quote: {str(e)}")
        return

    if not quote.get("result", {}).get("routes"):
        await update.message.reply_text("❌ No routes available for the provided parameters.")
        return

    # Build a preview message
    preview_message = (
        f"🚀 Cross-Chain Transfer Preview:\n"
        f"• From: {from_chain_name} (Chain ID: {from_chain_id})\n"
        f"• To: {to_chain_name} (Chain ID: {to_chain_id})\n"
        f"• Amount: {amount} {from_token_symbol}\n"
        f"• From Token Address: {from_token_address}\n"
        f"• To Token Address: {to_token_address}\n\n"
        "Confirm to proceed with this transaction."
    )

    # Save pending transaction details
    pending_transactions[user_id] = {
        "quote": quote,
        "wallet": user_wallet,
        "command_data": command_data
    }

    # Confirmation buttons
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    ]]
    await update.message.reply_text(
        preview_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in pending_transactions:
        await query.edit_message_text("⚠️ Transaction expired. Please start over.")
        return

    if query.data == "cancel":
        pending_transactions.pop(user_id)
        await query.edit_message_text("❌ Transaction cancelled.")
        return

    # Execute the transaction
    pending = pending_transactions.pop(user_id)
    private_key = user_wallets[user_id]["private_key"]
    route = pending["quote"]["result"]["routes"][0]

    try:
        tx_hash = await execute_transaction(user_id, route, private_key, user_wallets)
        message = (
            f"✅ Transaction submitted successfully!\n"
            f"Hash: {tx_hash}\n"
            f"Track on: https://explorer.bungee.exchange/tx/{tx_hash}"
        )
    except Exception as e:
        message = f"❌ Transaction failed: {str(e)}"

    await query.edit_message_text(message)

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
    
    # Run the bot until interrupted
    application.run_polling()

if __name__ == "__main__":
    main()
