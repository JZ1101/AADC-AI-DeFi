from openai import OpenAI
from dotenv import load_dotenv
import json
import os
import re

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------
# NLP Processing using OpenAI
# ------------------------------

def parse_command_nlp(text: str):
    """
    Use OpenAI's language model to parse the user's command.
    Expected keys vary based on the action type.
    """
    # Define possible actions and their required fields
    action_fields = {
        "transfer": ["amount", "from_token", "to_token", "from_chain", "to_chain"],
        "AvaYield_get_total_deposits": [],
        "AvaYield_get_rewards": [],
        "AvaYield_get_leverage": [],
        "AvaYield_deposit": ["amount_avax"],
        "AvaYield_withdraw": ["amount_shares"],
        "AvaYield_reinvest": []
    }

    # Generate the prompt dynamically based on the action type
    prompt = f"""
Extract the following information from the command below:
- action: one of {list(action_fields.keys())}
- fields: depending on the action, extract the relevant fields from the command.

For each action, the required fields are:
- transfer: amount, from_token, to_token, from_chain, to_chain
- AvaYield_get_total_deposits: no fields required
- AvaYield_get_rewards: no fields required
- AvaYield_get_leverage: no fields required
- AvaYield_deposit: amount_avax
- AvaYield_withdraw: amount_shares
- AvaYield_reinvest: no fields required

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
        # Call OpenAI's ChatCompletion API
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use the appropriate model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from natural language commands."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response content
        response_content = response.choices[0].message.content
        # Try to parse the JSON directly from the response
        try:
            # Attempt to find JSON in the response (with or without triple backticks)
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                print("Parsed JSON:", parsed)

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
            else:
                print("No JSON found in the response.")
                return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    except Exception as e:
        print(f"Error parsing command via NLP: {e}")
    return None