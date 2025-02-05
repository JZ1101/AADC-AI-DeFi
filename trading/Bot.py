from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from position_manager import GMXPositionManager
from config import TRADING_PAIRS

class GMXBot:
    def __init__(self):
        self.position_manager = GMXPositionManager()
        self.user_states = {}

    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display user positions"""
        try:
            wallet_address = "USER_WALLET_ADDRESS"  # Replace in production
            positions = await self.position_manager.fetch_existing_positions(wallet_address)
            
            if not positions:
                await update.message.reply_text("No open positions found")
                return

            for pos in positions:
                message = (
                    f"Position #{pos['id']}\n"
                    f"Size: ${pos['size']:,.2f}\n"
                    f"Leverage: {pos['leverage']}x\n"
                    f"Entry Price: ${pos['entryPrice']:,.2f}\n"
                    f"Liq. Price: ${pos['liquidationPrice']:,.2f}\n"
                    f"PnL: ${pos['pnl']:,.2f}\n"
                )
                keyboard = [
                    [
                        InlineKeyboardButton("Adjust Leverage", callback_data=f"adjust_{pos['id']}"),
                        InlineKeyboardButton("Close", callback_data=f"close_{pos['id']}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, reply_markup=reply_markup)

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def start_open_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the position opening process"""
        pairs_keyboard = [
            [InlineKeyboardButton(pair, callback_data=f"pair_{pair}")]
            for pair in TRADING_PAIRS.keys()
        ]
        reply_markup = InlineKeyboardMarkup(pairs_keyboard)
        
        await update.message.reply_text(
            "Select trading pair:",
            reply_markup=reply_markup
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboard"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        try:
            if data.startswith('pair_'):
                await self._handle_pair_selection(query, data)
            elif data.startswith('direction_'):
                await self._handle_direction_selection(query, data)
            elif data == 'confirm_open':
                await self._handle_open_confirmation(query)
            elif data.startswith('adjust_'):
                await self._handle_leverage_adjustment(query, data)
            elif data.startswith('close_'):
                await self._handle_position_close(query, data)
            
            await query.answer()
        except Exception as e:
            await query.answer(f"Error: {str(e)}", show_alert=True)

    async def _handle_pair_selection(self, query, data):
        """Handle trading pair selection"""
        pair = data.replace('pair_', '')
        self.user_states[query.from_user.id] = {'trading_pair': pair}
        
        keyboard = [
            [
                InlineKeyboardButton("LONG", callback_data="direction_long"),
                InlineKeyboardButton("SHORT", callback_data="direction_short")
            ]
        ]
        await query.edit_message_text(
            f"Selected {pair}. Choose position direction:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _handle_direction_selection(self, query, data):
        """Handle position direction selection"""
        is_long = data == 'direction_long'
        self.user_states[query.from_user.id]['is_long'] = is_long
        
        await query.edit_message_text(
            f"Enter position size in USD (e.g., /size 1000)"
        )

    async def _handle_open_confirmation(self, query):
        """Handle position open confirmation"""
        user_id = query.from_user.id
        if user_id not in self.user_states or 'preview' not in self.user_states[user_id]:
            raise ValueError("No position preview found")

        preview = self.user_states[user_id]['preview']
        tx_hash = await self.position_manager.confirm_open(
            "USER_WALLET_ADDRESS",  # Replace in production
            preview,
            "PRIVATE_KEY"  # Handle securely in production
        )
        
        await query.edit_message_text(
            f"Position opened! Transaction: {tx_hash}\n"
            "Use /positions to view your positions"
        )
        
        del self.user_states[user_id]

    async def set_position_size(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle position size input"""
        user_id = update.message.from_user.id
        if user_id not in self.user_states:
            await update.message.reply_text("Please start with /open_position")
            return

        try:
            size = float(context.args[0])
            self.user_states[user_id]['size_usd'] = size
            await update.message.reply_text(
                f"Enter collateral amount in USD (e.g., /collateral 100)"
            )
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid size. Example: /size 1000")

    async def set_collateral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle collateral input and preview position"""
        user_id = update.message.from_user.id
        if user_id not in self.user_states:
            await update.message.reply_text("Please start with /open_position")
            return

        try:
            collateral = float(context.args[0])
            state = self.user_states[user_id]
            
            preview = await self.position_manager.open_position(
                "USER_WALLET_ADDRESS",  # Replace in production
                state['trading_pair'],
                state['is_long'],
                state['size_usd'],
                collateral
            )
            
            message = self._format_position_preview(preview)
            keyboard = [[InlineKeyboardButton("Confirm Open", callback_data="confirm_open")]]
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            self.user_states[user_id]['preview'] = preview
            
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid collateral. Example: /collateral 100")
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    def _format_position_preview(self, preview: dict) -> str:
        """Format position preview message"""
        return (
            f"Position Preview:\n"
            f"Pair: {preview['trading_pair']}\n"
            f"Side: {'Long' if preview['is_long'] else 'Short'}\n"
            f"Size: ${preview['size_usd']:,.2f}\n"
            f"Collateral: ${preview['collateral_usd']:,.2f}\n"
            f"Leverage: {preview['leverage']:.2f}x\n"
            f"Entry Price: ${preview['entry_price']:,.2f}\n"
            f"Liq. Price: ${preview['liquidation_price']:,.2f}\n"
            f"Fee: ${preview['fee']:,.2f}\n"
        )
