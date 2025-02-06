"""
------------------------------------------------------------------------
Psoition Management for GMX 
------------------------------------------------------------------------
"""
"""
1 Position Management
1.1 fetch_existing_positions(wallet_address) – Fetches all open positions with on-chain data
1.2 _get_position(position_id) – Internal function to retrieve a specific position
1.3 check_liquidation_risk(wallet_address) – Checks positions nearing liquidation

2 Trading Execution
2.1 preview_open_position(wallet_address, token_address, is_long, size_usd, collateral_usd) – Gets preview details before opening a position
2.2 open_position(wallet_address, preview_data, private_key) – Opens a position on GMX

2.3 preview_leverage_adjustment(position_id, new_leverage) – Simulates leverage change before execution
2.4 adjust_leverage(wallet_address, position_id, preview_data, private_key) – Adjusts leverage for an open position

2.5 preview_close_position(position_id) – Simulates closing a position
2.6 close_position(wallet_address, position_id, private_key) – Closes a position on GMX

3️ Risk & Fees Monitoring
3.1 get_position_health(position_id) – Calculates health factor, risk score, and distance to liquidation
3.2 get_trading_fees(position_id) – Retrieves borrowing fees, trading fees, and funding fees
"""
from web3 import Web3
from typing import Dict, List, Optional
import json
import requests
from decimal import Decimal

