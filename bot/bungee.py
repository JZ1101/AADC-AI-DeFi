import os
import requests
from dotenv import load_dotenv
import json

BUNGEE_API_KEY = os.getenv("BUNGEE_API_KEY")
BASE_URL = "https://api.socket.tech/v2"

# ------------------------------
# Bungee API Integration Functions (Updated)
# ------------------------------

def get_bungee_headers():
    """Generate headers for Bungee API requests using the correct header key."""
    return {
        "API-KEY": BUNGEE_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def get_quote(from_chain_id, from_token_address, to_chain_id, to_token_address, from_amount, user_address,
              unique_routes_per_bridge, sort, single_tx_only):
    """
    Get cross-chain swap quote using Bungee's /quote endpoint.
    Returns the JSON response.
    """
    url = f"{BASE_URL}/quote"
    params = {
        "fromChainId": from_chain_id,
        "fromTokenAddress": from_token_address,
        "toChainId": to_chain_id,
        "toTokenAddress": to_token_address,
        "fromAmount": from_amount,
        "userAddress": user_address,
        "uniqueRoutesPerBridge": str(unique_routes_per_bridge).lower(),
        "sort": sort,
        "singleTxOnly": str(single_tx_only).lower()
    }
    response = requests.get(url, headers=get_bungee_headers(), params=params)
    response.raise_for_status()
    return response.json()

def build_transaction(route, sender_address):
    """
    Build final transaction using Bungee's /build-tx endpoint.
    Returns the JSON response.
    """
    url = f"{BASE_URL}/build-tx"
    payload = {
        "route": route,
        "senderAddress": sender_address
    }
    response = requests.post(url, headers=get_bungee_headers(), data=json.dumps(payload))
    response.raise_for_status()
    return response.json()

def check_allowance(chain_id, owner, allowance_target, token_address):
    """
    Check token allowance via Bungee's approval API.
    Returns the JSON response.
    """
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
    """
    Fetches transaction data for token approval from Bungee's approval API.
    Returns the JSON response.
    """
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
    """
    Fetch the status of the bridging transaction.
    Returns the JSON response.
    """
    url = f"{BASE_URL}/bridge-status"
    params = {
        "transactionHash": transaction_hash,
        "fromChainId": from_chain_id,
        "toChainId": to_chain_id
    }
    response = requests.get(url, headers=get_bungee_headers(), params=params)
    response.raise_for_status()
    return response.json()