""""
----------------------------------------------------------------------------
Write function test case
----------------------------------------------------------------------------
"""
import os
from dotenv import load_dotenv
from AvaYieldInteractor import AvaYieldInteractor
from web3 import Web3
import time

# Load environment variables
load_dotenv()

"""
----------------------------------------------------------------------------
Helper functions
----------------------------------------------------------------------------
"""
def withdraw_everything(strategy):
    # 1. Check your current rewards
    rewards = strategy.get_my_rewards()
    
    # 2. Reinvest if there are rewards (so they get added to your stake)
    if rewards > 0:
        print("Reinvesting rewards before withdrawal...")
        strategy.reinvest()
    
    # 3. Get your current balance in shares
    shares = strategy.get_my_balance()

    # 4. Withdraw all shares
    if shares > 0:
        print(f"Withdrawing all {shares} shares...")
        strategy.withdraw(shares)
    else:
        print("No shares left to withdraw.")

    print("Withdrawal complete.")

def only_claim_rewards(strategy):
    # 1. Check how much rewards you have
    rewards = strategy.get_my_rewards()

    # 2. Convert rewards (AVAX) into equivalent shares
    total_pool_deposits = strategy.get_pool_deposits()
    total_shares = strategy.contract.functions.totalSupply().call()

    if total_shares == 0 or total_pool_deposits == 0:
        print("No rewards available to claim.")
        return
    
    # Calculate how many shares represent your rewards
    reward_shares = (rewards / total_pool_deposits) * total_shares

    # 3. Withdraw that amount of shares to claim rewards
    if reward_shares > 0:
        print(f"Withdrawing {reward_shares} shares to claim rewards...")
        strategy.withdraw(reward_shares)
    else:
        print("No rewards available to withdraw.")

    print("Rewards claimed successfully.")


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
        # Optional: Test deposit functionality
        should_test_deposit = os.getenv("TEST_DEPOSIT", "false").lower() == "true"
        if should_test_deposit:
            print("\n⚡️ Triggering deposit function...")
            deposit_amount = float(os.getenv("TEST_DEPOSIT_AMOUNT", "0.01"))
            print(f"⚡️ Attempting to deposit {deposit_amount} AVAX")
            
            balance_before = strategy.w3.eth.get_balance(strategy.account.address)
            
            # Execute deposit
            receipt = strategy.deposit(deposit_amount)
            
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
            receipt = strategy.withdraw(withdraw_amount)
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
            rewards_before = strategy.get_rewards()
            
            # Execute reinvest
            receipt = strategy.reinvest()
            if receipt and receipt['status'] == 1:
                print(f"Reinvest successful! Transaction hash: {receipt['transactionHash'].hex()}")
                
                # Wait for a few blocks and check new rewards
                time.sleep(10)  # Wait for next block
                rewards_after = strategy.get_rewards()
                print(f"Rewards before: {rewards_before} AVAX")
                print(f"Rewards after: {rewards_after} AVAX")
            else:
                print("Reinvest failed!")

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise e

if __name__ == "__main__":
    main()