import os
from dotenv import load_dotenv
from AvaYieldInteractor import AvaYieldInteractor
from web3 import Web3
import time

# Load environment variables
load_dotenv()

def main():
    # Retrieve private key and other configs from .env
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY is missing from the .env file")

    # Contract address for AvaYield Strategy
    CONTRACT_ADDRESS = os.getenv("AVAYIELD_CONTRACT_ADDRESS", "0x8B414448de8B609e96bd63Dcf2A8aDbd5ddf7fdd")
    
    # RPC URL (can be overridden in .env)
    RPC_URL = os.getenv("AVAX_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")

    print("Initializing AvaYield Strategy Interactor...")
    strategy = AvaYieldInteractor(
        rpc_url=RPC_URL,
        contract_address=CONTRACT_ADDRESS,
        private_key=private_key
    )

    try:
        # Check wallet balance
        balance = strategy.w3.eth.get_balance(strategy.account.address)
        print(f"\nWallet Balance: {Web3.from_wei(balance, 'ether')} AVAX")

        # Check total deposits in the strategy
        total_deposits = strategy.AvaYield_get_total_deposits()
        print(f"Total Strategy Deposits: {total_deposits} AVAX")

        # Check current rewards
        rewards = strategy.AvaYield_get_rewards()
        print(f"Current Rewards: {rewards} AVAX")

        # Check current leverage
        leverage = strategy.AvaYield_get_leverage()
        print(f"Current Leverage: {leverage}x")

        # Get user's balance in the strategy
        user_balance = strategy.contract.functions.balanceOf(strategy.account.address).call()
        print(f"Your Strategy Balance: {Web3.from_wei(user_balance, 'ether')} shares")

        

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise e

if __name__ == "__main__":
    main()