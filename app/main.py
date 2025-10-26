from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os
from datetime import datetime
import hashlib
import json

# Add ML engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ml_engine'))

try:
    from predict import FraudDetector
    ML_AVAILABLE = True
    print("✓ ML Engine loaded")
except Exception as e:
    ML_AVAILABLE = False
    print(f"⚠ ML Engine not available: {e}")

# Fixed imports with relative paths
from .database import Database
from .blockchain import BlockchainClient

app = FastAPI(
    title="ChainGuardian API",
    version="1.0.0",
    description="Blockchain Fraud Detection System"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
print("🚀 Initializing components...")

db = Database()

try:
    blockchain = BlockchainClient()
    BLOCKCHAIN_AVAILABLE = True
except Exception as e:
    BLOCKCHAIN_AVAILABLE = False
    print(f"⚠ Blockchain not available: {e}")

if ML_AVAILABLE:
    try:
        fraud_detector = FraudDetector()
    except Exception as e:
        ML_AVAILABLE = False
        print(f"⚠ Could not load ML models: {e}")

# Pydantic models
class Transaction(BaseModel):
    txHash: str
    from_address: str
    to_address: str
    amount: float
    timestamp: Optional[str] = None
    gas_price: Optional[float] = 50.0
    gas_used: Optional[int] = 21000

@app.get("/")
async def root():
    return {
        "message": "ChainGuardian API",
        "version": "1.0.0",
        "status": "operational",
        "services": {
            "ml_engine": ML_AVAILABLE,
            "blockchain": BLOCKCHAIN_AVAILABLE,
            "database": True
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/tx")
async def process_transaction(tx: Transaction, background_tasks: BackgroundTasks):
    """Process incoming transaction and detect fraud"""
    print(f"📥 Processing transaction: {tx.txHash}")
    
    try:
        tx_data = {
            'from': tx.from_address,
            'to': tx.to_address,
            'amount': tx.amount,
            'timestamp': tx.timestamp or datetime.now().isoformat(),
            'gas_price': tx.gas_price,
            'gas_used': tx.gas_used
        }
        
        # Get fraud prediction
        if ML_AVAILABLE:
            prediction = fraud_detector.predict(tx_data)
        else:
            # Fallback prediction
            prediction = {
                'risk_score': 0.1,
                'label': 'normal',
                'explanation': {'top_features': [], 'model_scores': {}},
                'model_version': 'N/A',
                'model_hash': 'N/A'
            }
        
        # Store transaction IN DATABASE
        tx_record = {
            'txHash': tx.txHash,
            'from': tx.from_address,
            'to': tx.to_address,
            'amount': tx.amount,
            'timestamp': tx_data['timestamp'],
            'riskScore': prediction['risk_score'],
            'label': prediction['label'],
            'modelVersion': prediction['model_version'],
            'processed_at': datetime.now().isoformat()
        }
        db.save_transaction(tx_record)  # DATABASE SAVE
        
        alert_registered = False
        signature_hash = None
        
        if prediction['label'] == 'suspicious':
            fraud_signature = {
                'txHash': tx.txHash,
                'flaggedAddress': tx.from_address,
                'riskScore': prediction['risk_score'],
                'timestamp': tx_data['timestamp'],
                'modelVersion': prediction['model_version'],
                'explanation': prediction['explanation']
            }
            
            signature_hash = hashlib.sha256(
                json.dumps(fraud_signature, sort_keys=True).encode()
            ).hexdigest()
            
            severity = 2 if prediction['risk_score'] >= 0.8 else 1
            
            # Save alert IN DATABASE
            alert_record = {
                'sigHash': signature_hash,
                'txHash': tx.txHash,
                'flaggedAddress': tx.from_address,
                'riskScore': prediction['risk_score'],
                'severity': severity,
                'explanation': prediction['explanation'],
                'timestamp': datetime.now().isoformat(),
                'status': 'active'
            }
            db.save_alert(alert_record)  # DATABASE SAVE
            alert_registered = True
            
            print(f"⚠️  FRAUD DETECTED: {tx.txHash} - Risk: {prediction['risk_score']:.2f}")
        else:
            print(f"✅ Normal transaction: {tx.txHash} - Risk: {prediction['risk_score']:.2f}")
        
        return {
            'success': True,
            'txHash': tx.txHash,
            'riskScore': prediction['risk_score'],
            'label': prediction['label'],
            'explanation': prediction['explanation'],
            'alertRegistered': alert_registered,
            'signatureHash': signature_hash
        }
        
    except Exception as e:
        print(f"❌ Error processing transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/txs")
async def get_transactions(limit: int = 50):
    """Get recent transactions"""
    txs = db.get_transactions(limit)
    return {'transactions': txs, 'count': len(txs)}

@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts"""
    alerts = db.get_alerts(limit)
    return {'alerts': alerts, 'count': len(alerts)}

@app.get("/api/alerts/{sig_hash}")
async def get_alert_detail(sig_hash: str):
    """Get alert details"""
    alert = db.get_alert_by_hash(sig_hash)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    stats = db.get_statistics()
    return stats

@app.get("/api/model/status")
async def get_model_status():
    """Get ML model information"""
    if ML_AVAILABLE:
        return fraud_detector.metadata
    return {"error": "ML engine not available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)