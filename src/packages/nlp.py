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
    Expected keys: action, amount, from_token, to_token, from_chain, to_chain.
    """
    prompt = f"""
Extract the following information from the command below:
- action: either "transfer" or "migrate"
- amount: a numeric value
- from_token: the token symbol being sent from the source chain (e.g., AVAX, ETH)
- to_token: the token symbol to be received on the destination chain (e.g., USDC, DAI)
- from_chain: source blockchain name (e.g., Avalanche, Ethereum)
- to_chain: destination blockchain name (e.g., Base, Binance Smart Chain)

Command: "{text}"
If any field is missing or ambiguous, return null.

Return the result as a JSON object with keys: action, amount, from_token, to_token, from_chain, to_chain.
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
        if all(key in parsed for key in ["action", "amount", "from_token", "to_token", "from_chain", "to_chain"]):
            return parsed
        else:
            print("Missing or ambiguous fields in the parsed response")
            return None
    except Exception as e:
        print(f"Error parsing command via NLP: {e}")
    return None