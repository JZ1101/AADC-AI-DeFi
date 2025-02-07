import unittest
from unittest.mock import Mock, patch, mock_open
from web3 import Web3

# Create module level patches
@patch('YieldYakInteractor.Web3')
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
        self.file_patcher = patch('builtins.open', mock_open(read_data=self.mock_abi))
        self.mock_file = self.file_patcher.start()
        self.addCleanup(self.file_patcher.stop)

    def setup_web3_mock(self, mock_web3):
        """Setup Web3 mock with all necessary attributes"""
        # Setup mock Web3 instance
        mock_w3 = Mock()
        mock_w3.eth = Mock()
        mock_w3.eth.get_transaction_count = Mock(return_value=1)
        mock_w3.eth.gas_price = 20000000000
        mock_w3.eth.chain_id = 43114
        mock_w3.to_checksum_address = lambda x: x
        
        # Setup mock contract
        mock_contract = Mock()
        mock_w3.eth.contract.return_value = mock_contract
        
        # Setup Web3 class mock
        mock_web3.HTTPProvider = Mock(return_value=Mock())
        mock_web3.return_value = mock_w3
        
        return mock_w3, mock_contract

    def test_initialization(self, mock_web3):
        """Test contract initialization"""
        mock_w3, _ = self.setup_web3_mock(mock_web3)
        
        from YieldYakInteractor import YieldYakInteractor
        strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            private_key=self.private_key,
            contract_address=self.contract_address
        )
        
        self.mock_file.assert_called_once_with("abis/farm_abi.json", "r")
        mock_web3.HTTPProvider.assert_called_once_with(self.rpc_url)

    def test_check_reward(self, mock_web3):
        """Test checking rewards"""
        mock_w3, mock_contract = self.setup_web3_mock(mock_web3)
        expected_reward = 1000
        
        # Mock the checkReward function
        mock_function = Mock()
        mock_function.call.return_value = expected_reward
        mock_contract.functions.checkReward = Mock(return_value=mock_function)
        
        from YieldYakInteractor import YieldYakInteractor
        strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            private_key=self.private_key,
            contract_address=self.contract_address
        )
        
        result = strategy.check_reward()
        self.assertEqual(result, expected_reward)
        mock_contract.functions.checkReward.assert_called_once()

    def test_deposit(self, mock_web3):
        """Test deposit function"""
        mock_w3, mock_contract = self.setup_web3_mock(mock_web3)
        deposit_amount = 1000

        # Mock deposit function
        mock_deposit_func = Mock()
        mock_tx = {
            'from': "0x" + "4" * 40,
            'nonce': 1,
            'gas': 2000000,
            'gasPrice': 20000000000,
            'value': 0
        }
        mock_deposit_func.build_transaction.return_value = mock_tx
        mock_contract.functions.deposit = Mock(return_value=mock_deposit_func)

        # Mock transaction handling
        mock_signed_tx = Mock()
        mock_w3.eth.account.sign_transaction = Mock(return_value=mock_signed_tx)
        mock_w3.eth.send_raw_transaction = Mock(return_value=b'txhash')
        mock_w3.eth.wait_for_transaction_receipt = Mock(return_value={'status': 1})
        
        from YieldYakInteractor import YieldYakInteractor
        strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            private_key=self.private_key,
            contract_address=self.contract_address
        )
        
        result = strategy.deposit(deposit_amount)
        mock_contract.functions.deposit.assert_called_once_with(deposit_amount)

    def test_withdraw(self, mock_web3):
        """Test withdraw function"""
        mock_w3, mock_contract = self.setup_web3_mock(mock_web3)
        withdraw_amount = 500

        # Mock withdraw function
        mock_withdraw_func = Mock()
        mock_tx = {
            'from': "0x" + "4" * 40,
            'nonce': 1,
            'gas': 2000000,
            'gasPrice': 20000000000,
            'value': 0
        }
        mock_withdraw_func.build_transaction.return_value = mock_tx
        mock_contract.functions.withdraw = Mock(return_value=mock_withdraw_func)

        # Mock transaction handling
        mock_signed_tx = Mock()
        mock_w3.eth.account.sign_transaction = Mock(return_value=mock_signed_tx)
        mock_w3.eth.send_raw_transaction = Mock(return_value=b'txhash')
        mock_w3.eth.wait_for_transaction_receipt = Mock(return_value={'status': 1})
        
        from YieldYakInteractor import YieldYakInteractor
        strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            private_key=self.private_key,
            contract_address=self.contract_address
        )
        
        result = strategy.withdraw(withdraw_amount)
        mock_contract.functions.withdraw.assert_called_once_with(withdraw_amount)

    def test_no_private_key_error(self, mock_web3):
        """Test error when no private key is provided"""
        mock_w3, _ = self.setup_web3_mock(mock_web3)
        
        from YieldYakInteractor import YieldYakInteractor
        strategy = YieldYakInteractor(
            rpc_url=self.rpc_url,
            contract_address=self.contract_address
        )
        
        with self.assertRaises(ValueError):
            strategy.deposit(1000)

if __name__ == '__main__':
    unittest.main()