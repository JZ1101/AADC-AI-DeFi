"""
------------------------------------------------------------------------------------------------------------------------
Liquidity Provision with Dexalot
------------------------------------------------------------------------------------------------------------------------
"""
"""
Fetching available liquidity pools (get_liquidity_pools())
Checking user LP balances (get_user_lp_balances())
Adding liquidity (add_liquidity())
Removing liquidity (remove_liquidity())
Claiming rewards (claim_rewards())
Calculating pool APY (get_pool_apy())
Fetching LP token USD value (get_lp_value_usd())
"""

from web3 import Web3
from typing import Dict, List
import json

class DexalotManager:
    DEXALOT_CONTRACTS = {
        "portfolio": "0x5100Bd04485BFd679E46CFe25c5B23ec89c35775",
        "exchange": "0x01ceA217653A6ea0E76FAA93b7d4752eD38E8dDc",
        "rewards": "0x4e3A49567427f79665C83e4A05Eb2Da46f8487C4"
    }

    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.load_contracts()

    def load_contracts(self):
        """Load Dexalot contract ABIs"""
        with open('abis/dexalot_portfolio.json', 'r') as f:
            portfolio_abi = json.load(f)
        with open('abis/dexalot_exchange.json', 'r') as f:
            exchange_abi = json.load(f)
            
        self.portfolio = self.w3.eth.contract(
            address=self.DEXALOT_CONTRACTS["portfolio"],
            abi=portfolio_abi
        )
        self.exchange = self.w3.eth.contract(
            address=self.DEXALOT_CONTRACTS["exchange"],
            abi=exchange_abi
        )

    async def get_liquidity_pools(self) -> List[Dict]:
        """Fetch available Dexalot liquidity pools"""
        try:
            pool_count = self.exchange.functions.getPairCount().call()
            pools = []

            for i in range(pool_count):
                pool_info = self.exchange.functions.getPair(i).call()
                apy = await self.get_pool_apy(pool_info['pair'])
                
                pools.append({
                    'pair': pool_info['pair'],
                    'base_token': pool_info['baseToken'],
                    'quote_token': pool_info['quoteToken'],
                    'total_liquidity': pool_info['totalLiquidity'],
                    'apy': apy
                })

            return pools
        except Exception as e:
            raise Exception(f"Error fetching pools: {str(e)}")

    async def get_user_lp_balances(self, wallet_address: str) -> List[Dict]:
        """Get user's LP positions"""
        try:
            pools = await self.get_liquidity_pools()
            balances = []

            for pool in pools:
                lp_balance = self.portfolio.functions.getLPBalance(
                    wallet_address,
                    pool['pair']
                ).call()
                
                if lp_balance > 0:
                    balances.append({
                        'pair': pool['pair'],
                        'lp_balance': lp_balance,
                        'usd_value': await self.get_lp_value_usd(pool['pair'], lp_balance)
                    })

            return balances
        except Exception as e:
            raise Exception(f"Error fetching LP balances: {str(e)}")

    async def add_liquidity(
        self, 
        wallet_address: str, 
        pair: str, 
        base_amount: int, 
        quote_amount: int, 
        private_key: str
    ) -> str:
        """Add liquidity to Dexalot pool"""
        try:
            tx = self.portfolio.functions.addLiquidity(
                pair,
                base_amount,
                quote_amount
            ).build_transaction({
                'from': wallet_address,
                'gas': 2000000,
                'nonce': self.w3.eth.get_transaction_count(wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return tx_hash.hex()
        except Exception as e:
            raise Exception(f"Error adding liquidity: {str(e)}")

    async def remove_liquidity(
        self, 
        wallet_address: str, 
        pair: str, 
        lp_amount: int, 
        private_key: str
    ) -> str:
        """Remove liquidity from Dexalot pool"""
        try:
            tx = self.portfolio.functions.removeLiquidity(
                pair,
                lp_amount
            ).build_transaction({
                'from': wallet_address,
                'gas': 2000000,
                'nonce': self.w3.eth.get_transaction_count(wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return tx_hash.hex()
        except Exception as e:
            raise Exception(f"Error removing liquidity: {str(e)}")

    async def claim_rewards(self, wallet_address: str, pair: str, private_key: str) -> str:
        """Claim LP rewards"""
        try:
            rewards_contract = self.w3.eth.contract(
                address=self.DEXALOT_CONTRACTS["rewards"],
                abi=self.REWARDS_ABI
            )
            
            tx = rewards_contract.functions.claimRewards(pair).build_transaction({
                'from': wallet_address,
                'gas': 2000000,
                'nonce': self.w3.eth.get_transaction_count(wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return tx_hash.hex()
        except Exception as e:
            raise Exception(f"Error claiming rewards: {str(e)}")

    async def get_pool_apy(self, pair: str) -> float:
        """Calculate pool APY including fees and rewards"""
        try:
            # Get pool data
            pool_info = self.exchange.functions.getPairInfo(pair).call()
            
            # Get 24h volume
            volume_24h = pool_info['volume24h']
            
            # Get fee rate
            fee_rate = pool_info['feeRate']
            
            # Get total liquidity
            total_liquidity = pool_info['totalLiquidity']
            
            # Calculate fee APY
            daily_fees = volume_24h * fee_rate
            fee_apy = (daily_fees * 365 * 100) / total_liquidity
            
            # Get reward APY from rewards contract
            rewards_contract = self.w3.eth.contract(
                address=self.DEXALOT_CONTRACTS["rewards"],
                abi=self.REWARDS_ABI
            )
            reward_apy = rewards_contract.functions.getRewardAPY(pair).call()
            
            # Total APY
            total_apy = fee_apy + reward_apy
            
            return total_apy
        except Exception as e:
            raise Exception(f"Error calculating APY: {str(e)}")

    async def get_lp_value_usd(self, pair: str, lp_amount: int) -> float:
        """Get USD value of LP tokens"""
        try:
            # Get pool info
            pool_info = self.exchange.functions.getPairInfo(pair).call()
            
            # Calculate share of pool
            pool_share = lp_amount / pool_info['totalLiquidity']
            
            # Get token values in USD
            base_value = await self.get_token_price_usd(pool_info['baseToken'])
            quote_value = await self.get_token_price_usd(pool_info['quoteToken'])
            
            # Calculate total value
            total_value = (base_value + quote_value) * pool_share
            
            return total_value
        except Exception as e:
            raise Exception(f"Error getting LP value: {str(e)}")

    async def get_token_price_usd(self, token_address: str) -> float:
        """Get token price in USD"""
        try:
            # Call price oracle
            price = self.exchange.functions.getTokenPrice(token_address).call()
            return float(price) / 1e8  # Assuming 8 decimal places
        except Exception as e:
            raise Exception(f"Error getting token price: {str(e)}")

    # Basic rewards ABI
    REWARDS_ABI = [
        {
            "inputs": [{"name": "pair", "type": "string"}],
            "name": "claimRewards",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"name": "pair", "type": "string"}],
            "name": "getRewardAPY",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]