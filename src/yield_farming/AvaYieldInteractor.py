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
        
        abi_path = os.path.join(os.path.dirname(__file__), 'abis', 'ava_yield.json')
        with open(abi_path, "r") as f:
            self.abi = json.load(f) 

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        if private_key:
            self.account = Account.from_key(private_key)
        else:
            self.account = None

    def AvaYield_get_total_deposits(self):
        """Get total deposits in the strategy"""
        try:
            total = self.contract.functions.totalDeposits().call()
            return Web3.from_wei(total, 'ether')
        except Exception as e:
            print(f"Error getting total deposits: {e}")
            return None

    def AvaYield_get_rewards(self):
        """Get current rewards"""
        try:
            rewards = self.contract.functions.checkReward().call()
            return Web3.from_wei(rewards, 'ether')
        except Exception as e:
            print(f"Error checking rewards: {e}")
            return None

    def AvaYield_get_leverage(self):
        """Get current leverage ratio"""
        try:
            leverage = self.contract.functions.getActualLeverage().call()
            return Decimal(leverage) / Decimal(1e18)
        except Exception as e:
            print(f"Error getting leverage: {e}")
            return None

    def AvaYield_deposit(self, amount_avax):
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
                'gas': 2000000,  # Adjust gas limit as needed
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            
            return self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            print(f"Error depositing: {e}")
            return None

    def AvaYield_withdraw(self, amount_shares):
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

    def AvaYield_reinvest(self):
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

