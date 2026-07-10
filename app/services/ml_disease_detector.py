"""
ML-Based Disease Detection for Smart Pastoralism
Combines multiple ML approaches for early disease prediction
"""
import numpy as np
import pandas as pd
import sqlite3
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from app.config import settings

# ML Libraries (with fallback if not installed)
try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️  scikit-learn not installed. Run: pip install scikit-learn")


class MLDiseaseDetector:
    """
    Multi-model disease detection system:
    1. Anomaly Detection - Detects unusual patterns
    2. Disease Classification - Predicts specific diseases
    3. Time-Series Forecasting - Predicts future health trends
    """
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self.models_dir = "app/ml_models"
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Model instances
        self.anomaly_detector = None
        self.scaler = None
        self.disease_classifier = None
        self.feature_names = [
            'temperature', 'heart_rate', 'motion_magnitude',
            'temp_change_rate', 'hr_change_rate', 'motion_variability'
        ]
        
        # Disease labels (expanded to 12 conditions)
        self.disease_labels = [
            'healthy',
            'fever',
            'mastitis',
            'pneumonia',
            'metritis',
            'milk_fever',
            'ketosis',
            'bloat',
            'lameness',
            'laminitis',
            'heat_stress',
            'estrus',
            'calving_soon'
        ]
        
        if ML_AVAILABLE:
            self._load_or_train_models()
    
    def _load_or_train_models(self):
        """Load existing models or train new ones"""
        anomaly_path = os.path.join(self.models_dir, 'anomaly_detector.pkl')
        scaler_path = os.path.join(self.models_dir, 'scaler.pkl')
        
        if os.path.exists(anomaly_path) and os.path.exists(scaler_path):
            # Load existing models
            try:
                with open(anomaly_path, 'rb') as f:
                    self.anomaly_detector = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("✅ ML models loaded successfully")
            except Exception as e:
                print(f"⚠️  Error loading models: {e}")
                self._train_anomaly_detector()
        else:
            # Train new models
            self._train_anomaly_detector()
    
    def _train_anomaly_detector(self):
        """Train anomaly detection model on historical data"""
        try:
            print("🔄 Training anomaly detection model...")
            
            # Get historical data
            df = self._get_training_data()
            
            if df.empty or len(df) <100:
                print("⚠️  Insufficient data for training (need 100+ readings)")
                return
            
            # Prepare features
            features = self._extract_features(df)
            
            if features.empty:
                print("⚠️  No valid features extracted")
                return
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(features)
            
            # Train Isolation Forest
            self.anomaly_detector = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_estimators=100
            )
            self.anomaly_detector.fit(X_scaled)
            
            # Save models
            with open(os.path.join(self.models_dir, 'anomaly_detector.pkl'), 'wb') as f:
                pickle.dump(self.anomaly_detector, f)
            with open(os.path.join(self.models_dir, 'scaler.pkl'), 'wb') as f:
                pickle.dump(self.scaler, f)
            
            print(f"✅ Anomaly detector trained on {len(df)} readings")
            
        except Exception as e:
            print(f"❌ Error training anomaly detector: {e}")
    
    def _get_training_data(self, days: int = 30) -> pd.DataFrame:
        """Get historical data for training"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = f"""
                SELECT 
                    device_id,
                    temperature,
                    body_temperature,
                    ambient_temperature,
                    heart_rate,
                    motion_magnitude,
                    battery,
                    timestamp,
                    received_time
                FROM livestock_readings
                WHERE datetime(received_time) > datetime('now', '-{days} days')
                AND temperature IS NOT NULL
                AND heart_rate IS NOT NULL
                ORDER BY device_id, timestamp
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"❌ Error getting training data: {e}")
            return pd.DataFrame()
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract engineered features for ML"""
        if df.empty:
            return pd.DataFrame()
        
        features_list = []
        
        # Group by device to calculate temporal features
        for device_id, group in df.groupby('device_id'):
            group = group.sort_values('timestamp')
            
            for i in range(len(group)):
                if i < 5:  # Need at least 5 previous readings
                    continue
                
                recent = group.iloc[max(0, i-10):i+1]
                
                features = {
                    'temperature': recent['temperature'].iloc[-1],
                    'heart_rate': recent['heart_rate'].iloc[-1],
                    'motion_magnitude': recent['motion_magnitude'].iloc[-1] if 'motion_magnitude' in recent else 0,
                    
                    # Temporal features
                    'temp_change_rate': recent['temperature'].diff().mean(),
                    'hr_change_rate': recent['heart_rate'].diff().mean(),
                    'motion_variability': recent['motion_magnitude'].std() if 'motion_magnitude' in recent else 0,
                    
                    # Statistical features
                    'temp_std': recent['temperature'].std(),
                    'hr_std': recent['heart_rate'].std(),
                }
                
                features_list.append(features)
        
        return pd.DataFrame(features_list).fillna(0)
    
    def predict_anomaly(self, reading: Dict) -> Dict:
        """
        Predict if a reading is anomalous
        Returns: {
            'is_anomaly': bool,
            'anomaly_score': float,
            'confidence': float,
            'explanation': str
        }
        """
        if not ML_AVAILABLE or self.anomaly_detector is None:
            return {
                'is_anomaly': False,
                'anomaly_score': 0,
                'confidence': 0,
                'explanation': 'ML not available'
            }
        
        try:
            # Get recent readings for feature extraction
            recent_readings = self._get_recent_readings(reading['device_id'], limit=10)
            recent_readings.append(reading)
            
            df = pd.DataFrame(recent_readings)
            features = self._extract_features(df)
            
            if features.empty:
                return {'is_anomaly': False, 'anomaly_score': 0, 'confidence': 0, 'explanation': 'Insufficient data'}
            
            # Get last row (current reading)
            # Use ALL features that were used during training (including hr_std and temp_std)
            all_feature_names = [
                'temperature', 'heart_rate', 'motion_magnitude',
                'temp_change_rate', 'hr_change_rate', 'motion_variability',
                'temp_std', 'hr_std'
            ]
            current_features = features.iloc[-1:][all_feature_names].fillna(0)
            
            # Scale and predict
            X_scaled = self.scaler.transform(current_features)
            prediction = self.anomaly_detector.predict(X_scaled)[0]
            anomaly_score = self.anomaly_detector.score_samples(X_scaled)[0]
            
            is_anomaly = prediction == -1
            confidence = abs(anomaly_score) * 100  # Convert to percentage
            
            # Generate explanation
            explanation = self._explain_anomaly(reading, current_features.iloc[0])
            
            return {
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'confidence': min(float(confidence), 100.0),
                'explanation': explanation,
                'model': 'IsolationForest'
            }
            
        except Exception as e:
            print(f"❌ Error predicting anomaly: {e}")
            return {'is_anomaly': False, 'anomaly_score': 0, 'confidence': 0, 'explanation': str(e)}
    
    def _get_recent_readings(self, device_id: str, limit: int = 10) -> List[Dict]:
        """Get recent readings for a device"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM livestock_readings
                WHERE device_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (device_id, limit))
            
            readings = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return readings[::-1]  # Reverse to get chronological order
            
        except Exception as e:
            print(f"❌ Error getting recent readings: {e}")
            return []
    
    def _explain_anomaly(self, reading: Dict, features: pd.Series) -> str:
        """Generate human-readable explanation for anomaly"""
        explanations = []
        
        temp = reading.get('temperature', 0)
        hr = reading.get('heart_rate', 0)
        temp_change = features.get('temp_change_rate', 0)
        hr_change = features.get('hr_change_rate', 0)
        
        if temp > 39.5:
            explanations.append(f"High temperature ({temp:.1f}°C)")
        elif temp < 37.5:
            explanations.append(f"Low temperature ({temp:.1f}°C)")
        
        if hr > 80:
            explanations.append(f"Elevated heart rate ({hr} BPM)")
        elif hr < 50:
            explanations.append(f"Low heart rate ({hr} BPM)")
        
        if abs(temp_change) > 0.5:
            explanations.append(f"Rapid temperature change ({temp_change:+.2f}°C/reading)")
        
        if abs(hr_change) > 5:
            explanations.append(f"Rapid heart rate change ({hr_change:+.0f} BPM/reading)")
        
        if not explanations:
            explanations.append("Unusual pattern detected in sensor data")
        
        return "; ".join(explanations)
    
    def predict_disease(self, reading: Dict) -> Dict:
        """
        Predict specific disease from sensor readings
        Now includes all 12 diseases/conditions
        
        Returns: {
            'disease': str,
            'probability': float,
            'confidence': float,
            'recommendations': List[str],
            'severity': str
        }
        """
        
        temp = reading.get('temperature', 0)
        hr = reading.get('heart_rate', 0)
        motion = reading.get('motion_magnitude', 0)
        
        # Get additional context
        device_id = reading.get('device_id', '')
        
        # Try to get milk production and lactation data
        milk_context = self._get_milk_context(device_id)
        
        # COMPREHENSIVE DISEASE CLASSIFICATION (12 conditions)
        
        # 1. BLOAT (CRITICAL - Rapid onset)
        if temp > 39.5 and hr > 90 and motion > 1.5:  # Distress pattern
            return {
                'disease': 'bloat',
                'probability': 0.70,
                'confidence': 70,
                'severity': 'CRITICAL',
                'recommendations': [
                    '🚨 EMERGENCY: Release gas immediately',
                    'Insert stomach tube or trocar',
                    'Contact veterinarian NOW',
                    'Do NOT delay - life-threatening'
                ]
            }
        
        # 2. MILK FEVER (CRITICAL - Post-calving emergency)
        if temp < 38.0 and hr < 60 and motion < 0.1:
            days_post_calving = milk_context.get('days_since_calving', 999)
            if days_post_calving <= 3:
                return {
                    'disease': 'milk_fever',
                    'probability': 0.80,
                    'confidence': 80,
                    'severity': 'CRITICAL',
                    'recommendations': [
                        '🚨 EMERGENCY: IV Calcium gluconate IMMEDIATELY',
                        'Contact veterinarian NOW',
                        'Keep animal warm',
                        'Do NOT attempt to stand animal',
                        'Monitor every 15 minutes'
                    ]
                }
        
        # 3. FEVER / SYSTEMIC INFECTION
        if temp > 40.0:
            return {
                'disease': 'fever',
                'probability': 0.90,
                'confidence': 90,
                'severity': 'HIGH',
                'recommendations': [
                    'Isolate animal immediately',
                    'Contact veterinarian',
                    'Monitor temperature every hour',
                    'Provide cool water',
                    'Check for other symptoms'
                ]
            }
        
        # 4. PNEUMONIA (Respiratory infection)
        if temp > 40.0 and hr > 90 and motion < 0.2:
            return {
                'disease': 'pneumonia',
                'probability': 0.80,
                'confidence': 80,
                'severity': 'HIGH',
                'recommendations': [
                    'Check for labored breathing',
                    'Contact veterinarian immediately',
                    'Isolate from herd',
                    'Ensure adequate ventilation',
                    'Antibiotics may be needed'
                ]
            }
        
        # 5. MASTITIS (Udder infection)
        milk_drop = milk_context.get('yield_drop_pct', 0)
        if temp > 39.2 and milk_drop > 25:
            return {
                'disease': 'mastitis',
                'probability': 0.85,
                'confidence': 85,
                'severity': 'HIGH',
                'recommendations': [
                    'Check udder for hardness/swelling',
                    'Strip milk to check appearance',
                    'Contact veterinarian',
                    'Consider milking more frequently',
                    'Antibiotics likely needed'
                ]
            }
        
        # 6. METRITIS (Uterine infection post-calving)
        days_post_calving = milk_context.get('days_since_calving', 999)
        if temp > 39.5 and hr > 80 and days_post_calving <= 21:
            return {
                'disease': 'metritis',
                'probability': 0.82,
                'confidence': 82,
                'severity': 'HIGH',
                'recommendations': [
                    'Veterinary examination required',
                    'Check for foul discharge',
                    'Antibiotics typically needed',
                    'Monitor appetite and milk yield',
                    'May need uterine lavage'
                ]
            }
        
        # 7. HEAT STRESS (Environmental)
        ambient_temp = reading.get('ambient_temperature', 0)
        if temp > 39.5 and hr > 85 and ambient_temp > 28:
            return {
                'disease': 'heat_stress',
                'probability': 0.90,
                'confidence': 90,
                'severity': 'HIGH',
                'recommendations': [
                    'Move to shaded area immediately',
                    'Provide cold water',
                    'Use fans or sprinklers',
                    'Reduce physical activity',
                    'Monitor closely'
                ]
            }
        
        # 8. KETOSIS (Metabolic - Early lactation)
        days_in_lactation = milk_context.get('days_in_lactation', 999)
        if days_in_lactation <= 60 and milk_drop > 15 and motion < 0.5:
            return {
                'disease': 'ketosis',
                'probability': 0.78,
                'confidence': 78,
                'severity': 'MEDIUM',
                'recommendations': [
                    'Provide energy supplements',
                    'Propylene glycol or dextrose',
                    'Adjust feed ration',
                    'Monitor milk production',
                    'Consult nutritionist'
                ]
            }
        
        # 9. LAMINITIS (Severe hoof inflammation)
        if motion < 0.1 and temp > 38.8 and temp < 39.5:
            return {
                'disease': 'laminitis',
                'probability': 0.80,
                'confidence': 80,
                'severity': 'HIGH',
                'recommendations': [
                    'Provide soft bedding',
                    'Anti-inflammatory medication',
                    'Contact veterinarian',
                    'Reduce grain feeding',
                    'Hoof care specialist needed'
                ]
            }
        
        # 10. LAMENESS (Hoof/leg problems)
        if motion < 0.05 and temp < 38.5:
            return {
                'disease': 'lameness',
                'probability': 0.85,
                'confidence': 85,
                'severity': 'MEDIUM',
                'recommendations': [
                    'Check hooves for injury/stones',
                    'Observe walking pattern',
                    'Trim hooves if needed',
                    'Foot bath treatment',
                    'Contact veterinarian if severe'
                ]
            }
        
        # 11. ESTRUS / HEAT DETECTION (Positive event!)
        if motion > 1.2 and temp > 38.8:
            days_since_calving = milk_context.get('days_since_calving', 0)
            if 45 <= days_since_calving <= 120:  # Suitable breeding window
                return {
                    'disease': 'estrus',
                    'probability': 0.75,
                    'confidence': 75,
                    'severity': 'POSITIVE',
                    'recommendations': [
                        '✅ BREEDING OPPORTUNITY!',
                        'Arrange AI or natural service within 12-24 hours',
                        'Confirm with visual signs',
                        'Record breeding date',
                        'Monitor for successful conception'
                    ]
                }
        
        # 12. CALVING PREDICTION (Positive event!)
        days_pregnant = milk_context.get('days_pregnant', 0)
        # Calving prediction based on pregnancy days and behavior changes
        if 270 <= days_pregnant <= 285:  # Near term pregnancy
            return {
                'disease': 'calving_soon',
                'probability': 0.85,
                'confidence': 85,
                'severity': 'MONITOR',
                'recommendations': [
                    '🐄 Calving expected within 24-48 hours',
                    'Move to calving pen',
                    'Prepare calving supplies',
                    'Monitor frequently',
                    'Ensure assistance available'
                ]
            }
        
        # DEFAULT: Healthy
        else:
            return {
                'disease': 'healthy',
                'probability': 0.90,
                'confidence': 90,
                'severity': 'NONE',
                'recommendations': ['Continue normal monitoring']
            }
    
    def _get_milk_context(self, device_id: str) -> Dict:
        """Get milk production and reproductive context"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get animal profile
            cursor.execute('SELECT * FROM animal_profiles WHERE device_id = ?', (device_id,))
            profile = cursor.fetchone()
            
            context = {}
            
            if profile:
                # Calculate days since calving
                if profile['last_calving_date']:
                    calving_date = pd.to_datetime(profile['last_calving_date'])
                    days_since = (datetime.now() - calving_date).days
                    context['days_since_calving'] = days_since
                    context['days_in_lactation'] = days_since
            
            # Get recent milk yield
            cursor.execute('''
                SELECT yield_liters, collection_date
                FROM milk_production
                WHERE device_id = ?
                ORDER BY collection_date DESC
                LIMIT 7
            ''', (device_id,))
            
            recent_yields = cursor.fetchall()
            if recent_yields and len(recent_yields) >= 3:
                recent_avg = sum(r['yield_liters'] for r in recent_yields[:3]) / 3
                older_avg = sum(r['yield_liters'] for r in recent_yields[3:]) / max(1, len(recent_yields[3:]))
                
                if older_avg > 0:
                    drop_pct = ((older_avg - recent_avg) / older_avg) * 100
                    context['yield_drop_pct'] = drop_pct
            
            conn.close()
            return context
            
        except Exception as e:
            print(f"Error getting milk context: {e}")
            return {}
    
    def forecast_health(self, device_id: str, hours_ahead: int = 24) -> Dict:
        """
        Forecast future health metrics
        Returns predicted temperature and heart rate trends
        """
        try:
            # Get historical data
            readings = self._get_recent_readings(device_id, limit=100)
            
            if len(readings) < 10:
                return {'error': 'Insufficient historical data'}
            
            df = pd.DataFrame(readings)
            
            # Simple moving average forecast
            temp_avg = df['temperature'].rolling(window=10).mean().iloc[-1]
            temp_trend = df['temperature'].diff().mean()
            
            hr_avg = df['heart_rate'].rolling(window=10).mean().iloc[-1]
            hr_trend = df['heart_rate'].diff().mean()
            
            # Predict future values
            temp_forecast = temp_avg + (temp_trend * hours_ahead / 2)
            hr_forecast = hr_avg + (hr_trend * hours_ahead / 2)
            
            # Determine risk level
            risk_level = 'low'
            if temp_forecast > 39.5 or hr_forecast > 85:
                risk_level = 'high'
            elif temp_forecast > 39.0 or hr_forecast > 75:
                risk_level = 'medium'
            
            return {
                'device_id': device_id,
                'forecast_hours': hours_ahead,
                'predicted_temperature': round(float(temp_forecast), 2),
                'predicted_heart_rate': round(float(hr_forecast), 0),
                'current_temperature': float(df['temperature'].iloc[-1]),
                'current_heart_rate': float(df['heart_rate'].iloc[-1]),
                'temperature_trend': 'increasing' if temp_trend > 0 else 'decreasing',
                'heart_rate_trend': 'increasing' if hr_trend > 0 else 'decreasing',
                'risk_level': risk_level,
                'confidence': 70  # Simple forecast = lower confidence
            }
            
        except Exception as e:
            print(f"❌ Error forecasting health: {e}")
            return {'error': str(e)}
    
    def retrain_models(self):
        """Retrain all models with latest data"""
        print("🔄 Retraining ML models...")
        self._train_anomaly_detector()
        print("✅ Model retraining complete")
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        return {
            'ml_available': ML_AVAILABLE,
            'anomaly_detector_loaded': self.anomaly_detector is not None,
            'scaler_loaded': self.scaler is not None,
            'disease_classifier_loaded': self.disease_classifier is not None,
            'models_directory': self.models_dir,
            'supported_diseases': self.disease_labels
        }
        
        if ML_AVAILABLE:
            self._load_or_train_models()
    
    def _load_or_train_models(self):
        """Load existing models or train new ones"""
        anomaly_path = os.path.join(self.models_dir, 'anomaly_detector.pkl')
        scaler_path = os.path.join(self.models_dir, 'scaler.pkl')
        
        if os.path.exists(anomaly_path) and os.path.exists(scaler_path):
            # Load existing models
            try:
                with open(anomaly_path, 'rb') as f:
                    self.anomaly_detector = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("✅ ML models loaded successfully")
            except Exception as e:
                print(f"⚠️  Error loading models: {e}")
                self._train_anomaly_detector()
        else:
            # Train new models
            self._train_anomaly_detector()
    
    def _train_anomaly_detector(self):
        """Train anomaly detection model on historical data"""
        try:
            print("🔄 Training anomaly detection model...")
            
            # Get historical data
            df = self._get_training_data()
            
            if df.empty or len(df) < 100:
                print("⚠️  Insufficient data for training (need 100+ readings)")
                return
            
            # Prepare features
            features = self._extract_features(df)
            
            if features.empty:
                print("⚠️  No valid features extracted")
                return
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(features)
            
            # Train Isolation Forest
            self.anomaly_detector = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42,
                n_estimators=100
            )
            self.anomaly_detector.fit(X_scaled)
            
            # Save models
            with open(os.path.join(self.models_dir, 'anomaly_detector.pkl'), 'wb') as f:
                pickle.dump(self.anomaly_detector, f)
            with open(os.path.join(self.models_dir, 'scaler.pkl'), 'wb') as f:
                pickle.dump(self.scaler, f)
            
            print(f"✅ Anomaly detector trained on {len(df)} readings")
            
        except Exception as e:
            print(f"❌ Error training anomaly detector: {e}")
    
    def _get_training_data(self, days: int = 30) -> pd.DataFrame:
        """Get historical data for training"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = f"""
                SELECT 
                    device_id,
                    temperature,
                    body_temperature,
                    ambient_temperature,
                    heart_rate,
                    motion_magnitude,
                    battery,
                    timestamp,
                    received_time
                FROM livestock_readings
                WHERE datetime(received_time) > datetime('now', '-{days} days')
                AND temperature IS NOT NULL
                AND heart_rate IS NOT NULL
                ORDER BY device_id, timestamp
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"❌ Error getting training data: {e}")
            return pd.DataFrame()
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract engineered features for ML"""
        if df.empty:
            return pd.DataFrame()
        
        features_list = []
        
        # Group by device to calculate temporal features
        for device_id, group in df.groupby('device_id'):
            group = group.sort_values('timestamp')
            
            for i in range(len(group)):
                if i < 5:  # Need at least 5 previous readings
                    continue
                
                recent = group.iloc[max(0, i-10):i+1]
                
                features = {
                    'temperature': recent['temperature'].iloc[-1],
                    'heart_rate': recent['heart_rate'].iloc[-1],
                    'motion_magnitude': recent['motion_magnitude'].iloc[-1] if 'motion_magnitude' in recent else 0,
                    
                    # Temporal features
                    'temp_change_rate': recent['temperature'].diff().mean(),
                    'hr_change_rate': recent['heart_rate'].diff().mean(),
                    'motion_variability': recent['motion_magnitude'].std() if 'motion_magnitude' in recent else 0,
                    
                    # Statistical features
                    'temp_std': recent['temperature'].std(),
                    'hr_std': recent['heart_rate'].std(),
                }
                
                features_list.append(features)
        
        return pd.DataFrame(features_list).fillna(0)
    
    def predict_anomaly(self, reading: Dict) -> Dict:
        """
        Predict if a reading is anomalous
        Returns: {
            'is_anomaly': bool,
            'anomaly_score': float,
            'confidence': float,
            'explanation': str
        }
        """
        if not ML_AVAILABLE or self.anomaly_detector is None:
            return {
                'is_anomaly': False,
                'anomaly_score': 0,
                'confidence': 0,
                'explanation': 'ML not available'
            }
        
        try:
            # Get recent readings for feature extraction
            recent_readings = self._get_recent_readings(reading['device_id'], limit=10)
            recent_readings.append(reading)
            
            df = pd.DataFrame(recent_readings)
            features = self._extract_features(df)
            
            if features.empty:
                return {'is_anomaly': False, 'anomaly_score': 0, 'confidence': 0, 'explanation': 'Insufficient data'}
            
            # Get last row (current reading)
            # Use ALL features that were used during training (including hr_std and temp_std)
            all_feature_names = [
                'temperature', 'heart_rate', 'motion_magnitude',
                'temp_change_rate', 'hr_change_rate', 'motion_variability',
                'temp_std', 'hr_std'
            ]
            current_features = features.iloc[-1:][all_feature_names].fillna(0)
            
            # Scale and predict
            X_scaled = self.scaler.transform(current_features)
            prediction = self.anomaly_detector.predict(X_scaled)[0]
            anomaly_score = self.anomaly_detector.score_samples(X_scaled)[0]
            
            is_anomaly = prediction == -1
            confidence = abs(anomaly_score) * 100  # Convert to percentage
            
            # Generate explanation
            explanation = self._explain_anomaly(reading, current_features.iloc[0])
            
            return {
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'confidence': min(float(confidence), 100.0),
                'explanation': explanation,
                'model': 'IsolationForest'
            }
            
        except Exception as e:
            print(f"❌ Error predicting anomaly: {e}")
            return {'is_anomaly': False, 'anomaly_score': 0, 'confidence': 0, 'explanation': str(e)}
    
    def _get_recent_readings(self, device_id: str, limit: int = 10) -> List[Dict]:
        """Get recent readings for a device"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM livestock_readings
                WHERE device_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (device_id, limit))
            
            readings = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return readings[::-1]  # Reverse to get chronological order
            
        except Exception as e:
            print(f"❌ Error getting recent readings: {e}")
            return []
    
    def _explain_anomaly(self, reading: Dict, features: pd.Series) -> str:
        """Generate human-readable explanation for anomaly"""
        explanations = []
        
        temp = reading.get('temperature', 0)
        hr = reading.get('heart_rate', 0)
        temp_change = features.get('temp_change_rate', 0)
        hr_change = features.get('hr_change_rate', 0)
        
        if temp > 39.5:
            explanations.append(f"High temperature ({temp:.1f}°C)")
        elif temp < 37.5:
            explanations.append(f"Low temperature ({temp:.1f}°C)")
        
        if hr > 80:
            explanations.append(f"Elevated heart rate ({hr} BPM)")
        elif hr < 50:
            explanations.append(f"Low heart rate ({hr} BPM)")
        
        if abs(temp_change) > 0.5:
            explanations.append(f"Rapid temperature change ({temp_change:+.2f}°C/reading)")
        
        if abs(hr_change) > 5:
            explanations.append(f"Rapid heart rate change ({hr_change:+.0f} BPM/reading)")
        
        if not explanations:
            explanations.append("Unusual pattern detected in sensor data")
        
        return "; ".join(explanations)
    
    def predict_disease(self, reading: Dict) -> Dict:
        """
        Predict specific disease (if classifier is trained)
        Returns: {
            'disease': str,
            'probability': float,
            'confidence': float,
            'recommendations': List[str]
        }
        """
        # This would use a trained classifier if we have labeled data
        # For now, return rule-based prediction
        
        temp = reading.get('temperature', 0)
        hr = reading.get('heart_rate', 0)
        motion = reading.get('motion_magnitude', 0)
        
        # Simple rule-based classification
        if temp > 40:
            return {
                'disease': 'fever',
                'probability': 0.85,
                'confidence': 85,
                'recommendations': [
                    'Isolate animal immediately',
                    'Contact veterinarian',
                    'Monitor temperature every hour',
                    'Provide cool water'
                ]
            }
        elif temp > 39.5 and hr > 85:
            return {
                'disease': 'heat_stress',
                'probability': 0.75,
                'confidence': 75,
                'recommendations': [
                    'Move to shaded area',
                    'Provide cold water',
                    'Monitor closely',
                    'Reduce physical activity'
                ]
            }
        elif hr > 90 and motion < 0.1:
            return {
                'disease': 'respiratory',
                'probability': 0.65,
                'confidence': 65,
                'recommendations': [
                    'Check for labored breathing',
                    'Contact veterinarian if symptoms persist',
                    'Monitor heart rate',
                    'Ensure adequate ventilation'
                ]
            }
        elif motion < 0.05 and temp < 38.5:
            return {
                'disease': 'lameness',
                'probability': 0.60,
                'confidence': 60,
                'recommendations': [
                    'Check hooves for injury',
                    'Observe walking pattern',
                    'Reduce movement if limping',
                    'Contact veterinarian if severe'
                ]
            }
        else:
            return {
                'disease': 'healthy',
                'probability': 0.90,
                'confidence': 90,
                'recommendations': ['Continue normal monitoring']
            }
    
    def forecast_health(self, device_id: str, hours_ahead: int = 24) -> Dict:
        """
        Forecast future health metrics
        Returns predicted temperature and heart rate trends
        """
        try:
            # Get historical data
            readings = self._get_recent_readings(device_id, limit=100)
            
            if len(readings) < 10:
                return {'error': 'Insufficient historical data'}
            
            df = pd.DataFrame(readings)
            
            # Simple moving average forecast
            temp_avg = df['temperature'].rolling(window=10).mean().iloc[-1]
            temp_trend = df['temperature'].diff().mean()
            
            hr_avg = df['heart_rate'].rolling(window=10).mean().iloc[-1]
            hr_trend = df['heart_rate'].diff().mean()
            
            # Predict future values
            temp_forecast = temp_avg + (temp_trend * hours_ahead / 2)
            hr_forecast = hr_avg + (hr_trend * hours_ahead / 2)
            
            # Determine risk level
            risk_level = 'low'
            if temp_forecast > 39.5 or hr_forecast > 85:
                risk_level = 'high'
            elif temp_forecast > 39.0 or hr_forecast > 75:
                risk_level = 'medium'
            
            return {
                'device_id': device_id,
                'forecast_hours': hours_ahead,
                'predicted_temperature': round(float(temp_forecast), 2),
                'predicted_heart_rate': round(float(hr_forecast), 0),
                'current_temperature': float(df['temperature'].iloc[-1]),
                'current_heart_rate': float(df['heart_rate'].iloc[-1]),
                'temperature_trend': 'increasing' if temp_trend > 0 else 'decreasing',
                'heart_rate_trend': 'increasing' if hr_trend > 0 else 'decreasing',
                'risk_level': risk_level,
                'confidence': 70  # Simple forecast = lower confidence
            }
            
        except Exception as e:
            print(f"❌ Error forecasting health: {e}")
            return {'error': str(e)}
    
    def retrain_models(self):
        """Retrain all models with latest data"""
        print("🔄 Retraining ML models...")
        self._train_anomaly_detector()
        print("✅ Model retraining complete")
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        return {
            'ml_available': ML_AVAILABLE,
            'anomaly_detector_loaded': self.anomaly_detector is not None,
            'scaler_loaded': self.scaler is not None,
            'disease_classifier_loaded': self.disease_classifier is not None,
            'models_directory': self.models_dir,
            'supported_diseases': self.disease_labels
        }


# Global instance
ml_detector = MLDiseaseDetector() if ML_AVAILABLE else None
