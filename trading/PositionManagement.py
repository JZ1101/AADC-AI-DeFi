from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from web3 import Web3
import json
import requests
from typing import Dict, List
from eth_account import Account

class GMXPositionManager:
    # GMX v2 contract addresses
    GMX_CONTRACTS = {
        "reader": "0x38d91ED96283d62182Fc6d990C24097A918a4d9b",
        "position_router": "0x6f2800d4fb11d45963ac8EA6f036b63E77176E0F",
        "router": "0x7452c558d45f8afC8c83dAe62C3f8A5BE19c71f6",
        "vault": "0x489ee077994B6658eAfA855C308275EAd8097C4A"
    }

    # Available trading pairs
    TRADING_PAIRS = {
        "AVAX-USD": {
            "token": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
            "decimals": 18,
            "min_collateral": 10  # Minimum collateral in USD
        },
        "ETH-USD": {
            "token": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
            "decimals": 18,
            "min_collateral": 10
        },
        "BTC-USD": {
            "token": "0x152b9d0FdC40C096757F570A51E494bd4b943E50",
            "decimals": 8,
            "min_collateral": 10
        },
        "USDC-USD": {
            "token": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
            "decimals": 6,
            "min_collateral": 10
        }
    }

    def __init__(self):
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))
        
        # Load contract ABIs
        self.load_contracts()
        
        # GMX Subgraph endpoint
        self.subgraph_url = "https://api.thegraph.com/subgraphs/name/gmx-io/gmx-avalanche"

    def load_contracts(self):
        """Load GMX contract ABIs and create contract instances"""
        with open('abis/gmx_reader.json', 'r') as f:
            reader_abi = json.load(f)
        with open('abis/gmx_position_router.json', 'r') as f:
            position_router_abi = json.load(f)
        
        self.reader = self.w3.eth.contract(
            address=self.GMX_CONTRACTS["reader"],
            abi=reader_abi
        )
        self.position_router = self.w3.eth.contract(
            address=self.GMX_CONTRACTS["position_router"],
            abi=position_router_abi
        )

    async def fetch_existing_positions(self, wallet_address: str) -> List[Dict]:
        """Fetch positions from GMX contracts and subgraph"""
        # Query subgraph for historical position data
        query = """
        {
          positions(where: {account: "%s", status: "OPEN"}) {
            id
            indexToken
            size
            collateral
            leverage
            entryPrice
            liquidationPrice
            pnl
            isLong
            collateralToken
          }
        }
        """ % wallet_address.lower()
        
        response = requests.post(self.subgraph_url, json={'query': query})
        positions = response.json()['data']['positions']

        # Enrich with on-chain data
        for pos in positions:
            on_chain_data = self.reader.functions.getPosition(
                wallet_address,
                pos['indexToken'],
                pos['collateralToken'],
                pos['isLong']
            ).call()
            pos.update({
                'size': on_chain_data[0],
                'collateral': on_chain_data[1],
                'leverage': on_chain_data[2],
                'liquidationPrice': on_chain_data[3]
            })

        return positions

    async def open_position(self, wallet_address: str, trading_pair: str, is_long: bool, 
                          size_usd: float, collateral_usd: float) -> Dict:
        """Preview opening a new position"""
        if trading_pair not in self.TRADING_PAIRS:
            raise ValueError(f"Invalid trading pair. Available pairs: {', '.join(self.TRADING_PAIRS.keys())}")

        if collateral_usd < self.TRADING_PAIRS[trading_pair]["min_collateral"]:
            raise ValueError(f"Minimum collateral required: ${self.TRADING_PAIRS[trading_pair]['min_collateral']}")

        # Calculate leverage
        leverage = size_usd / collateral_usd
        if leverage > 50 or leverage < 1.1:
            raise ValueError("Leverage must be between 1.1x and 50x")

        # Get price and fees from Reader contract
        token = self.TRADING_PAIRS[trading_pair]["token"]
        preview = self.reader.functions.previewOpenPosition(
            token,
            size_usd,
            collateral_usd,
            is_long
        ).call()

        return {
            'trading_pair': trading_pair,
            'size_usd': size_usd,
            'collateral_usd': collateral_usd,
            'leverage': leverage,
            'entry_price': preview[0],
            'liquidation_price': preview[1],
            'fee': preview[2],
            'is_long': is_long
        }

    async def confirm_open(self, wallet_address: str, preview_data: Dict, private_key: str):
        """Execute opening a new position"""
        token = self.TRADING_PAIRS[preview_data['trading_pair']]["token"]
        
        tx = self.position_router.functions.openPosition(
            token,
            preview_data['is_long'],
            preview_data['size_usd'],
            preview_data['collateral_usd']
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
        signed_tx = Account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()
        """Preview leverage adjustment"""
        position = await self.get_position(position_id)
        
        # Calculate required collateral changes
        preview = self.reader.functions.previewPositionLeverageAdjustment(
            position['indexToken'],
            position['size'],
            position['collateral'],
            new_leverage
        ).call()

        return {
            'position_id': position_id,
            'new_leverage': new_leverage,
            'collateral_delta': preview[0],
            'fee': preview[1],
            'liquidation_price': preview[2]
        }

    async def confirm_leverage(self, wallet_address: str, preview_data: Dict, private_key: str):
        """Execute leverage adjustment"""
        # Build transaction
        tx = self.position_router.functions.adjustPositionLeverage(
            preview_data['position_id'],
            preview_data['new_leverage']
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
        # Sign and send transaction
        signed_tx = Account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()

    async def close_position(self, wallet_address: str, position_id: str) -> Dict:
        """Preview position closure"""
        position = await self.get_position(position_id)
        
        preview = self.reader.functions.previewPositionClose(
            position['indexToken'],
            position['size'],
            position['collateral'],
            position['isLong']
        ).call()

        return {
            'position_id': position_id,
            'return_amount': preview[0],
            'fee': preview[1],
            'market_impact': preview[2]
        }

    async def confirm_close(self, wallet_address: str, preview_data: Dict, private_key: str):
        """Execute position closure"""
        tx = self.position_router.functions.closePosition(
            preview_data['position_id']
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
        signed_tx = Account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()

class GMXBot:
    def __init__(self):
        self.position_manager = GMXPositionManager()
        self.user_states = {}  # Store temporary user state during position opening

    async def start_open_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the position opening process"""
        # Show available trading pairs
        pairs_keyboard = [
            [InlineKeyboardButton(pair, callback_data=f"pair_{pair}")]
            for pair in self.position_manager.TRADING_PAIRS.keys()
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

        if data.startswith('pair_'):
            # User selected a trading pair
            pair = data.replace('pair_', '')
            self.user_states[user_id] = {'trading_pair': pair}
            
            # Ask for position direction
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

        elif data.startswith('direction_'):
            # User selected direction
            is_long = data == 'direction_long'
            self.user_states[user_id]['is_long'] = is_long
            
            await query.edit_message_text(
                f"Enter position size in USD (e.g., /size 1000)"
            )

        await query.answer()

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
            
            # Preview position
            preview = await self.position_manager.open_position(
                "USER_WALLET_ADDRESS",  # Replace with actual wallet
                state['trading_pair'],
                state['is_long'],
                state['size_usd'],
                collateral
            )
            
            # Show preview and confirmation button
            message = (
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
            
            keyboard = [[InlineKeyboardButton("Confirm Open", callback_data="confirm_open")]]
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Store preview data
            self.user_states[user_id]['preview'] = preview
            
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid collateral. Example: /collateral 100")
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

    async def confirm_open_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute position opening"""
        user_id = update.message.from_user.id
        if user_id not in self.user_states or 'preview' not in self.user_states[user_id]:
            await update.message.reply_text("Please start with /open_position")
            return

        try:
            preview = self.user_states[user_id]['preview']
            tx_hash = await self.position_manager.confirm_open(
                "USER_WALLET_ADDRESS",  # Replace with actual wallet
                preview,
                "PRIVATE_KEY"  # Handle securely in production
            )
            
            await update.message.reply_text(
                f"Position opened! Transaction: {tx_hash}\n"
                "Use /positions to view your positions"
            )
            
            # Clear user state
            del self.user_states[user_id]
            
        except Exception as e:
            await update.message.reply_text(f"Error opening position: {str(e)}")

    async def positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display user positions"""
        try:
            # In production, get wallet_address from user data
            wallet_address = "USER_WALLET_ADDRESS"
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
                        InlineKeyboardButton("Adjust Leverage", callback_data=f'adjust_{pos["id"]}'),
                        InlineKeyboardButton("Close", callback_data=f'close_{pos["id"]}')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, reply_markup=reply_markup)

        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")

async def main():
    bot = GMXBot()
    app = Application.builder().token("YOUR_BOT_TOKEN").build()
    
    # Position management commands
    app.add_handler(CommandHandler("positions", bot.positions))
    app.add_handler(CommandHandler("open_position", bot.start_open_position))
    app.add_handler(CommandHandler("size", bot.set_position_size))
    app.add_handler(CommandHandler("collateral", bot.set_collateral))
    
    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())