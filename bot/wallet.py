from web3 import Web3, Account
import os
from dotenv import load_dotenv

WEB3_PROVIDER = os.getenv("WEB3_PROVIDER", "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID")
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
# ------------------------------
# Wallet Functionality (as in original code)
# ------------------------------

def create_wallet():
    """Generate a new EVM wallet and return the address and private key."""
    account = w3.eth.account.create()
    return account.address, w3.to_hex(account.key)

def import_wallet(private_key: str):
    """Import a wallet from a given private key. Returns the wallet address and validated private key."""
    try:
        account = Account.from_key(private_key)
        return account.address, account.privateKey.hex()
    except Exception as e:
        print(f"Error importing wallet: {e}")
        return None, None

def get_wallet_balance(address: str):
    """Retrieve the balance (in ETH) for the given address."""
    try:
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.fromWei(balance_wei, 'ether')
        return balance_eth
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None