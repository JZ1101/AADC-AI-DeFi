import unittest
from unittest import mock
from web3 import Web3
from decimal import Decimal
import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your main module
from main import withdraw_everything, only_claim_rewards, main
try:
    from AvaYieldInteractor import AvaYieldInteractor
except ImportError:
    print("Warning: AvaYieldInteractor module not found. Tests will run with mocks only.")

class TestAvaYieldStrategy(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.rpc_url = "https://api.avax.network/ext/bc/C/rpc"
        self.contract_address = "0x8B414448de8B609e96bd63Dcf2A8aDbd5ddf7fdd"
        self.private_key = "test_private_key"
        
        # Create mock strategy
        self.strategy = mock.Mock()
        self.strategy.w3 = mock.Mock()
        self.strategy.contract = mock.Mock()
        self.strategy.account = mock.Mock()
        
        # Set up Web3 mock
        self.w3_mock = mock.Mock()
        self.strategy.w3 = self.w3_mock

    def test_withdraw_everything_with_rewards(self):
        """Test withdraw_everything when there are rewards to reinvest"""
        # Set up mock returns
        self.strategy.get_my_rewards.return_value = Web3.to_wei(0.1, 'ether')
        self.strategy.get_my_balance.return_value = Web3.to_wei(1.0, 'ether')
        
        # Execute withdraw_everything
        withdraw_everything(self.strategy)
        
        # Verify all expected methods were called
        self.strategy.reinvest.assert_called_once()
        self.strategy.withdraw.assert_called_once_with(Web3.to_wei(1.0, 'ether'))
        
    def test_withdraw_everything_no_rewards(self):
        """Test withdraw_everything when there are no rewards"""
        # Set up mock returns
        self.strategy.get_my_rewards.return_value = 0
        self.strategy.get_my_balance.return_value = Web3.to_wei(1.0, 'ether')
        
        # Execute withdraw_everything
        withdraw_everything(self.strategy)
        
        # Verify behavior
        self.strategy.reinvest.assert_not_called()
        self.strategy.withdraw.assert_called_once_with(Web3.to_wei(1.0, 'ether'))

    def test_withdraw_everything_no_shares(self):
        """Test withdraw_everything when user has no shares"""
        # Set up mock returns
        self.strategy.get_my_rewards.return_value = 0
        self.strategy.get_my_balance.return_value = 0
        
        # Execute withdraw_everything
        withdraw_everything(self.strategy)
        
        # Verify behavior
        self.strategy.reinvest.assert_not_called()
        self.strategy.withdraw.assert_not_called()

    def test_only_claim_rewards_with_rewards(self):
        """Test only_claim_rewards when there are rewards to claim"""
        # Set up mock returns
        self.strategy.get_my_rewards.return_value = Web3.to_wei(0.1, 'ether')
        self.strategy.get_pool_deposits.return_value = Web3.to_wei(10.0, 'ether')
        self.strategy.contract.functions.totalSupply().call.return_value = Web3.to_wei(5.0, 'ether')
        
        # Execute only_claim_rewards
        only_claim_rewards(self.strategy)
        
        # Calculate expected shares to withdraw
        expected_shares = (Web3.to_wei(0.1, 'ether') / Web3.to_wei(10.0, 'ether')) * Web3.to_wei(5.0, 'ether')
        
        # Verify behavior
        self.strategy.withdraw.assert_called_once_with(expected_shares)

    def test_only_claim_rewards_no_rewards(self):
        """Test only_claim_rewards when there are no rewards"""
        # Set up mock returns
        self.strategy.get_my_rewards.return_value = 0
        self.strategy.get_pool_deposits.return_value = Web3.to_wei(10.0, 'ether')
        self.strategy.contract.functions.totalSupply().call.return_value = Web3.to_wei(5.0, 'ether')
        
        # Execute only_claim_rewards
        only_claim_rewards(self.strategy)
        
        # Verify behavior
        self.strategy.withdraw.assert_not_called()

    def test_only_claim_rewards_empty_pool(self):
        """Test only_claim_rewards when pool is empty"""
        # Set up mock returns
        self.strategy.get_my_rewards.return_value = Web3.to_wei(0.1, 'ether')
        self.strategy.get_pool_deposits.return_value = 0
        self.strategy.contract.functions.totalSupply().call.return_value = 0
        
        # Execute only_claim_rewards
        only_claim_rewards(self.strategy)
        
        # Verify behavior
        self.strategy.withdraw.assert_not_called()

    @mock.patch('os.getenv')
    @mock.patch('main.AvaYieldInteractor')  # Changed the patch target
    def test_main_function_basic_setup(self, mock_interactor, mock_getenv):
        """Test main function basic setup without any operations"""
        # Set up environment variable mocks
        mock_getenv.side_effect = lambda x, default=None: {
            "PRIVATE_KEY": "test_private_key",
            "AVAYIELD_CONTRACT_ADDRESS": self.contract_address,
            "AVAX_RPC_URL": self.rpc_url,
            "TEST_DEPOSIT": "false",
            "TEST_WITHDRAW": "false",
            "TEST_REINVEST": "false"
        }.get(x, default)
        
        # Set up interactor mock
        mock_interactor.return_value = self.strategy
        
        # Execute main function
        main()
        
        # Verify AvaYieldInteractor was initialized correctly
        mock_interactor.assert_called_once_with(
            rpc_url=self.rpc_url,
            contract_address=self.contract_address,
            private_key="test_private_key"
        )

    @mock.patch('os.getenv')
    def test_main_function_missing_private_key(self, mock_getenv):
        """Test main function when private key is missing"""
        # Mock missing private key
        mock_getenv.return_value = None
        
        # Execute main function and verify it raises ValueError
        with self.assertRaises(ValueError):
            main()

if __name__ == '__main__':
    unittest.main()