# avayield_strategy.py

from web3 import Web3
from eth_account import Account
from decimal import Decimal

import json
import os
class AvaYieldInteractor:
    def __init__(self, rpc_url, contract_address, private_key=None):
        """
        Initialize the AvaYield interactor
        
        Args:
            rpc_url (str): The Avalanche RPC URL
            contract_address (str): The deployed strategy contract address
            private_key (str, optional): Private key for signing transactions
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract_address = Web3.to_checksum_address(contract_address)
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        abi_path = os.path.join(base_path, 'abis', 'ava_yield.json')
        with open(abi_path, "r") as f:
            self.abi = json.load(f)

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        if private_key:
            self.account = Account.from_key(private_key)
        else:
            self.account = None
    """
    ----------------------------------------------------------------------------
    READ FUNCTIONS (POOL)
    ----------------------------------------------------------------------------
    """
    def get_pool_deposits(self):
        """Returns the total amount of AVAX deposited in the entire pool"""
        try:
            total = self.contract.functions.totalDeposits().call()
            return Web3.from_wei(total, 'ether')
        except Exception as e:
            print(f"Error getting total deposits: {e}")
            return None

    def get_pool_rewards(self):
        """total pending AVAX rewards for the contract (pool as a whole), not just your rewards"""
        try:
            rewards = self.contract.functions.checkReward().call()
            return Web3.from_wei(rewards, 'ether')
        except Exception as e:
            print(f"Error checking rewards: {e}")
            return None

    def get_leverage(self):
        """Get current leverage ratio"""
        try:
            leverage = self.contract.functions.getActualLeverage().call()
            return Decimal(leverage) / Decimal(1e18)
        except Exception as e:
            print(f"Error getting leverage: {e}")
            return None
    """
    ----------------------------------------------------------------------------
    READ FUNCTIONS (INDIVIDUAL)
    ----------------------------------------------------------------------------
    """
    def get_my_balance(self):
        """Returns the number of shares you own in the staking pool."""
        try:
            balance = self.contract.functions.balanceOf(self.account.address).call()
            return Web3.from_wei(balance, 'ether')
        except Exception as e:
            print(f"Error checking balance: {e}")
            return None

    def get_my_rewards(self):
        """Returns the estimated pending rewards that belong to YOU."""
        try:
            total_rewards = self.contract.functions.checkReward().call()  # Total pool rewards
            my_shares = self.contract.functions.balanceOf(self.account.address).call()  # Your shares
            total_shares = self.contract.functions.totalSupply().call()  # Total issued shares

            if total_shares == 0:
                return 0

            my_rewards = (my_shares / total_shares) * total_rewards
            return Web3.from_wei(my_rewards, 'ether')
        except Exception as e:
            print(f"Error checking your rewards: {e}")
            return None

    def get_my_leverage(self):
        """Returns the leverage ratio applied to your staked AVAX."""
        try:
            leverage = self.contract.functions.getActualLeverage().call()
            return leverage / 1e18  # Convert from wei-based decimal format
        except Exception as e:
            print(f"Error checking leverage: {e}")
            return None
        

    """
    ----------------------------------------------------------------------------
    WRITE FUNCTIONS: deposit / withdraw / reinvest
    ----------------------------------------------------------------------------
    """
    def deposit(self, amount_avax):
        """
        Deposit AVAX into the strategy
        
        Args:
            amount_avax (float): Amount of AVAX to deposit
        """
        if not self.account:
            raise ValueError("Private key not provided - cannot sign transaction")
        
        try:
            amount_wei = Web3.to_wei(amount_avax, 'ether')
            
            transaction = self.contract.functions.deposit().build_transaction({
                'from': self.account.address,
                'value': amount_wei,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 2000000,  # gas limit
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"Error depositing: {e}")
            return None

    def withdraw(self, amount_shares):
        """
        Withdraw from the strategy
        
        Args:
            amount_shares (float): Amount of shares to withdraw
        """
        if not self.account:
            raise ValueError("Private key not provided - cannot sign transaction")
        
        if amount_shares <= 0:
            raise ValueError("Withdrawal amount must be positive")
            
        try:
            amount_wei = Web3.to_wei(amount_shares, 'ether')
            
            transaction = self.contract.functions.withdraw(amount_wei).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 2000000,  # Adjust gas limit as needed
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"Error withdrawing: {e}")
            return None

    def reinvest(self):
        """Reinvest accumulated rewards"""
        if not self.account:
            raise ValueError("Private key not provided - cannot sign transaction")
        
        try:
            transaction = self.contract.functions.reinvest().build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 2000000,  # Adjust gas limit as needed
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"Error reinvesting: {e}")
            return None

