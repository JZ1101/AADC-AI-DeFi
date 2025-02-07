from YieldYakInteractor import YieldYakInteractor
from web3 import Web3

def main():
    # Initialize Yield Yak Interactor
    strategy = YieldYakInteractor(
        rpc_url="https://api.avax.network/ext/bc/C/rpc",
        private_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", 
        contract_address="0x0C4684086914D5B1525bf16c62a0FF8010AB991A"
    )

    try:
        # Check rewards
        rewards = strategy.check_reward()
        print(f"Current rewards: {rewards}")

        # Get total deposits
        deposits = strategy.get_total_deposits()
        print(f"Total deposits: {deposits}")

        # Example deposit 
        amount_to_deposit = Web3.to_wei(1, 'ether')
        receipt = strategy.deposit(amount_to_deposit)
        print(f"Deposit Transaction Hash: {receipt['transactionHash'].hex()}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
