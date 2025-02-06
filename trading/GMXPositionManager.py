"""
--------------------------------------------------------------------------
Position Management with GMX
--------------------------------------------------------------------------
"""
from web3 import Web3
import json
import requests
from typing import Dict, List
from eth_account import Account
from config import GMX_CONTRACTS, TRADING_PAIRS, RPC_URL, SUBGRAPH_URL

class GMXPositionManager:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.load_contracts()

    def load_contracts(self):
        """Load GMX contract ABIs and create contract instances"""
        with open('abis/gmx_reader.json', 'r') as f:
            reader_abi = json.load(f)
        with open('abis/gmx_position_router.json', 'r') as f:
            position_router_abi = json.load(f)
        
        self.reader = self.w3.eth.contract(
            address=GMX_CONTRACTS["reader"],
            abi=reader_abi
        )
        self.position_router = self.w3.eth.contract(
            address=GMX_CONTRACTS["position_router"],
            abi=position_router_abi
        )

    async def fetch_existing_positions(self, wallet_address: str) -> List[Dict]:
        """Fetch positions from GMX contracts and subgraph"""
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
        
        response = requests.post(SUBGRAPH_URL, json={'query': query})
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
        if trading_pair not in TRADING_PAIRS:
            raise ValueError(f"Invalid trading pair. Available pairs: {', '.join(TRADING_PAIRS.keys())}")

        if collateral_usd < TRADING_PAIRS[trading_pair]["min_collateral"]:
            raise ValueError(f"Minimum collateral required: ${TRADING_PAIRS[trading_pair]['min_collateral']}")

        leverage = size_usd / collateral_usd
        if leverage > 50 or leverage < 1.1:
            raise ValueError("Leverage must be between 1.1x and 50x")

        token = TRADING_PAIRS[trading_pair]["token"]
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
        token = TRADING_PAIRS[preview_data['trading_pair']]["token"]
        
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

    async def adjust_leverage(self, wallet_address: str, position_id: str, new_leverage: float) -> Dict:
        """Preview leverage adjustment"""
        position = await self.get_position(position_id)
        
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
        tx = self.position_router.functions.adjustPositionLeverage(
            preview_data['position_id'],
            preview_data['new_leverage']
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
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