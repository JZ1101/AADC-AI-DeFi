from deepseek import DeepSeekAPI
from dotenv import load_dotenv
import json
import os

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek_client = DeepSeekAPI(DEEPSEEK_API_KEY)

# ------------------------------
# NLP Processing using OpenAI
# ------------------------------
import re

def parse_command_nlp(text: str):
    """
    Use OpenAI's language model to parse the user's command.
    Expected keys vary based on the action type.
    """
    # Define possible actions and their required fields
    action_fields = {
        "fetch_existing_positions": ["wallet_address"],
        "check_liquidation_risk": ["wallet_address"],
        "preview_open_position": ["wallet_address", "token_address", "is_long", "size_usd", "collateral_usd"],
        "open_position": ["wallet_address", "preview_data", "private_key"],
        "preview_leverage_adjustment": ["position_id", "new_leverage"],
        "adjust_leverage": ["wallet_address", "position_id", "preview_data", "private_key"],
        "preview_close_position": ["position_id"],
        "close_position": ["wallet_address", "position_id", "private_key"],
        "get_position_health": ["position_id"],
        "get_trading_fees": ["position_id"],
        "transfer": ["amount", "from_token", "to_token", "from_chain", "to_chain"]
    }

    # Generate the prompt dynamically based on the action type
    prompt = f"""
Extract the following information from the command below:
- action: one of {list(action_fields.keys())}
- fields: depending on the action, extract the relevant fields from the command.

For each action, the required fields are:
- fetch_existing_positions: wallet_address
- check_liquidation_risk: wallet_address
- preview_open_position: wallet_address, token_address, is_long, size_usd, collateral_usd
- open_position: wallet_address, preview_data, private_key
- preview_leverage_adjustment: position_id, new_leverage
- adjust_leverage: wallet_address, position_id, preview_data, private_key
- preview_close_position: position_id
- close_position: wallet_address, position_id, private_key
- get_position_health: position_id
- get_trading_fees: position_id
- transfer: amount, from_token, to_token, from_chain, to_chain

Command: "{text}"
If any field is missing or ambiguous, return null.

Return the result as a JSON object with keys: action, and any other relevant fields based on the action.
Example:
{{
    "action": "transfer",
    "amount": 100,
    "from_token": "AVAX",
    "to_token": "USDC",
    "from_chain": "Avalanche",
    "to_chain": "Ethereum"
}}
"""

    try:
        print(f"user balance: {deepseek_client.user_balance()}")
        response = deepseek_client.chat_completion(prompt=prompt)
        json_match = re.search(r'```json\s*({.*?})\s*```', response, re.DOTALL)
        if not json_match:
            print("No JSON found in the response.")
            return None

        json_str = json_match.group(1)
        parsed = json.loads(json_str)

        # Validate the parsed response based on the action type
        action = parsed.get("action")
        if action not in action_fields:
            print(f"Unknown action: {action}")
            return None

        required_fields = action_fields[action]
        if all(key in parsed for key in required_fields):
            return parsed
        else:
            print(f"Missing or ambiguous fields in the parsed response for action: {action}")
            return None
    except Exception as e:
        print(f"Error parsing command via NLP: {e}")
    return None

# def parse_command_nlp(text: str):
#     """
#     Use OpenAI's language model to parse the user's command.
#     Expected keys: action, amount, from_token, to_token, from_chain, to_chain.
#     """
#     prompt = f"""
# Extract the following information from the command below:
# - action: either "transfer" or "migrate"
# - amount: a numeric value
# - from_token: the token symbol being sent from the source chain (e.g., AVAX, ETH)
# - to_token: the token symbol to be received on the destination chain (e.g., USDC, DAI)
# - from_chain: source blockchain name (e.g., Avalanche, Ethereum)
# - to_chain: destination blockchain name (e.g., Base, Binance Smart Chain)

# Command: "{text}"
# If any field is missing or ambiguous, return null.

# Return the result as a JSON object with keys: action, amount, from_token, to_token, from_chain, to_chain.
# """
#     try:
#         print(f"user balance: {deepseek_client.user_balance()}")
#         response = deepseek_client.chat_completion(prompt=prompt)
#         json_match = re.search(r'```json\s*({.*?})\s*```', response, re.DOTALL)
#         if not json_match:
#             print("No JSON found in the response.")
#             return None

#         json_str = json_match.group(1)
#         parsed = json.loads(json_str)
#         if all(key in parsed for key in ["action", "amount", "from_token", "to_token", "from_chain", "to_chain"]):
#             return parsed
#         else:
#             print("Missing or ambiguous fields in the parsed response")
#             return None
#     except Exception as e:
#         print(f"Error parsing command via NLP: {e}")
#     return None