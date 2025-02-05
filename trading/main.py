import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from bot import GMXBot

# Load environment variables
load_dotenv()

async def main():
    # Get bot token from environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("No bot token found in environment variables")

    # Initialize bot
    bot = GMXBot()
    app = Application.builder().token(bot_token).build()
    
    # Register command handlers
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("positions", bot.positions))
    app.add_handler(CommandHandler("open_position", bot.start_open_position))
    app.add_handler(CommandHandler("size", bot.set_position_size))
    app.add_handler(CommandHandler("collateral", bot.set_collateral))
    
    # Register callback handler
    app.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # Start bot
    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")