"""
------------------------------------------------------------------------
Yield Farming with YieldYak
------------------------------------------------------------------------
"""
"""
Example usage:
yieldyak_manager = YieldYakManager(RPC_URL)
farms = await yieldyak_manager.get_farms()
deposits = await yieldyak_manager.get_user_deposits(wallet_address)
"""
"""
1 Fetching available farms (get_farms())
2 Checking user deposits (get_user_deposits())
3 Depositing into farms (deposit())
4 Withdrawing from farms (withdraw())
5 Claiming rewards (claim_rewards())
6 Fetching APY estimates (get_farm_apy())
7 Getting token USD value (get_token_value_usd())
"""
from web3 import Web3
from typing import Dict, List
import json
import requests

class YieldYakManager:
    YIELDYAK_CONTRACTS = {
        "router": "0xC4729E56b831d74bBc18797e0e17A295fA77488c",
        "master": "0x0cf605484A512d3F3435fed77AB5ddC0525Daf5f",
        "helper": "0x5B73210864b498E2c67f810C31B5Fb41D1A4b039"
    }

    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.load_contracts()

    def load_contracts(self):
        """Load YieldYak contract ABIs"""
        with open('abis/yieldyak_router.json', 'r') as f:
            router_abi = json.load(f)
        with open('abis/yieldyak_master.json', 'r') as f:
            master_abi = json.load(f)
            
        self.router = self.w3.eth.contract(
            address=self.YIELDYAK_CONTRACTS["router"],
            abi=router_abi
        )
        self.master = self.w3.eth.contract(
            address=self.YIELDYAK_CONTRACTS["master"],
            abi=master_abi
        )

    async def get_farms(self) -> List[Dict]:
        """Fetch available YieldYak farms"""
        try:
            farm_count = self.router.functions.farmCount().call()
            farms = []

            for i in range(farm_count):
                farm_info = self.router.functions.getFarm(i).call()
                apy = await self.get_farm_apy(i)
                
                farms.append({
                    'id': i,
                    'name': farm_info[0],
                    'token': farm_info[1],
                    'tvl': farm_info[2],
                    'apy': apy
                })

            return farms
        except Exception as e:
            raise Exception(f"Error fetching farms: {str(e)}")

    async def get_user_deposits(self, wallet_address: str) -> List[Dict]:
        """Get user's deposits across all farms"""
        try:
            farms = await self.get_farms()
            deposits = []

            for farm in farms:
                balance = self.router.functions.getUserBalance(
                    farm['id'],
                    wallet_address
                ).call()
                
                if balance > 0:
                    deposits.append({
                        'farm_id': farm['id'],
                        'farm_name': farm['name'],
                        'balance': balance,
                        'balance_usd': await self.get_token_value_usd(farm['token'], balance)
                    })

            return deposits
        except Exception as e:
            raise Exception(f"Error fetching user deposits: {str(e)}")

    async def deposit(self, wallet_address: str, farm_id: int, amount: int, private_key: str) -> str:
        """Deposit assets into a YieldYak farm"""
        try:
            tx = self.router.functions.deposit(
                farm_id,
                amount
            ).build_transaction({
                'from': wallet_address,
                'gas': 2000000,
                'nonce': self.w3.eth.get_transaction_count(wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return tx_hash.hex()
        except Exception as e:
            raise Exception(f"Error depositing: {str(e)}")

    async def withdraw(self, wallet_address: str, farm_id: int, amount: int, private_key: str) -> str:
        """Withdraw assets from a YieldYak farm"""
        try:
            tx = self.router.functions.withdraw(
                farm_id,
                amount
            ).build_transaction({
                'from': wallet_address,
                'gas': 2000000,
                'nonce': self.w3.eth.get_transaction_count(wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return tx_hash.hex()
        except Exception as e:
            raise Exception(f"Error withdrawing: {str(e)}")

    async def claim_rewards(self, wallet_address: str, farm_id: int, private_key: str) -> str:
        """Claim auto-compounded rewards"""
        try:
            tx = self.router.functions.harvest(
                farm_id
            ).build_transaction({
                'from': wallet_address,
                'gas': 2000000,
                'nonce': self.w3.eth.get_transaction_count(wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            return tx_hash.hex()
        except Exception as e:
            raise Exception(f"Error claiming rewards: {str(e)}")

    async def get_farm_apy(self, farm_id: int) -> float:
        """Get estimated APY for a farm"""
        try:
            # Get farm metrics from YieldYak helper contract
            metrics = self.router.functions.getFarmMetrics(farm_id).call()
            
            # Calculate APY based on rewards rate and TVL
            apy = metrics[2] / metrics[1] * 365 * 100  # Annualized percentage
            
            return apy
        except Exception as e:
            raise Exception(f"Error calculating APY: {str(e)}")

    async def get_token_value_usd(self, token_address: str, amount: int) -> float:
        """Get USD value of token amount using price feeds"""
        try:
            # Call price oracle to get token price
            price = self.router.functions.getTokenPrice(token_address).call()
            
            # Convert amount to USD value
            decimals = self.w3.eth.contract(address=token_address, abi=self.ERC20_ABI).functions.decimals().call()
            value_usd = (amount * price) / (10 ** decimals)
            
            return value_usd
        except Exception as e:
            raise Exception(f"Error getting token value: {str(e)}")

    # Basic ERC20 ABI for token interactions
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }
    ]