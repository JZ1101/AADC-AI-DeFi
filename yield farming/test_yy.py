import unittest
from unittest.mock import Mock, patch, mock_open
from web3 import Web3
from yieldyak import YieldYakInteractor

class TestYieldYakInteractor(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.rpc_url = "https://api.avax.network/ext/bc/C/rpc"
        self.private_key = "0x" + "1" * 64  # Dummy private key
        self.contract_address = "0x0C4684086914D5B1525bf16c62a0FF8010AB991A"
        
        # Mock ABI content
        self.mock_abi = '''[
            {
                "inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}],
                "name": "deposit",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "checkReward",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]'''

        # Create mock for file reading
        self.mock_file = mock_open(read_data=self.mock_abi)
        
        # Setup patches
        self.web3_patcher = patch('web3.Web3')
        self.file_patcher = patch('builtins.open', self.mock_file)
        
        # Start patches
        self.mock_web3 = self.web3_patcher.start()
        self.mock_file_open = self.file_patcher.start()
        
        # Setup mock Web3 instance
        self.w3 = Mock()
        self.mock_web3.HTTPProvider.return_value = Mock()
        self.mock_web3.return_value = self.w3
        
        # Setup mock account
        self.mock_account = Mock()
        self.mock_account.address = "0x" + "4" * 40
        
        # Initialize strategy
        self.strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            private_key=self.private_key,
            contract_address=self.contract_address
        )
        
        # Mock the account
        self.strategy.account = self.mock_account

    def tearDown(self):
        """Clean up after each test"""
        self.web3_patcher.stop()
        self.file_patcher.stop()

    def test_initialization(self):
        """Test contract initialization"""
        self.assertEqual(self.strategy.w3, self.w3)
        self.mock_file.assert_called_once_with("abis/farm_abi.json", "r")

    def test_check_reward(self):
        """Test checking rewards"""
        expected_reward = 1000
        
        # Mock the checkReward function
        mock_function = Mock()
        mock_function.call.return_value = expected_reward
        self.strategy.contract.functions.checkReward = Mock(return_value=mock_function)

        # Call and verify
        result = self.strategy.check_reward()
        self.assertEqual(result, expected_reward)
        self.strategy.contract.functions.checkReward.assert_called_once()

    def test_deposit(self):
        """Test deposit function"""
        deposit_amount = 1000

        # Mock transaction parameters
        self.w3.eth.get_transaction_count.return_value = 1
        self.w3.eth.gas_price = 20000000000

        # Mock deposit function
        mock_deposit_func = Mock()
        mock_tx = {
            'from': self.mock_account.address,
            'nonce': 1,
            'gas': 2000000,
            'gasPrice': 20000000000,
            'value': 0
        }
        mock_deposit_func.build_transaction.return_value = mock_tx
        self.strategy.contract.functions.deposit = Mock(return_value=mock_deposit_func)

        # Mock transaction signing and sending
        mock_signed_tx = Mock()
        self.mock_account.sign_transaction = Mock(return_value=mock_signed_tx)
        self.w3.eth.send_raw_transaction = Mock(return_value=b'txhash')
        self.w3.eth.wait_for_transaction_receipt = Mock(return_value={'status': 1})

        # Call deposit
        result = self.strategy.deposit(deposit_amount)

        # Verify calls
        self.strategy.contract.functions.deposit.assert_called_once_with(deposit_amount)
        self.mock_account.sign_transaction.assert_called_once_with(mock_tx)
        self.w3.eth.send_raw_transaction.assert_called_once()
        self.w3.eth.wait_for_transaction_receipt.assert_called_once_with(b'txhash')

    def test_withdraw(self):
        """Test withdraw function"""
        withdraw_amount = 500

        # Mock transaction parameters
        self.w3.eth.get_transaction_count.return_value = 1
        self.w3.eth.gas_price = 20000000000

        # Mock withdraw function
        mock_withdraw_func = Mock()
        mock_tx = {
            'from': self.mock_account.address,
            'nonce': 1,
            'gas': 2000000,
            'gasPrice': 20000000000,
            'value': 0
        }
        mock_withdraw_func.build_transaction.return_value = mock_tx
        self.strategy.contract.functions.withdraw = Mock(return_value=mock_withdraw_func)

        # Mock transaction signing and sending
        mock_signed_tx = Mock()
        self.mock_account.sign_transaction = Mock(return_value=mock_signed_tx)
        self.w3.eth.send_raw_transaction = Mock(return_value=b'txhash')
        self.w3.eth.wait_for_transaction_receipt = Mock(return_value={'status': 1})

        # Call withdraw
        result = self.strategy.withdraw(withdraw_amount)

        # Verify calls
        self.strategy.contract.functions.withdraw.assert_called_once_with(withdraw_amount)
        self.mock_account.sign_transaction.assert_called_once_with(mock_tx)
        self.w3.eth.send_raw_transaction.assert_called_once()
        self.w3.eth.wait_for_transaction_receipt.assert_called_once_with(b'txhash')

    def test_no_private_key_error(self):
        """Test error when no private key is provided"""
        strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            contract_address=self.contract_address
        )
        
        with self.assertRaises(ValueError):
            strategy.deposit(1000)

if __name__ == '__main__':
    unittest.main()