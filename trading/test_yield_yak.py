import pytest
from unittest.mock import Mock, patch
from web3 import Web3
from decimal import Decimal
import json

from YieldYakManager import YieldYakManager

# Test constants
TEST_RPC_URL = "http://localhost:8545"
TEST_WALLET = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TEST_PRIVATE_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
TEST_FARM_ID = 0
TEST_AMOUNT = 1000000000000000000  # 1 token with 18 decimals

@pytest.fixture
def mock_web3():
    with patch('web3.Web3', autospec=True) as mock:
        mock.HTTPProvider = Mock()
        mock.eth = Mock()
        mock.eth.contract = Mock()
        yield mock

@pytest.fixture
def yield_yak(mock_web3):
    with patch('builtins.open', create=True) as mock_open:
        # Mock reading contract ABIs
        mock_open.return_value.__enter__.return_value.read.return_value = '{}'
        manager = YieldYakManager(TEST_RPC_URL)
        return manager

@pytest.mark.asyncio
async def test_get_farms(yield_yak):
    # Mock farm data
    mock_farm = ['Test Farm', '0x1234...', 1000000, 100]
    yield_yak.router.functions.farmCount.return_value.call.return_value = 1
    yield_yak.router.functions.getFarm.return_value.call.return_value = mock_farm
    
    # Mock APY calculation
    with patch.object(yield_yak, 'get_farm_apy', return_value=10.5):
        farms = await yield_yak.get_farms()
        
        assert len(farms) == 1
        assert farms[0]['name'] == 'Test Farm'
        assert farms[0]['apy'] == 10.5

@pytest.mark.asyncio
async def test_get_user_deposits(yield_yak):
    # Mock dependencies
    mock_farm = {
        'id': TEST_FARM_ID,
        'name': 'Test Farm',
        'token': '0x1234...',
        'tvl': 1000000,
        'apy': 10.5
    }
    
    with patch.object(yield_yak, 'get_farms', return_value=[mock_farm]):
        with patch.object(yield_yak, 'get_token_value_usd', return_value=100.0):
            yield_yak.router.functions.getUserBalance.return_value.call.return_value = TEST_AMOUNT
            
            deposits = await yield_yak.get_user_deposits(TEST_WALLET)
            
            assert len(deposits) == 1
            assert deposits[0]['farm_id'] == TEST_FARM_ID
            assert deposits[0]['balance'] == TEST_AMOUNT
            assert deposits[0]['balance_usd'] == 100.0

@pytest.mark.asyncio
async def test_deposit(yield_yak):
    # Mock transaction data
    mock_tx_hash = '0x123...'
    yield_yak.w3.eth.get_transaction_count.return_value = 1
    yield_yak.w3.eth.account.sign_transaction.return_value.rawTransaction = b'raw_tx'
    yield_yak.w3.eth.send_raw_transaction.return_value.hex.return_value = mock_tx_hash
    
    tx_hash = await yield_yak.deposit(
        TEST_WALLET,
        TEST_FARM_ID,
        TEST_AMOUNT,
        TEST_PRIVATE_KEY
    )
    
    assert tx_hash == mock_tx_hash
    yield_yak.router.functions.deposit.assert_called_once_with(TEST_FARM_ID, TEST_AMOUNT)

@pytest.mark.asyncio
async def test_withdraw(yield_yak):
    # Mock transaction data
    mock_tx_hash = '0x123...'
    yield_yak.w3.eth.get_transaction_count.return_value = 1
    yield_yak.w3.eth.account.sign_transaction.return_value.rawTransaction = b'raw_tx'
    yield_yak.w3.eth.send_raw_transaction.return_value.hex.return_value = mock_tx_hash
    
    tx_hash = await yield_yak.withdraw(
        TEST_WALLET,
        TEST_FARM_ID,
        TEST_AMOUNT,
        TEST_PRIVATE_KEY
    )
    
    assert tx_hash == mock_tx_hash
    yield_yak.router.functions.withdraw.assert_called_once_with(TEST_FARM_ID, TEST_AMOUNT)

@pytest.mark.asyncio
async def test_claim_rewards(yield_yak):
    # Mock transaction data
    mock_tx_hash = '0x123...'
    yield_yak.w3.eth.get_transaction_count.return_value = 1
    yield_yak.w3.eth.account.sign_transaction.return_value.rawTransaction = b'raw_tx'
    yield_yak.w3.eth.send_raw_transaction.return_value.hex.return_value = mock_tx_hash
    
    tx_hash = await yield_yak.claim_rewards(
        TEST_WALLET,
        TEST_FARM_ID,
        TEST_PRIVATE_KEY
    )
    
    assert tx_hash == mock_tx_hash
    yield_yak.router.functions.harvest.assert_called_once_with(TEST_FARM_ID)

@pytest.mark.asyncio
async def test_get_farm_apy(yield_yak):
    # Mock farm metrics
    mock_metrics = [0, 1000000, 100000]  # Format: [unknown, tvl, rewards_rate]
    yield_yak.router.functions.getFarmMetrics.return_value.call.return_value = mock_metrics
    
    apy = await yield_yak.get_farm_apy(TEST_FARM_ID)
    
    expected_apy = (mock_metrics[2] / mock_metrics[1]) * 365 * 100
    assert apy == expected_apy

@pytest.mark.asyncio
async def test_get_token_value_usd(yield_yak):
    # Mock token data
    mock_price = 1000000  # $1.00 with 6 decimals
    mock_decimals = 18
    
    yield_yak.router.functions.getTokenPrice.return_value.call.return_value = mock_price
    yield_yak.w3.eth.contract().functions.decimals.return_value.call.return_value = mock_decimals
    
    value = await yield_yak.get_token_value_usd('0x1234...', TEST_AMOUNT)
    
    expected_value = (TEST_AMOUNT * mock_price) / (10 ** mock_decimals)
    assert value == expected_value

@pytest.mark.asyncio
async def test_error_handling(yield_yak):
    # Test error handling for get_farms
    yield_yak.router.functions.farmCount.side_effect = Exception("RPC Error")
    
    with pytest.raises(Exception) as exc_info:
        await yield_yak.get_farms()
    assert "Error fetching farms" in str(exc_info.value)