
import os
import time
from decimal import Decimal
import asyncio
from deepseek import DeepSeekAPI
from web3 import Web3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from yield_farming.AvaYieldInteractor import AvaYieldInteractor
from dotenv import load_dotenv
from packages.wallet import create_wallet, import_wallet, get_wallet_balance
from packages.nlp import parse_command_nlp
from packages.bungee import get_quote, CHAIN_IDS, get_token_address, execute_transaction

# ------------------------------
# Configuration and Setup
# ------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
WEB3_PROVIDER = os.getenv("WEB3_PROVIDER", "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID")
BUNGEE_API_KEY = os.getenv("BUNGEE_API_KEY")
# Set the base URL for the Socket (Bungee) API v2
BASE_URL = "https://api.socket.tech/v2"

# Set up DeepSeek and Web3 providers
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
    
    action = command_data.get("action")
    if action == "cross_chain_send&transfer":
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

        # Extract the first route from the quote
        route = quote["result"]["routes"][0]
        used_bridge_names = route.get("usedBridgeNames", [])
        bridge_names = ", ".join(used_bridge_names) if used_bridge_names else "N/A"

        # Build a preview message
        preview_message = (
            f"🚀 Cross-Chain Transfer Preview:\n"
            f"• From: {from_chain_name} (Chain ID: {from_chain_id})\n"
            f"• To: {to_chain_name} (Chain ID: {to_chain_id})\n"
            f"• Amount: {amount} {from_token_symbol}\n"
            f"• From Token Address: {from_token_address}\n"
            f"• To Token Address: {to_token_address}\n\n"
            f"**Available Bridge Routes:**\n{bridge_names}\n\n"
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
    else:
        user_id = update.message.from_user.id
        user_wallet = user_wallets.get(user_id, {}).get("address")
        private_key = user_wallets.get(user_id, {}).get("private_key")

        if not user_wallet:
            await update.message.reply_text("⚠️ Please create/import a wallet first!")
            return

        # 读取环境变量，设置合约地址和 RPC URL
        CONTRACT_ADDRESS = os.getenv("AVAYIELD_CONTRACT_ADDRESS", "0x8B414448de8B609e96bd63Dcf2A8aDbd5ddf7fdd")
        RPC_URL = os.getenv("AVAX_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")

        print("Initializing AvaYield Strategy Interactor...")

        # 创建 AvaYield 交互对象
        strategy = AvaYieldInteractor(
            rpc_url=RPC_URL,
            contract_address=CONTRACT_ADDRESS,
            private_key=private_key
        )
        if action == "get_pool_deposits":
            try:
                # 获取钱包 AVAX 余额
                balance_wei = strategy.w3.eth.get_balance(strategy.account.address)
                balance_avax = Web3.from_wei(balance_wei, "ether")

                # 获取 AvaYield 策略的总存款量
                total_deposits = strategy.get_pool_deposits()

                # 生成交互消息
                response_message = (
                    f"💰 **AvaYield Strategy Overview** 💰\n\n"
                    f"• **Wallet Address:** `{user_wallet}`\n"
                    f"• **Wallet Balance:** {balance_avax:.4f} AVAX\n"
                    f"• **Total Deposits in Strategy:** {total_deposits:.4f} AVAX\n"
                )

                await update.message.reply_text(response_message, parse_mode="Markdown")

            except Exception as e:
                print(f"\nError occurred: {str(e)}")
                await update.message.reply_text(f"❌ Error fetching AvaYield data: {str(e)}")
        elif action == "get_pool_rewards":
            try:
                # Check current rewards
                rewards = strategy.get_pool_rewards()
                print(f"Current Rewards: {rewards} AVAX")

                # 生成交互消息
                response_message = (
                    f"💰 **AvaYield Strategy Rewards** 💰\n\n"
                    f"• **Wallet Address:** `{user_wallet}`\n"
                    f"• **Current Rewards:** {rewards:.3f} AVAX 🏆\n"
                )
                await update.message.reply_text(response_message, parse_mode="Markdown")
            except Exception as e:
                print(f"\nError occurred: {str(e)}")
                await update.message.reply_text(f"❌ Error fetching AvaYield rewards: {str(e)}")
        elif action == "get_leverage":
            try:
                # Check current leverage
                leverage = strategy.get_leverage()
                print(f"Current Leverage: {leverage}x")

                # 生成交互消息
                response_message = (
                    f"💰 **AvaYield Strategy Leverage** 💰\n\n"
                    f"• **Wallet Address:** `{user_wallet}`\n"
                    f"• **Current Leverage:** {leverage:.4f}x 🔥\n"
                )
                await update.message.reply_text(response_message, parse_mode="Markdown")
            except Exception as e:
                print(f"\nError occurred: {str(e)}")
                await update.message.reply_text(f"❌ Error fetching AvaYield leverage: {str(e)}")
        elif action == 'get_my_balance':
            try:
                # Check user balance
                user_balance = strategy.w3.eth.get_balance(strategy.account.address)
                print(f"\nWallet Balance: {Web3.from_wei(user_balance, 'ether')} AVAX")

                # 生成交互消息
                response_message = (
                    f"💰 **AvaYield User Balance** 💰\n\n"
                    f"• **Wallet Address:** `{user_wallet}`\n"
                    f"• **Your Balance:** {Web3.from_wei(user_balance, 'ether'):.3f} shares 🚀\n"
                )
                await update.message.reply_text(response_message, parse_mode="Markdown")
            except Exception as e:
                print(f"\nError occurred: {str(e)}")
                await update.message.reply_text(f"❌ Error fetching AvaYield user balance: {str(e)}")
        elif action == 'get_my_rewards':
            try:
                # Check user rewards
                user_rewards = strategy.get_my_rewards()
                print(f"User Rewards: {Web3.from_wei(user_rewards, 'ether')} AVAX")

                # 生成交互消息
                response_message = (
                    f"💰 **AvaYield User Rewards** 💰\n\n"
                    f"• **Wallet Address:** `{user_wallet}`\n"
                    f"• **Your Rewards:** {Web3.from_wei(user_rewards, 'ether'):.3f} AVAX 🏆\n"
                )
                await update.message.reply_text(response_message, parse_mode="Markdown")
            except Exception as e:
                print(f"\nError occurred: {str(e)}")
                await update.message.reply_text(f"❌ Error fetching AvaYield user rewards: {str(e)}")
        elif action == 'check_apr':
            try:
                # Check APR
                apr = strategy.get_apr()
                print(f"\nEstimated APR: {apr:.3f}%")
                # 生成交互消息
                response_message = (
                    f"💰 **AvaYield Estimated APR** 💰\n\n"
                    f"• **Wallet Address:** `{user_wallet}`\n"
                    f"• **Estimated APR:** {apr:.3f}% 💸\n"
                )
                await update.message.reply_text(response_message, parse_mode="Markdown")
            except Exception as e:
                print(f"\nError occurred: {str(e)}")
                await update.message.reply_text(f"❌ Error fetching AvaYield APR: {str(e)}")
        elif action == 'deposits':
            amount_avax = command_data.get('amount_avax') # 假设用户输入的是金额
            if not amount_avax:
                await update.message.reply_text("❌ Please provide the amount of AVAX to deposit.")
                return

            print(f"\n--- Depositing {amount_avax} AVAX ---")

            # Fetch current balance
            balance_before = strategy.w3.eth.get_balance(strategy.account.address)
            balance_before_avax = Web3.from_wei(balance_before, 'ether')

            # Build a preview message
            preview_message = (
                f"🚀 AVAX Deposit Preview:\n"
                f"• Amount to Deposit: {amount_avax} AVAX\n"
                f"• Current Balance: {balance_before_avax:.3f} AVAX\n\n"
                "Confirm to proceed with this deposit."
            )

            # 将存款数据嵌入到回调数据中
            callback_data_confirm = f"confirm_deposit:{amount_avax}:{balance_before}"
            callback_data_cancel = "cancel_deposit"

            # Confirmation buttons
            keyboard = [[
                InlineKeyboardButton("✅ Confirm", callback_data=callback_data_confirm),
                InlineKeyboardButton("❌ Cancel", callback_data=callback_data_cancel)
            ]]
            await update.message.reply_text(
                preview_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        elif action == 'reinvest_rewards':
            print("\n--- Reinvesting Rewards ---")
            # Fetch pending rewards
            rewards = strategy.get_my_rewards()
            min_reinvest = Web3.from_wei(strategy.contract.functions.MIN_TOKENS_TO_REINVEST().call(), 'ether')

            if rewards >= min_reinvest:
                # Build a preview message
                preview_message = (
                    f"🚀 Reinvest Rewards Preview:\n"
                    f"• Pending Rewards: {rewards} AVAX\n"
                    f"• Minimum Required: {min_reinvest:.3f} AVAX\n\n"
                    "Confirm to proceed with reinvestment."
                )

                # Confirmation buttons
                keyboard = [[
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm_reinvest"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_reinvest")
                ]]
                await update.message.reply_text(
                    preview_message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                print(f"Not enough rewards to reinvest. Need at least {min_reinvest} AVAX.")
                await update.message.reply_text(f"❌ Not enough rewards to reinvest. Need at least {min_reinvest} AVAX.")
        elif action == 'withdraw_rewards':
            print("\n--- Withdrawing Only Rewards ---")
            # Fetch pending rewards
            rewards = strategy.get_my_rewards()  # Get user's pending rewards in AVAX
            if rewards > 0:
                # Build a preview message
                preview_message = (
                    f"🚀 Withdraw Rewards Preview:\n"
                    f"• Pending Rewards: {rewards:.3f} AVAX\n\n"
                    "Confirm to proceed with withdrawal."
                )

                # Confirmation buttons
                keyboard = [[
                    InlineKeyboardButton("✅ Confirm", callback_data="confirm_withdraw"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")
                ]]
                await update.message.reply_text(
                    preview_message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                print("No rewards available to withdraw.")
                await update.message.reply_text("❌ No rewards available to withdraw.")
        elif action == 'withdraw_partial':
            # Extract the percentage of shares to withdraw
            percentage = command_data.get("percentage")
            if not percentage:
                await update.message.reply_text("❌ Please provide the percentage of shares to withdraw.")
                return

            # 获取用户的当前份额
            user_shares = Decimal(strategy.get_my_balance())

            if user_shares > 0:
                # 计算提现金额
                withdraw_amount = user_shares * Decimal(percentage) / Decimal(100)

                # 构建预览消息
                preview_message = (
                    f"🚀 Withdraw Shares Preview:\n"
                    f"• Total Shares: {user_shares}\n"
                    f"• Percentage to Withdraw: {percentage}%\n"
                    f"• Amount to Withdraw: {withdraw_amount:.3f} AVAX\n\n"
                    "Confirm to proceed with withdrawal."
                )

                # 确认按钮
                keyboard = [[
                    InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_withdraw_shares:{percentage}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw_shares")
                ]]
                await update.message.reply_text(
                    preview_message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                print("No shares to withdraw.")
                await update.message.reply_text("❌ No shares to withdraw.")
        elif action == 'withdraw_everything':
            print("\n--- Withdrawing Everything ---")
            # 获取用户的奖励和份额
            rewards = strategy.get_my_rewards()
            user_shares = Decimal(strategy.get_my_balance())

            # 构建预览消息
            preview_message = (
                f"🚀 Withdraw Everything Preview:\n"
                f"• Pending Rewards: {rewards} AVAX\n"
                f"• Total Shares: {user_shares:.3f}\n\n"
                "Confirm to proceed with reinvesting rewards and withdrawing all shares."
            )

            # 确认按钮
            keyboard = [[
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_withdraw_all"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw_all")
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

    if query.data == "cancel":
        if user_id not in pending_transactions:
            await query.edit_message_text("⚠️ Transaction expired. Please start over.")
            return
        pending_transactions.pop(user_id)
        await query.edit_message_text("❌ Transaction cancelled.")
        return
    if query.data == "confirm":
        if user_id not in pending_transactions:
            await query.edit_message_text("⚠️ Transaction expired. Please start over.")
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
                f"Track on: https://www.socketscan.io/tx/{tx_hash}"
            )
        except Exception as e:
            message = f"❌ Transaction failed: {str(e)}"

        await query.edit_message_text(message)
    
        # 读取环境变量，设置合约地址和 RPC URL
    
    CONTRACT_ADDRESS = os.getenv("AVAYIELD_CONTRACT_ADDRESS", "0x8B414448de8B609e96bd63Dcf2A8aDbd5ddf7fdd")
    RPC_URL = os.getenv("AVAX_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
    # 创建 AvaYield 交互对象
    strategy = AvaYieldInteractor(
        rpc_url=RPC_URL,
        contract_address=CONTRACT_ADDRESS,
        private_key=user_wallets[user_id]["private_key"]
    )
    # 处理取消操作
    if query.data == "cancel_deposit":
        await query.edit_message_text("❌ Deposit cancelled.")
        return
    # 处理存款确认
    if query.data.startswith("confirm_deposit:"):
        # 从回调数据中提取金额和余额
        _, amount_avax, balance_before = query.data.split(":")
        balance_before = int(balance_before)

        # Deposit AVAX into the strategy
        print(f"\n--- Depositing {amount_avax} AVAX ---")
        try:
            receipt = strategy.deposit(Decimal(amount_avax))
            if receipt:
                print(f"Deposit successful! Transaction hash: {receipt['transactionHash'].hex()}")
            else:
                raise Exception("Deposit failed.")

            time.sleep(10)  # Wait for confirmation

            balance_after = strategy.w3.eth.get_balance(strategy.account.address)
            difference = Web3.from_wei(balance_before - balance_after, 'ether')
            print(f"Balance change after deposit: {difference} AVAX (includes gas fees)")
            print("--------------------------------\n")

            # Send success message to the user
            message = (
                f"✅ Deposit successful!\n"
                f"Transaction hash: {receipt['transactionHash'].hex()}\n"
                f"Track on: https://www.snowtrace.io/tx/{receipt['transactionHash'].hex()}"
                f"Balance change: {difference} AVAX (includes gas fees)"
            )
        except Exception as e:
            message = f"❌ Deposit failed: {str(e)}"

        await query.edit_message_text(message)

 # 处理取消操作
    if query.data == "cancel_reinvest":
        await query.edit_message_text("❌ Reinvestment canceled.")
        return

    # 处理复投确认
    if query.data == "confirm_reinvest":
        # Fetch pending rewards
        rewards = strategy.get_my_rewards()

        # Execute reinvestment
        print(f"Reinvesting {rewards} AVAX...")
        try:
            strategy.reinvest()
            time.sleep(10)  # Wait for transaction confirmation
            new_rewards = strategy.get_my_rewards()
            print(f"Rewards after reinvest: {new_rewards} AVAX (should be 0 or near 0)")

            # Send success message to the user
            message = f"✅ Reinvestment successful! New rewards: {new_rewards} AVAX"
        except Exception as e:
            message = f"❌ Reinvestment failed: {str(e)}"

        await query.edit_message_text(message)

    # 处理取消操作
    if query.data == "cancel_withdraw":
        await query.edit_message_text("❌ Withdrawal canceled.")
        return

    # 处理提现确认
    if query.data == "confirm_withdraw":
        # Fetch pending rewards
        rewards = strategy.get_my_rewards()

        # Execute withdrawal
        print(f"Attempting to withdraw {rewards} AVAX directly...")
        try:
            receipt = strategy.withdraw(rewards)  # Attempt direct AVAX withdrawal
            if receipt:
                print(f"Withdrawal successful! Transaction hash: {receipt['transactionHash'].hex()}")

                # Send success message to the user
                message = f"✅ Withdrawal successful! Transaction hash: {receipt['transactionHash'].hex()}"
            else:
                raise Exception("Withdrawal failed! Check contract requirements.")
        except Exception as e:
            message = f"❌ Withdrawal failed: {str(e)}"

        await query.edit_message_text(message)

    # 处理取消操作
    if query.data == "cancel_withdraw_shares":
        await query.edit_message_text("❌ Withdrawal canceled.")
        return

    # 处理提现确认
    if query.data.startswith("confirm_withdraw_shares:"):
        # 从回调数据中提取提现比例
        percentage = query.data.split(":")[1]

        # 获取用户的当前份额
        user_shares = Decimal(strategy.get_my_balance())

        # 计算提现金额
        withdraw_amount = user_shares * Decimal(percentage) / Decimal(100)

        # 执行提现操作
        print(f"\n--- Withdrawing {percentage}% of Shares ---")
        print(f"Withdrawing {withdraw_amount} AVAX ({percentage}% of total)...")
        try:
            strategy.withdraw(withdraw_amount)
            time.sleep(10)  # Wait for transaction confirmation

            # 发送成功消息
            message = f"✅ Withdrawal successful! {withdraw_amount} AVAX withdrawn."
        except Exception as e:
            message = f"❌ Withdrawal failed: {str(e)}"

        await query.edit_message_text(message)

    if query.data == "confirm_withdraw_all":
        # Step 1: Reinvest rewards (if any)
        rewards = strategy.get_my_rewards()
        if rewards > 0:
            print("Reinvesting rewards before withdrawal...")
            try:
                strategy.reinvest()
                time.sleep(10)  # Wait for transaction confirmation
                await query.edit_message_text("✅ Rewards reinvested successfully.")
            except Exception as e:
                await query.edit_message_text(f"❌ Rewards reinvestment failed: {str(e)}")
                return

        # Step 2: Withdraw all shares
        user_shares = Decimal(strategy.get_my_balance())
        if user_shares > 0:
            print(f"Withdrawing all {user_shares} AVAX...")
            try:
                strategy.withdraw(user_shares)
                time.sleep(10)  # Wait for transaction confirmation
                await query.edit_message_text(f"✅ Full withdrawal successful! {user_shares} AVAX withdrawn.")
            except Exception as e:
                await query.edit_message_text(f"❌ Full withdrawal failed: {str(e)}")
        else:
            await query.edit_message_text("❌ No shares left to withdraw.")

        print("Withdrawal complete.")
        print("--------------------------------\n")
    if query.data == "cancel_withdraw_all":
        await query.edit_message_text("❌ Withdrawal canceled.")
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
