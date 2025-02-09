"""
----------------------------------------------------------------------------
Write function test cases for AvaYield Strategy
----------------------------------------------------------------------------
"""
import os
from dotenv import load_dotenv
from AvaYieldInteractor import AvaYieldInteractor
from web3 import Web3
from decimal import Decimal
import time

# Load environment variables
load_dotenv()

"""
----------------------------------------------------------------------------
Helper functions
----------------------------------------------------------------------------
"""

def check_initial_state(strategy):
    """Check the initial state of the contract and user before testing."""
    print("\n--- Checking Initial State ---")
    wallet_balance = strategy.w3.eth.get_balance(strategy.account.address)
    total_pool_deposits = strategy.get_pool_deposits()
    pool_rewards = strategy.get_pool_rewards()
    user_shares = strategy.get_my_balance()
    user_rewards = strategy.get_my_rewards()
    user_leverage = strategy.get_my_leverage()

    print(f"Wallet Balance: {Web3.from_wei(wallet_balance, 'ether')} AVAX")
    print(f"Total Strategy Deposits (Pool): {total_pool_deposits} AVAX")
    print(f"Pool Rewards: {pool_rewards} AVAX")
    print(f"Your Shares: {user_shares}")
    print(f"Your Pending Rewards: {user_rewards} AVAX")
    print(f"Your Leverage: {user_leverage}x")
    print("--------------------------------\n")

def deposit(strategy, amount_avax):
    """Deposit AVAX into the strategy."""
    print(f"\n--- Depositing {amount_avax} AVAX ---")
    balance_before = strategy.w3.eth.get_balance(strategy.account.address)
    
    receipt = strategy.deposit(amount_avax)
    
    if receipt:
        print(f"Deposit successful! Transaction hash: {receipt['transactionHash'].hex()}")
    else:
        print("Deposit failed.")

    time.sleep(10)  # Wait for confirmation

    balance_after = strategy.w3.eth.get_balance(strategy.account.address)
    difference = Web3.from_wei(balance_before - balance_after, 'ether')
    print(f"Balance change after deposit: {difference} AVAX (includes gas fees)")
    print("--------------------------------\n")

def reinvest_rewards(strategy):
    """Reinvests pending rewards if above the reinvestment threshold."""
    print("\n--- Reinvesting Rewards ---")
    rewards = strategy.get_my_rewards()
    min_reinvest = Web3.from_wei(strategy.contract.functions.MIN_TOKENS_TO_REINVEST().call(), 'ether')

    if rewards >= min_reinvest:
        print(f"Reinvesting {rewards} AVAX...")
        strategy.reinvest()
        time.sleep(10)  # Wait for transaction confirmation
        new_rewards = strategy.get_my_rewards()
        print(f"Rewards after reinvest: {new_rewards} AVAX (should be 0 or near 0)")
    else:
        print(f"Not enough rewards to reinvest. Need at least {min_reinvest} AVAX.")
    print("--------------------------------\n")

def withdraw_rewards(strategy):
    """Attempt to withdraw rewards directly as AVAX."""
    print("\n--- Withdrawing Only Rewards ---")
    
    rewards = strategy.get_my_rewards()  # Get user's pending rewards in AVAX

    if rewards > 0:
        print(f"Attempting to withdraw {rewards} AVAX directly...")
        receipt = strategy.withdraw(rewards)  # Attempt direct AVAX withdrawal
        if receipt:
            print(f"Withdrawal successful! Transaction hash: {receipt['transactionHash'].hex()}")
        else:
            print("Withdrawal failed! Check contract requirements.")
    else:
        print("No rewards available to withdraw.")

    print("--------------------------------\n")


def withdraw_partial(strategy, percentage):
    """Withdraws a percentage of the user's shares."""
    print(f"\n--- Withdrawing {percentage}% of Shares ---")
    user_shares = Decimal(strategy.get_my_balance())

    if user_shares > 0:
        withdraw_amount = user_shares * Decimal(percentage) / Decimal(100)
        print(f"Withdrawing {withdraw_amount} shares ({percentage}% of total)...")
        strategy.withdraw(withdraw_amount)
        time.sleep(10)  # Wait for transaction confirmation
    else:
        print("No shares to withdraw.")
    print("--------------------------------\n")

def withdraw_everything(strategy):
    """Withdraws all shares after reinvesting rewards if applicable."""
    print("\n--- Withdrawing Everything ---")
    
    # Step 1: Reinvest any pending rewards before full withdrawal
    rewards = strategy.get_my_rewards()
    if rewards > 0:
        print("Reinvesting rewards before withdrawal...")
        strategy.reinvest()
        time.sleep(10)

    # Step 2: Withdraw all shares
    user_shares = Decimal(strategy.get_my_balance())

    if user_shares > 0:
        print(f"Withdrawing all {user_shares} shares...")
        strategy.withdraw(user_shares)
        time.sleep(10)  # Wait for transaction confirmation
    else:
        print("No shares left to withdraw.")
    print("Withdrawal complete.")
    print("--------------------------------\n")

"""
----------------------------------------------------------------------------
Main function - Executes all test cases
----------------------------------------------------------------------------
"""

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
        # Test Case 0: Check Initial State
        check_initial_state(strategy)

        # Test Case 1: Deposit 0.01 AVAX
        deposit(strategy, Decimal("0.01"))

        # Test Case 2: Try Reinvesting (will only work if rewards > threshold)
        reinvest_rewards(strategy)

        # Test Case 3: Withdraw Only Rewards
        withdraw_rewards(strategy)

        # Test Case 4: Withdraw 50% of Shares
        withdraw_partial(strategy, 50)

        # Test Case 5: Withdraw Everything
        withdraw_everything(strategy)

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
