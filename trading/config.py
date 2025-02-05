# GMX v2 contract addresses
GMX_CONTRACTS = {
    "reader": "0x38d91ED96283d62182Fc6d990C24097A918a4d9b",
    "position_router": "0x6f2800d4fb11d45963ac8EA6f036b63E77176E0F",
    "router": "0x7452c558d45f8afC8c83dAe62C3f8A5BE19c71f6",
    "vault": "0x489ee077994B6658eAfA855C308275EAd8097C4A"
}

# Available trading pairs
TRADING_PAIRS = {
    "AVAX-USD": {
        "token": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        "decimals": 18,
        "min_collateral": 10
    },
    "ETH-USD": {
        "token": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
        "decimals": 18,
        "min_collateral": 10
    },
    "BTC-USD": {
        "token": "0x152b9d0FdC40C096757F570A51E494bd4b943E50",
        "decimals": 8,
        "min_collateral": 10
    },
    "USDC-USD": {
        "token": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "decimals": 6,
        "min_collateral": 10
    }
}

# RPC endpoint
RPC_URL = 'https://api.avax.network/ext/bc/C/rpc'

# GMX Subgraph endpoint
SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/gmx-io/gmx-avalanche"