# AI Agents for DeFi & Cross-Chain Operations
## Main Development started on Feb 8, 202 
## The project has been extended to include voice commands and a more user friendly interface. 
Cross-Chain Migration Assistant
  - 1.1 Develop an AI agent that simplifies moving assets across chains through **natural language commands**
  - 1.2 Automate the complete bridging and swapping process
  - 1.3 Find the optimal path for the user to move assets across chains.
  
DeFi Position Management
  - 2.1 Create an AI agent that can execute DeFi operations through **natural language commands**
  - 2.2 Handle yield farming with BENQI through chat interface
  - 2.3 Implement safety checks and transaction previews before execution

## Bridges Integrated

| Name   |  Status  |
|:-----  |:--------:|
| Across | ✔️ |
| Celer CBridge| ✔️ |
| Circle CCTP     | ✔️ |
| Connext     | ✔️ |
| Hop     | ✔️ |
| Hyphen    | ✔️ |
| Refuel    | ✔️ |
| Stargate     | ✔️ |
| Symbiosis     | ✔️ |
| Synapse     | ✔️ |

## Chains Integrated

| Name   | Status  |  
|--------|:------:|  
| Arbitrum | ✔️ |  
| Aurora | ✔️ |  
| Avalanche | ✔️ |  
| Base | ✔️ |  
| Binance Smart Chain (BSC) | ✔️ |  
| Blast | ✔️ |  
| Ethereum | ✔️ |  
| Fantom | ✔️ |  
| Gnosis Chain | ✔️ |  
| Linea | ✔️ |  
| Mantle | ✔️ |  
| Optimism | ✔️ |  
| Polygon | ✔️ |  
| Polygon zkEVM | ✔️ |  
| Scroll | ✔️ |  
| zkSync Era | ✔️ |  

## DEX Integrated For Cross Chain Atomic Swap

| Name   |  Status  |
|:-----  |:--------:|
| 1inch | ✔️ |
| 0x | ✔️ |

## 🚀 DeFi - Yield Farming with BENQI

| **Feature**  | **Status** |
|:------------|:--------:|
| **Deposit**  | ✔️ |
| **Withdraw** | ✔️ |
| **Reinvest** | ✔️ |
| **Contract Info** | ✔️ |

## 🤖 Bot Abilities

| **Feature**  | **Status** |
|:------------|:--------:|
| **Multi-language Support**  | ✔️ |
| **Telegram Bot Integration** | ✔️ |
| **DeFi Commands (Swap, Withdraw, APR Check, etc.)** | ✔️ |
| **Transaction previews** | ✔️ |

## Implementation Guide

### Step 1: Setting Up the Environment 🚀
1. Clone the repository:
  ```bash
  git clone https://github.com/your-repo/ETH-Oxford-2025.git
  cd ETH-Oxford-2025
  ```

2. Install dependencies:
  ```bash
  pip install uv
  cd src
  uv pip install .
  ```

### Step 2: Configuring the Environment Variables 🔧

Create a `.env` file in the root directory of the project and add the following parameters:
```plaintext
TELEGRAM_TOKEN = "your-telegram-token" # Use Telegram BotFather to create a Telegram bot token
OPENAI_API_KEY = "your-openai-api-key" # Obtain from https://platform.openai.com/api-keys
INFURA_API_KEY = "your-infura-api-key" # Obtain from https://developer.metamask.io/
WEB3_PROVIDER = "your-web3-provider" # Obtain from https://developer.metamask.io/ too, but choose the Infura RPC key
BUNGEE_API_KEY  = "72a5b4b0-e727-48be-8aa1-5da9d62fe635" # Use the BUNGEE test key, Obtain from https://docs.bungee.exchange/bungee-manual/socket-api/introduction
```

### Step 3: Start test in the telegram bot
```bash
cd src
uv run bot.py  
```
1. Open the Telegram app and search for your bot using the bot username you created with BotFather.
2. Start a conversation with your bot by typing `/start`.
3. Follow the on-screen instructions to interact with the bot and test its functionalities.
