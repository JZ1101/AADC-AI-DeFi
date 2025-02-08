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

        
        # Optional: Test deposit functionality
        should_test_deposit = os.getenv("TEST_DEPOSIT", "false").lower() == "true"
        if should_test_deposit:
            print("\n⚡️ Triggering deposit function...")
            deposit_amount = float(os.getenv("TEST_DEPOSIT_AMOUNT", "0.01"))
            print(f"⚡️ Attempting to deposit {deposit_amount} AVAX")
            
            balance_before = strategy.w3.eth.get_balance(strategy.account.address)
            
            # Execute deposit
            receipt = strategy.AvaYield_deposit(deposit_amount)
            
            if receipt:
                print(f"✅ Deposit transaction sent! Hash: {receipt['transactionHash'].hex()}")
            else:
                print("❌ Deposit function did not execute properly.")

            time.sleep(10)  # Wait for confirmation

            # Check balance after deposit
            balance_after = strategy.w3.eth.get_balance(strategy.account.address)
            difference = Web3.from_wei(balance_before - balance_after, 'ether')
            print(f"💰 Balance change: -{difference} AVAX (includes gas)")


        # Optional: Test withdraw functionality
        should_test_withdraw = os.getenv("TEST_WITHDRAW", "false").lower() == "true"
        if should_test_withdraw:
            print("\nTesting withdraw functionality...")
            withdraw_amount = float(os.getenv("TEST_WITHDRAW_AMOUNT", "0.005"))
            print(f"Attempting to withdraw {withdraw_amount} shares")
            
            # Execute withdrawal
            receipt = strategy.AvaYield_withdraw(withdraw_amount)
            if receipt and receipt['status'] == 1:
                print(f"Withdrawal successful! Transaction hash: {receipt['transactionHash'].hex()}")
                
                # Wait for a few blocks and check new balance
                time.sleep(10)  # Wait for next block
                new_user_balance = strategy.contract.functions.balanceOf(strategy.account.address).call()
                print(f"New strategy balance: {Web3.from_wei(new_user_balance, 'ether')} shares")
            else:
                print("Withdrawal failed!")

        # Optional: Test reinvest functionality
        should_test_reinvest = os.getenv("TEST_REINVEST", "false").lower() == "true"
        if should_test_reinvest:
            print("\nTesting reinvest functionality...")
            rewards_before = strategy.AvaYield_get_rewards()
            
            # Execute reinvest
            receipt = strategy.reinvest()
            if receipt and receipt['status'] == 1:
                print(f"Reinvest successful! Transaction hash: {receipt['transactionHash'].hex()}")
                
                # Wait for a few blocks and check new rewards
                time.sleep(10)  # Wait for next block
                rewards_after = strategy.AvaYield_get_rewards()
                print(f"Rewards before: {rewards_before} AVAX")
                print(f"Rewards after: {rewards_after} AVAX")
            else:
                print("Reinvest failed!")

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise e

if __name__ == "__main__":
    main()