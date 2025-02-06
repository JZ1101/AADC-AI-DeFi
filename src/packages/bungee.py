import os
import requests
from dotenv import load_dotenv
import json
from web3 import Web3

load_dotenv()

BUNGEE_API_KEY = os.getenv("BUNGEE_API_KEY")
BASE_URL = "https://api.socket.tech/v2"

# Token Registry (example structure)
with open('token_registry.json', 'r') as file:
    TOKEN_REGISTRY = json.load(file)


# ------------------------------
# Helper Functions
# ------------------------------

CHAIN_IDS = {
    "Ethereum": 1,
    "Binance Smart Chain": 56,
    "Polygon": 137,
    "Avalanche": 43114,
    "Arbitrum": 42161,
    "Optimism": 10,
    "Base": 8453,
    "ZKSync": 324,
    "Linea": 59144,
    "Scroll": 534352
}

def get_token_address(chain_id, symbol):
    """Fetch token address from the registry based on chain ID and symbol."""
    chain_key = str(chain_id)
    if chain_key not in TOKEN_REGISTRY:
        raise ValueError(f"Chain ID {chain_id} not supported in the token registry.")
    
    for token in TOKEN_REGISTRY[chain_key]:
        if token["symbol"].lower() == symbol.lower():
            return Web3.to_checksum_address(token["address"])
    raise ValueError(f"Token {symbol} not found on chain {chain_id}.")

def get_bungee_headers():
    """Generate headers for Bungee API requests."""
    return {
        "API-KEY": BUNGEE_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def validate_token_address(chain_id, token_address):
    """Validate if a token exists in the registry for the given chain."""
    chain_key = str(chain_id)
    if chain_key not in TOKEN_REGISTRY:
        raise ValueError(f"Chain ID {chain_id} not supported")
    
    token_address = Web3.to_checksum_address(token_address)
    tokens = TOKEN_REGISTRY[chain_key]
    
    for token in tokens:
        registry_address = Web3.to_checksum_address(token["address"])
        if registry_address == token_address and token["chainId"] == chain_id:
            return
    raise ValueError(f"Token {token_address} not found on chain {chain_id}")

def convert_token_amount(amount, chain_id, token_address):
    chain_key = str(chain_id)
    if chain_key not in TOKEN_REGISTRY:
        raise ValueError(f"Chain ID {chain_id} not supported")

    token_address = Web3.to_checksum_address(token_address)
    tokens = TOKEN_REGISTRY[chain_key]

    for token in tokens:
        registry_address = Web3.to_checksum_address(token["address"])
        if registry_address == token_address and token["chainId"] == chain_id:
            return amount * 10 ** token["decimals"]

# ------------------------------
# Core API Functions
# ------------------------------

def get_quote(from_chain_id, from_token_address, to_chain_id, to_token_address, from_amount, user_address,
              unique_routes_per_bridge=True, sort="output", single_tx_only=True):
    """
    Get cross-chain swap quote with proper parameter formatting and validation.
    """
    # Validate tokens against registry
    validate_token_address(from_chain_id, from_token_address)
    validate_token_address(to_chain_id, to_token_address)

    from_amount = convert_token_amount(from_amount, from_chain_id, from_token_address)

    # Convert addresses to checksum format
    from_token_address = Web3.to_checksum_address(from_token_address)
    to_token_address = Web3.to_checksum_address(to_token_address)
    user_address = Web3.to_checksum_address(user_address)

    url = f"{BASE_URL}/quote"
    params = {
        "fromChainId": from_chain_id,
        "fromTokenAddress": from_token_address,
        "toChainId": to_chain_id,
        "toTokenAddress": to_token_address,
        "fromAmount": f"{from_amount:.0f}",  # Ensure string format
        "userAddress": user_address,
        "uniqueRoutesPerBridge": str(unique_routes_per_bridge).lower(),
        "sort": sort,
        "singleTxOnly": str(single_tx_only).lower()
    }
    
    response = requests.get(url, headers=get_bungee_headers(), params=params)
    response.raise_for_status()
    return response.json()

def build_transaction(route, sender_address):
    """Build transaction with checksummed sender address."""
    sender_address = Web3.to_checksum_address(sender_address)
    url = f"{BASE_URL}/build-tx"
    payload = {
        "route": route,
        "senderAddress": sender_address
    }
    response = requests.post(url, headers=get_bungee_headers(), json=payload)
    response.raise_for_status()
    return response.json()

def check_allowance(chain_id, owner, allowance_target, token_address):
    """Check allowance with validated addresses."""
    owner = Web3.to_checksum_address(owner)
    allowance_target = Web3.to_checksum_address(allowance_target)
    token_address = Web3.to_checksum_address(token_address)
    
    url = f"{BASE_URL}/approval/check-allowance"
    params = {
        "chainID": chain_id,
        "owner": owner,
        "allowanceTarget": allowance_target,
        "tokenAddress": token_address
    }
    response = requests.get(url, headers=get_bungee_headers(), params=params)
    response.raise_for_status()
    return response.json()

def get_approval_transaction_data(chain_id, owner, allowance_target, token_address, amount):
    """Get approval TX data with checksummed addresses."""
    owner = Web3.to_checksum_address(owner)
    allowance_target = Web3.to_checksum_address(allowance_target)
    token_address = Web3.to_checksum_address(token_address)
    
    url = f"{BASE_URL}/approval/build-tx"
    params = {
        "chainID": chain_id,
        "owner": owner,
        "allowanceTarget": allowance_target,
        "tokenAddress": token_address,
        "amount": amount
    }
    response = requests.get(url, headers=get_bungee_headers(), params=params)
    response.raise_for_status()
    return response.json()

def get_bridge_status(transaction_hash, from_chain_id, to_chain_id):
    """Check bridge status with proper parameter types."""
    url = f"{BASE_URL}/bridge-status"
    params = {
        "transactionHash": transaction_hash,
        "fromChainId": int(from_chain_id),
        "toChainId": int(to_chain_id)
    }
    response = requests.get(url, headers=get_bungee_headers(), params=params)
    response.raise_for_status()
    return response.json()