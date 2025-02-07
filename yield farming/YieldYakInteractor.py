from web3 import Web3
from eth_account import Account
import json
from typing import Optional

class YieldYakInteractor:
    def __init__(
        self,
        rpc_url: str = "https://api.avax.network/ext/bc/C/rpc",  # avalanche c-chain
        private_key: Optional[str] = None,
        contract_address: str = "0x0C4684086914D5B1525bf16c62a0FF8010AB991A", #https://snowtrace.io/address/0x0C4684086914D5B1525bf16c62a0FF8010AB991A/contract/43114/code
    ):
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Load ABI from JSON file 
        with open("abis/farm_abi.json", "r") as f:
            self.abi = json.load(f) 

        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(contract_address),
            abi=self.abi 
        )

        
        # Set up account if private key provided
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)

    def _get_transaction_params(self, value: int = 0):
        """Get basic transaction parameters."""
        return {
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 2000000,  # Adjust as needed
            'gasPrice': self.w3.eth.gas_price,
            'value': value
        }

    def deposit(self, amount: int):
        """Deposit tokens into the strategy."""
        if not self.account:
            raise ValueError("Account not initialized. Provide private key.")
        
        tx_params = self._get_transaction_params()
        transaction = self.contract.functions.deposit(amount).build_transaction(tx_params)
        
        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def withdraw(self, amount: int):
        """Withdraw tokens from the strategy."""
        if not self.account:
            raise ValueError("Account not initialized. Provide private key.")
        
        tx_params = self._get_transaction_params()
        transaction = self.contract.functions.withdraw(amount).build_transaction(tx_params)
        
        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def reinvest(self):
        """Reinvest rewards from staking contract."""
        if not self.account:
            raise ValueError("Account not initialized. Provide private key.")
        
        tx_params = self._get_transaction_params()
        transaction = self.contract.functions.reinvest().build_transaction(tx_params)
        
        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def check_reward(self) -> int:
        """Check pending rewards."""
        return self.contract.functions.checkReward().call()

    def get_total_deposits(self) -> int:
        """Get total deposits in the strategy."""
        return self.contract.functions.totalDeposits().call()

    def estimate_deployed_balance(self) -> int:
        """Estimate the deployed balance."""
        return self.contract.functions.estimateDeployedBalance().call()

