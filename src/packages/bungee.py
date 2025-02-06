import os
import requests
from dotenv import load_dotenv
import json
from web3 import Web3

load_dotenv()

BUNGEE_API_KEY = os.getenv("BUNGEE_API_KEY")
BASE_URL = "https://api.socket.tech/v2"
WEB3_PROVIDER = os.getenv("WEB3_PROVIDER", "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID")
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

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


def get_route_transaction_data(route):
    """Fetch transaction data for a given route."""
    url = f"{BASE_URL}/build-tx"
    headers = {
        "API-KEY": BUNGEE_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    body = json.dumps({"route": route})
    print(f"body")
    response = requests.post(url, headers=headers, data=body)
    print(f"response: {response}")

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


# ------------------------------
# Transaction Execution Logic
# ------------------------------

async def execute_transaction(user_id, route, private_key, user_wallets):
    """Execute the cross-chain transaction."""
    try:
        # Fetch transaction data
        print(f"here")
        api_return_data = get_route_transaction_data(route)
        approval_data = api_return_data.get("result", {}).get("approvalData")

        print(f"Transaction Data: {api_return_data}")

        # Handle token approval if required
        if approval_data:
            allowance_target = approval_data["allowanceTarget"]
            minimum_approval_amount = int(approval_data["minimumApprovalAmount"], 16)
            from_chain_id = route["fromChainId"]
            from_token_address = route["fromTokenAddress"]

            # Check current allowance
            allowance_check = check_allowance(from_chain_id, user_wallets[user_id]["address"], allowance_target, from_token_address)
            current_allowance = int(allowance_check.get("result", {}).get("value", "0x0"), 16)

            if current_allowance < minimum_approval_amount:
                # Fetch approval transaction data
                approval_tx_data = get_approval_transaction_data(
                    from_chain_id,
                    user_wallets[user_id]["address"],
                    allowance_target,
                    from_token_address,
                    minimum_approval_amount,
                )

                # Build and send approval transaction
                approval_tx = {
                    "to": approval_tx_data["result"]["to"],
                    "data": approval_tx_data["result"]["data"],
                    "value": 0,
                    "gas": 200000,  # Adjust gas limit as needed
                    "nonce": w3.eth.get_transaction_count(user_wallets[user_id]["address"]),
                    "chainId": from_chain_id,
                }
                signed_approval_tx = w3.eth.account.sign_transaction(approval_tx, private_key)
                approval_tx_hash = w3.eth.send_raw_transaction(signed_approval_tx.rawTransaction)
                print(f"Approval Transaction Hash: {w3.toHex(approval_tx_hash)}")

        # Get the current gas price
        gas_price = w3.eth.gas_price
        tx_data = api_return_data["result"]
        gas_estimate = w3.eth.estimate_gas({
            'from': user_wallets[user_id]["address"],
            'to': tx_data['txTarget'],
            'value': tx_data['value'],
            'data': tx_data['txData'],
            'gasPrice': gas_price,
        })
        transaction = {
            'from': user_wallets[user_id]["address"],
            'to': tx_data['txTarget'],
            'value': tx_data['value'],
            'data': tx_data['txData'],
            'gasPrice': gas_price,
            'gas': gas_estimate,
        }
        
        signed_main_tx = w3.eth.account.sign_transaction(transaction, private_key)
        main_tx_hash = w3.eth.send_raw_transaction(signed_main_tx.rawTransaction)
        return w3.toHex(main_tx_hash)

    except Exception as e:
        raise Exception(f"Transaction execution failed: {str(e)}")