class GMXManager:
    GMX_CONTRACTS = {
        "reader": "0x38d91ED96283d62182Fc6d990C24097A918a4d9b",
        "position_router": "0x6f2800d4fb11d45963ac8EA6f036b63E77176E0F",
        "vault": "0x489ee077994B6658eAfA855C308275EAd8097C4A",
        "glp_manager": "0x3963FfC9dff443c2A94f21b129D429891E32ec18"
    }

    def __init__(self, rpc_url: str, subgraph_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.subgraph_url = subgraph_url
        self.load_contracts()

    def load_contracts(self):
        """Load GMX contract ABIs and initialize contracts"""
        with open('abis/gmx_reader.json', 'r') as f:
            reader_abi = json.load(f)
        with open('abis/gmx_position_router.json', 'r') as f:
            position_router_abi = json.load(f)
        with open('abis/gmx_vault.json', 'r') as f:
            vault_abi = json.load(f)
            
        self.reader = self.w3.eth.contract(
            address=self.GMX_CONTRACTS["reader"],
            abi=reader_abi
        )
        self.position_router = self.w3.eth.contract(
            address=self.GMX_CONTRACTS["position_router"],
            abi=position_router_abi
        )
        self.vault = self.w3.eth.contract(
            address=self.GMX_CONTRACTS["vault"],
            abi=vault_abi
        )

    async def fetch_existing_positions(self, wallet_address: str) -> List[Dict]:
        """Get all open positions with enriched data"""
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
            lastIncreasedTime
            borrowingFees
            fundingFees
          }
        }
        """ % wallet_address.lower()
        
        response = requests.post(self.subgraph_url, json={'query': query})
        positions = response.json()['data']['positions']

        # Enrich with on-chain data
        for pos in positions:
            chain_data = self.reader.functions.getPosition(
                wallet_address,
                pos['indexToken'],
                pos['collateral'],
                pos['isLong']
            ).call()
            
            # Get current market price
            market_price = self.vault.functions.getPrice(pos['indexToken']).call()
            
            health_metrics = await self.get_position_health(pos['id'])
            fees = await self.get_trading_fees(pos['id'])
            
            pos.update({
                'size': chain_data[0],
                'collateral': chain_data[1],
                'leverage': chain_data[2],
                'market_price': market_price,
                'health_factor': health_metrics['health_factor'],
                'liquidation_risk_score': health_metrics['risk_score'],
                'fees': fees
            })

        return positions

    async def preview_open_position(
        self,
        wallet_address: str,
        token_address: str,
        is_long: bool,
        size_usd: float,
        collateral_usd: float
    ) -> Dict:
        """Preview opening a new position"""
        # Validate leverage
        leverage = size_usd / collateral_usd
        if leverage < 1.1 or leverage > 50:
            raise ValueError("Leverage must be between 1.1x and 50x")

        # Get minimum collateral
        min_collateral = self.vault.functions.minCollateral().call()
        if collateral_usd < min_collateral:
            raise ValueError(f"Minimum collateral is ${min_collateral}")

        # Get position parameters
        preview = self.reader.functions.getPositionDelta(
            token_address,
            size_usd,
            is_long
        ).call()

        return {
            'entry_price': preview[0],
            'liquidation_price': preview[1],
            'fees': preview[2],
            'leverage': leverage,
            'size_usd': size_usd,
            'collateral_usd': collateral_usd
        }

    async def open_position(
        self,
        wallet_address: str,
        preview_data: Dict,
        private_key: str
    ) -> str:
        """Execute position opening"""
        tx = self.position_router.functions.createPosition(
            preview_data['token_address'],
            preview_data['size_usd'],
            preview_data['collateral_usd'],
            preview_data['is_long']
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()

    async def preview_leverage_adjustment(
        self,
        position_id: str,
        new_leverage: float
    ) -> Dict:
        """Preview leverage adjustment"""
        position = await self._get_position(position_id)
        
        if new_leverage < 1.1 or new_leverage > 50:
            raise ValueError("New leverage must be between 1.1x and 50x")

        preview = self.reader.functions.getPositionLeverageDelta(
            position['id'],
            new_leverage
        ).call()

        return {
            'new_collateral': preview[0],
            'new_size': preview[1],
            'fees': preview[2],
            'new_liquidation_price': preview[3]
        }

    async def adjust_leverage(
        self,
        wallet_address: str,
        position_id: str,
        preview_data: Dict,
        private_key: str
    ) -> str:
        """Execute leverage adjustment"""
        tx = self.position_router.functions.adjustLeverage(
            position_id,
            preview_data['new_size'],
            preview_data['new_collateral']
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()

    async def preview_close_position(self, position_id: str) -> Dict:
        """Preview position closure"""
        position = await self._get_position(position_id)
        
        preview = self.reader.functions.getPositionCloseDelta(
            position['id']
        ).call()

        return {
            'return_amount': preview[0],
            'fees': preview[1],
            'market_impact': preview[2]
        }

    async def close_position(
        self,
        wallet_address: str,
        position_id: str,
        private_key: str
    ) -> str:
        """Execute position closure"""
        tx = self.position_router.functions.closePosition(
            position_id
        ).build_transaction({
            'from': wallet_address,
            'gas': 2000000,
            'nonce': self.w3.eth.get_transaction_count(wallet_address)
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()

    async def check_liquidation_risk(self, wallet_address: str) -> List[Dict]:
        """Check positions for liquidation risk"""
        positions = await self.fetch_existing_positions(wallet_address)
        at_risk_positions = []

        for pos in positions:
            market_price = Decimal(pos['market_price'])
            liq_price = Decimal(pos['liquidationPrice'])
            
            # Calculate distance to liquidation
            price_diff_percent = abs(market_price - liq_price) / market_price * 100
            
            if price_diff_percent < 2:  # Within 2% of liquidation
                at_risk_positions.append({
                    'position_id': pos['id'],
                    'distance_to_liquidation': float(price_diff_percent),
                    'market_price': float(market_price),
                    'liquidation_price': float(liq_price),
                    'risk_level': 'CRITICAL' if price_diff_percent < 1 else 'HIGH'
                })

        return at_risk_positions

    async def get_trading_fees(self, position_id: str) -> Dict:
        """Calculate all applicable fees"""
        position = await self._get_position(position_id)
        
        # Get borrowing fees
        borrowing_fees = self.vault.functions.getBorrowingFees(
            position['indexToken'],
            position['size']
        ).call()
        
        # Get trading fees
        trading_fees = self.vault.functions.getTradingFees(
            position['indexToken'],
            position['size']
        ).call()
        
        # Get funding fees
        funding_fees = self.vault.functions.getFundingFees(
            position['indexToken'],
            position['size'],
            position['isLong']
        ).call()

        return {
            'borrowing_fees': borrowing_fees,
            'trading_fees': trading_fees,
            'funding_fees': funding_fees,
            'total_fees': borrowing_fees + trading_fees + funding_fees
        }

    async def get_position_health(self, position_id: str) -> Dict:
        """Calculate position health metrics"""
        position = await self._get_position(position_id)
        
        # Calculate health factor
        collateral = Decimal(position['collateral'])
        size = Decimal(position['size'])
        health_factor = (collateral / size) * Decimal('100')
        
        # Calculate risk score (0-100, higher is riskier)
        market_price = Decimal(position['market_price'])
        liq_price = Decimal(position['liquidationPrice'])
        price_diff_percent = abs(market_price - liq_price) / market_price * 100
        risk_score = min(100, (100 - price_diff_percent) * 2)
        
        return {
            'health_factor': float(health_factor),
            'risk_score': float(risk_score),
            'collateral_ratio': float(collateral / size),
            'distance_to_liquidation': float(price_diff_percent)
        }

    async def _get_position(self, position_id: str) -> Optional[Dict]:
        """Internal method to fetch position details"""
        query = """
        {
          position(id: "%s") {
            id
            indexToken
            size
            collateral
            leverage
            isLong
            entryPrice
            liquidationPrice
            market_price
          }
        }
        """ % position_id
        
        response = requests.post(self.subgraph_url, json={'query': query})
        return response.json()['data']['position']