from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        try:
            mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
            db_name = os.getenv('DATABASE_NAME', 'chainguardian')
            
            print(f"🔗 Connecting to MongoDB: {mongo_url}")
            print(f"📂 Database: {db_name}")
            
            self.client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            
            # Test connection
            self.client.server_info()
            
            self.db = self.client[db_name]
            self.transactions = self.db['transactions']
            self.alerts = self.db['alerts']
            self.models = self.db['models']
            
            # Create indexes
            self.transactions.create_index('txHash')
            self.alerts.create_index('sigHash')
            
            print("✓ Database connected successfully")
            print(f"📊 Existing transactions: {self.transactions.count_documents({})}")
            print(f"⚠️  Existing alerts: {self.alerts.count_documents({})}")
            
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            raise
    
    def save_transaction(self, tx_data):
        """Save transaction to database"""
        try:
            result = self.transactions.insert_one(tx_data)
            print(f"✅ Saved transaction: {tx_data.get('txHash')} - {tx_data.get('label')}")
            return result
        except Exception as e:
            print(f"❌ Error saving transaction: {e}")
            raise
    
    def save_alert(self, alert_data):
        """Save alert to database"""
        try:
            result = self.alerts.insert_one(alert_data)
            print(f"⚠️  Saved alert: {alert_data.get('sigHash')}")
            return result
        except Exception as e:
            print(f"❌ Error saving alert: {e}")
            raise
    
    def get_transactions(self, limit=50):
        """Get recent transactions"""
        try:
            txs = list(self.transactions.find().sort('timestamp', -1).limit(limit))
            for tx in txs:
                tx['_id'] = str(tx['_id'])
            print(f"📋 Retrieved {len(txs)} transactions")
            return txs
        except Exception as e:
            print(f"❌ Error getting transactions: {e}")
            return []
    
    def get_alerts(self, limit=50):
        """Get recent alerts"""
        try:
            alerts = list(self.alerts.find().sort('timestamp', -1).limit(limit))
            for alert in alerts:
                alert['_id'] = str(alert['_id'])
            print(f"🚨 Retrieved {len(alerts)} alerts")
            return alerts
        except Exception as e:
            print(f"❌ Error getting alerts: {e}")
            return []
    
    def get_alert_by_hash(self, sig_hash):
        """Get alert by signature hash"""
        try:
            alert = self.alerts.find_one({'sigHash': sig_hash})
            if alert:
                alert['_id'] = str(alert['_id'])
            return alert
        except Exception as e:
            print(f"❌ Error getting alert: {e}")
            return None
    
    def get_statistics(self):
        """Get system statistics"""
        try:
            total_txs = self.transactions.count_documents({})
            fraud_detected = self.transactions.count_documents({'label': 'suspicious'})
            active_alerts = self.alerts.count_documents({'status': 'active'})
            
            if total_txs > 0:
                accuracy = ((total_txs - fraud_detected) / total_txs) * 100
            else:
                accuracy = 0
            
            stats = {
                'totalTx': total_txs,
                'fraudDetected': fraud_detected,
                'accuracy': round(accuracy, 2),
                'activeAlerts': active_alerts
            }
            
            print(f"📊 Stats: {stats}")
            return stats
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {
                'totalTx': 0,
                'fraudDetected': 0,
                'accuracy': 0,
                'activeAlerts': 0
            }