import os
import json
import requests
import openai  # Used to process natural language commands via an AI model
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ------------------------------
# Configuration and Setup
# ------------------------------

# Environment variables for secure tokens/keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BUNGEE_API_BASE = "https://api.bungee.exchange"  # Adjust if needed

# Setup OpenAI API key
openai.api_key = OPENAI_API_KEY

# A simple in-memory storage for pending transactions per user (for demo purposes)
pending_transactions = {}

# ------------------------------
# NLP Processing using OpenAI
# ------------------------------

def parse_command_nlp(text: str):
    """
    Use OpenAI's language model to parse the user's command.
    The prompt instructs the model to extract:
    - action (transfer/migrate)
    - amount
    - token symbol
    - source chain
    - target chain
    
    Returns a dictionary with these details or None if parsing fails.
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
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or another model of your choice
            messages=[{"role": "user", "content": prompt}],
            temperature=0  # for deterministic output
        )
        content = response["choices"][0]["message"]["content"]
        # Attempt to parse the JSON response.
        parsed = json.loads(content)
        # Basic validation: ensure all keys are present
        if all(key in parsed for key in ["action", "amount", "token", "from_chain", "to_chain"]):
            return parsed
    except Exception as e:
        print(f"Error parsing command via NLP: {e}")
    return None

# ------------------------------
# Bungee API Integration Functions
# ------------------------------

def get_quote(from_chain, to_chain, token, amount):
    """
    Retrieve a quote for the cross-chain migration.
    This uses the QuoteController_getQuote endpoint (see :contentReference[oaicite:0]{index=0}).
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
    Ensure that route_data has been reviewed by the user before calling.
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
# Telegram Bot Handlers with Safety Checks
# ------------------------------

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to the AI Cross-Chain Migration Assistant!\n\n"
        "Send a command like: 'Transfer 100 DAI from Ethereum to Binance Smart Chain'.\n"
        "I will preview the transaction before execution."
    )

def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    # Process the command using the NLP AI instead of regex.
    command_data = parse_command_nlp(text)
    if not command_data:
        update.message.reply_text("Sorry, I couldn't understand that command. Please try again with a clearer instruction.")
        return

    # Call Bungee API to get a quote for the migration.
    quote = get_quote(command_data["from_chain"], command_data["to_chain"],
                      command_data["token"], command_data["amount"])
    if not quote:
        update.message.reply_text("Failed to retrieve a quote. Please verify your command details and try again.")
        return

    # Build a preview message summarizing the intended migration.
    preview_message = (
        f"**Transaction Preview**\n"
        f"Action: {command_data['action'].capitalize()}\n"
        f"Amount: {command_data['amount']} {command_data['token']}\n"
        f"From: {command_data['from_chain']}\n"
        f"To: {command_data['to_chain']}\n\n"
        f"**Quote Details:**\n{json.dumps(quote, indent=2)}\n\n"
        "Please review these details carefully. "
        "If everything looks correct, press Confirm to proceed or Cancel to abort."
    )

    # Save pending transaction details for later confirmation.
    pending_transactions[user_id] = {
        "command_data": command_data,
        "quote": quote
    }

    # Provide inline keyboard buttons for user confirmation.
    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data="confirm"),
            InlineKeyboardButton("Cancel", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(preview_message, reply_markup=reply_markup, parse_mode="Markdown")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()

    if user_id not in pending_transactions:
        query.edit_message_text("No pending transaction found. Please start over.")
        return

    if query.data == "cancel":
        # Remove the pending transaction
        pending_transactions.pop(user_id, None)
        query.edit_message_text("Transaction cancelled.")
    elif query.data == "confirm":
        # Retrieve stored details
        pending = pending_transactions.pop(user_id)
        # For added safety, you might re-check the quote details here.
        route_response = start_migration(pending["quote"])
        if route_response:
            query.edit_message_text(f"Migration started successfully:\n{json.dumps(route_response, indent=2)}")
        else:
            query.edit_message_text("Failed to start migration. Please try again later.")

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers for commands and messages.
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    updater.start_polling()
    print("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()
