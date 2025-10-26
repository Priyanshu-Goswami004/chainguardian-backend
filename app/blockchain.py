from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv()

class BlockchainClient:
    def __init__(self):
        try:
            self.w3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
            
            if not self.w3.is_connected():
                raise Exception("Cannot connect to blockchain")
            
            self.account = self.w3.eth.account.from_key(os.getenv('PRIVATE_KEY'))
            
            # Load contract ABI
            abi_path = os.path.join(os.path.dirname(__file__), '../contract_abi.json')
            if os.path.exists(abi_path):
                with open(abi_path, 'r') as f:
                    contract_abi = json.load(f)
                
                self.contract = self.w3.eth.contract(
                    address=os.getenv('CONTRACT_ADDRESS'),
                    abi=contract_abi
                )
                print("✓ Blockchain client initialized")
            else:
                print("⚠ Contract ABI not found")
                self.contract = None
                
        except Exception as e:
            print(f"⚠ Blockchain initialization error: {e}")
            raise
    
    def register_alert(self, sig_hash, flagged_address, ipfs_uri, severity):
        """Register alert on blockchain"""
        if not self.contract:
            raise Exception("Contract not initialized")
        
        sig_hash_bytes = bytes.fromhex(sig_hash)
        
        tx = self.contract.functions.registerAlert(
            sig_hash_bytes,
            flagged_address,
            ipfs_uri,
            severity
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return receipt['transactionHash'].hex()
    
    def get_alert(self, sig_hash):
        """Get alert from blockchain"""
        if not self.contract:
            raise Exception("Contract not initialized")
        
        sig_hash_bytes = bytes.fromhex(sig_hash)
        alert = self.contract.functions.getAlert(sig_hash_bytes).call()
        
        return {
            'sigHash': alert[0].hex(),
            'flagged': alert[1],
            'timestamp': alert[2],
            'ipfsURI': alert[3],
            'reporter': alert[4]
        }