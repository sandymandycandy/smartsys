"""
ML-Based Milk Yield Prediction for Smart Pastoralism
Predicts future milk production based on historical data and health metrics
"""
import numpy as np
import pandas as pd
import sqlite3
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.config import settings

# ML Libraries
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️  scikit-learn not installed for milk prediction")


class MilkYieldPredictor:
    """
    Predicts milk yield using machine learning
    Combines historical production data with health metrics
    """
    
    def __init__(self):
        self.db_path = settings.LORA_DB_PATH
        self.models_dir = "app/ml_models"
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Model instances
        self.yield_predictor = None
        self.scaler = None
        
        # Feature names
        self.feature_names = [
            'days_in_lactation',
            'lactation_number',
            'avg_yield_7d',
            'avg_yield_30d',
            'yield_trend',
            'avg_temperature',
            'avg_heart_rate',
            'avg_activity',
            'health_score',
            'session_morning',
            'session_afternoon',
            'session_evening'
        ]
        
        if ML_AVAILABLE:
            self._load_or_train_model()
    
    def _load_or_train_model(self):
        """Load existing model or train new one"""
        model_path = os.path.join(self.models_dir, 'milk_yield_predictor.pkl')
        scaler_path = os.path.join(self.models_dir, 'milk_scaler.pkl')
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            try:
                with open(model_path, 'rb') as f:
                    self.yield_predictor = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("✅ Milk yield predictor loaded")
            except Exception as e:
                print(f"⚠️  Error loading milk predictor: {e}")
                self._train_model()
        else:
            self._train_model()
    
    def _train_model(self):
        """Train milk yield prediction model"""
        try:
            print("🔄 Training milk yield predictor...")
            
            # Get training data
            df = self._get_training_data()
            
            if df.empty or len(df) < 50:
                print("⚠️  Insufficient milk production data (need 50+ records)")
                return
            
            # Prepare features
            X, y = self._prepare_features(df)
            
            if X.empty:
                print("⚠️  No valid features for training")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train Random Forest Regressor
            self.yield_predictor = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
            self.yield_predictor.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.yield_predictor.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            print(f"✅ Model trained - MAE: {mae:.2f}L, R²: {r2:.3f}")
            
            # Save models
            with open(os.path.join(self.models_dir, 'milk_yield_predictor.pkl'), 'wb') as f:
                pickle.dump(self.yield_predictor, f)
            with open(os.path.join(self.models_dir, 'milk_scaler.pkl'), 'wb') as f:
                pickle.dump(self.scaler, f)
            
        except Exception as e:
            print(f"❌ Error training milk predictor: {e}")
    
    def _get_training_data(self) -> pd.DataFrame:
        """Get historical milk production and health data"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get milk production with health data
            query = """
                SELECT 
                    mp.device_id,
                    mp.collection_date,
                    mp.collection_time,
                    mp.yield_liters,
                    mp.milking_session,
                    ap.lactation_number,
                    ap.last_calving_date,
                    (SELECT AVG(temperature) 
                     FROM livestock_readings lr 
                     WHERE lr.device_id = mp.device_id 
                     AND date(lr.received_time) = mp.collection_date) as avg_temp,
                    (SELECT AVG(heart_rate) 
                     FROM livestock_readings lr 
                     WHERE lr.device_id = mp.device_id 
                     AND date(lr.received_time) = mp.collection_date) as avg_hr,
                    (SELECT AVG(motion_magnitude) 
                     FROM livestock_readings lr 
                     WHERE lr.device_id = mp.device_id 
                     AND date(lr.received_time) = mp.collection_date) as avg_activity
                FROM milk_production mp
                LEFT JOIN animal_profiles ap ON mp.device_id = ap.device_id
                ORDER BY mp.device_id, mp.collection_date, mp.collection_time
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
            
        except Exception as e:
            print(f"❌ Error getting training data: {e}")
            return pd.DataFrame()
    
    def _prepare_features(self, df: pd.DataFrame) -> tuple:
        """Extract features for ML model"""
        if df.empty:
            return pd.DataFrame(), pd.Series()
        
        features_list = []
        targets = []
        
        # Group by device to calculate temporal features
        for device_id, group in df.groupby('device_id'):
            group = group.sort_values('collection_date')
            
            for i in range(len(group)):
                if i < 3:  # Need at least 3 previous records
                    continue
                
                current = group.iloc[i]
                recent_7d = group.iloc[max(0, i-14):i]  # ~7 days (2 sessions/day)
                recent_30d = group.iloc[max(0, i-60):i]  # ~30 days
                
                # Calculate days in lactation
                if pd.notna(current['last_calving_date']):
                    calving_date = pd.to_datetime(current['last_calving_date'])
                    collection_date = pd.to_datetime(current['collection_date'])
                    days_in_lactation = (collection_date - calving_date).days
                else:
                    days_in_lactation = 100  # Default assumption
                
                # Build feature vector
                features = {
                    'days_in_lactation': min(days_in_lactation, 365),
                    'lactation_number': current['lactation_number'] if pd.notna(current['lactation_number']) else 1,
                    'avg_yield_7d': recent_7d['yield_liters'].mean() if len(recent_7d) > 0 else 0,
                    'avg_yield_30d': recent_30d['yield_liters'].mean() if len(recent_30d) > 0 else 0,
                    'yield_trend': recent_7d['yield_liters'].diff().mean() if len(recent_7d) > 1 else 0,
                    'avg_temperature': current['avg_temp'] if pd.notna(current['avg_temp']) else 38.5,
                    'avg_heart_rate': current['avg_hr'] if pd.notna(current['avg_hr']) else 70,
                    'avg_activity': current['avg_activity'] if pd.notna(current['avg_activity']) else 0.5,
                    'health_score': self._calculate_health_score(current),
                    'session_morning': 1 if current['milking_session'] == 'morning' else 0,
                    'session_afternoon': 1 if current['milking_session'] == 'afternoon' else 0,
                    'session_evening': 1 if current['milking_session'] == 'evening' else 0,
                }
                
                features_list.append(features)
                targets.append(current['yield_liters'])
        
        X = pd.DataFrame(features_list)
        y = pd.Series(targets)
        
        return X.fillna(0), y
    
    def _calculate_health_score(self, record: pd.Series) -> float:
        """Calculate health score from vitals (0-100)"""
        score = 100.0
        
        temp = record.get('avg_temp', 38.5)
        hr = record.get('avg_hr', 70)
        
        # Penalize abnormal temperature
        if temp > 39.5 or temp < 37.5:
            score -= 20
        elif temp > 39.0 or temp < 38.0:
            score -= 10
        
        # Penalize abnormal heart rate
        if hr > 85 or hr < 50:
            score -= 20
        elif hr > 75 or hr < 60:
            score -= 10
        
        return max(score, 0)
    
    def predict_next_yield(self, device_id: str, session: str = 'morning') -> Dict:
        """
        Predict milk yield for next milking session
        
        Args:
            device_id: Animal device ID
            session: 'morning', 'afternoon', or 'evening'
        
        Returns:
            {
                'predicted_yield': float,
                'confidence': float,
                'expected_range': (min, max),
                'factors': {...}
            }
        """
        if not ML_AVAILABLE or self.yield_predictor is None:
            return self._rule_based_prediction(device_id, session)
        
        try:
            # Get recent data
            features = self._extract_current_features(device_id, session)
            
            if features is None:
                return self._rule_based_prediction(device_id, session)
            
            # Scale and predict
            X = pd.DataFrame([features])[self.feature_names]
            X_scaled = self.scaler.transform(X)
            
            predicted_yield = self.yield_predictor.predict(X_scaled)[0]
            
            # Calculate confidence based on feature quality
            confidence = self._calculate_prediction_confidence(features)
            
            # Estimate range (±15%)
            margin = predicted_yield * 0.15
            expected_range = (
                max(0, predicted_yield - margin),
                predicted_yield + margin
            )
            
            # Identify key factors
            factors = self._identify_key_factors(features, predicted_yield)
            
            return {
                'device_id': device_id,
                'predicted_yield': round(float(predicted_yield), 2),
                'confidence': round(float(confidence), 1),
                'expected_range': (round(expected_range[0], 2), round(expected_range[1], 2)),
                'session': session,
                'factors': factors,
                'model': 'RandomForest'
            }
            
        except Exception as e:
            print(f"❌ Error predicting yield: {e}")
            return self._rule_based_prediction(device_id, session)
    
    def _extract_current_features(self, device_id: str, session: str) -> Optional[Dict]:
        """Extract features for current prediction"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get animal profile
            cursor.execute('SELECT * FROM animal_profiles WHERE device_id = ?', (device_id,))
            profile = cursor.fetchone()
            
            # Get recent milk production
            cursor.execute('''
                SELECT * FROM milk_production 
                WHERE device_id = ? 
                ORDER BY collection_date DESC, collection_time DESC 
                LIMIT 60
            ''', (device_id,))
            recent_production = [dict(row) for row in cursor.fetchall()]
            
            # Get recent health data
            cursor.execute('''
                SELECT AVG(temperature) as avg_temp, 
                       AVG(heart_rate) as avg_hr,
                       AVG(motion_magnitude) as avg_activity
                FROM livestock_readings
                WHERE device_id = ?
                AND datetime(received_time) > datetime('now', '-1 day')
            ''', (device_id,))
            health = cursor.fetchone()
            
            conn.close()
            
            if not recent_production:
                return None
            
            # Calculate days in lactation
            if profile and profile['last_calving_date']:
                calving_date = pd.to_datetime(profile['last_calving_date'])
                days_in_lactation = (datetime.now() - calving_date).days
            else:
                days_in_lactation = 100
            
            # Calculate averages
            recent_7d = recent_production[:14]  # ~7 days
            recent_30d = recent_production[:60]  # ~30 days
            
            yields_7d = [r['yield_liters'] for r in recent_7d]
            yields_30d = [r['yield_liters'] for r in recent_30d]
            
            features = {
                'days_in_lactation': min(days_in_lactation, 365),
                'lactation_number': profile['lactation_number'] if profile and profile['lactation_number'] else 1,
                'avg_yield_7d': np.mean(yields_7d) if yields_7d else 0,
                'avg_yield_30d': np.mean(yields_30d) if yields_30d else 0,
                'yield_trend': np.mean(np.diff(yields_7d)) if len(yields_7d) > 1 else 0,
                'avg_temperature': health['avg_temp'] if health and health['avg_temp'] else 38.5,
                'avg_heart_rate': health['avg_hr'] if health and health['avg_hr'] else 70,
                'avg_activity': health['avg_activity'] if health and health['avg_activity'] else 0.5,
                'health_score': self._calculate_health_score(pd.Series({
                    'avg_temp': health['avg_temp'] if health else 38.5,
                    'avg_hr': health['avg_hr'] if health else 70
                })),
                'session_morning': 1 if session == 'morning' else 0,
                'session_afternoon': 1 if session == 'afternoon' else 0,
                'session_evening': 1 if session == 'evening' else 0,
            }
            
            return features
            
        except Exception as e:
            print(f"❌ Error extracting features: {e}")
            return None
    
    def _calculate_prediction_confidence(self, features: Dict) -> float:
        """Calculate confidence level for prediction"""
        confidence = 100.0
        
        # Reduce confidence if limited historical data
        if features['avg_yield_7d'] == 0:
            confidence -= 30
        elif features['avg_yield_30d'] == 0:
            confidence -= 15
        
        # Reduce confidence if health is poor
        if features['health_score'] < 70:
            confidence -= 20
        elif features['health_score'] < 85:
            confidence -= 10
        
        # Reduce confidence if very early or late in lactation
        if features['days_in_lactation'] < 30 or features['days_in_lactation'] > 300:
            confidence -= 10
        
        return max(confidence, 40)
    
    def _identify_key_factors(self, features: Dict, predicted_yield: float) -> Dict:
        """Identify factors affecting the prediction"""
        factors = {}
        
        # Lactation stage
        days = features['days_in_lactation']
        if days < 60:
            factors['lactation_stage'] = 'Early (peak production expected)'
        elif days < 200:
            factors['lactation_stage'] = 'Mid (stable production)'
        else:
            factors['lactation_stage'] = 'Late (declining production)'
        
        # Trend
        if features['yield_trend'] > 0.1:
            factors['trend'] = 'Increasing (+)'
        elif features['yield_trend'] < -0.1:
            factors['trend'] = 'Decreasing (-)'
        else:
            factors['trend'] = 'Stable'
        
        # Health impact
        if features['health_score'] < 80:
            factors['health_impact'] = f"Health issues detected (score: {features['health_score']:.0f})"
        else:
            factors['health_impact'] = 'Good health'
        
        # Session impact
        if features['session_morning'] == 1:
            factors['session_note'] = 'Morning sessions typically yield more'
        elif features['session_evening'] == 1:
            factors['session_note'] = 'Evening sessions typically yield less'
        
        return factors
    
    def _rule_based_prediction(self, device_id: str, session: str) -> Dict:
        """Fallback rule-based prediction when ML not available"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get average of last 7 days
            cursor.execute('''
                SELECT AVG(yield_liters) as avg_yield
                FROM milk_production
                WHERE device_id = ?
                AND collection_date >= date('now', '-7 days')
            ''', (device_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            avg_yield = result[0] if result and result[0] else 8.0
            
            # Adjust by session
            if session == 'morning':
                predicted = avg_yield * 1.1
            elif session == 'evening':
                predicted = avg_yield * 0.9
            else:
                predicted = avg_yield
            
            return {
                'device_id': device_id,
                'predicted_yield': round(predicted, 2),
                'confidence': 60.0,
                'expected_range': (round(predicted * 0.85, 2), round(predicted * 1.15, 2)),
                'session': session,
                'factors': {'method': 'Rule-based (7-day average)'},
                'model': 'RuleBased'
            }
            
        except Exception as e:
            print(f"❌ Error in rule-based prediction: {e}")
            return {
                'device_id': device_id,
                'predicted_yield': 8.0,
                'confidence': 40.0,
                'expected_range': (6.0, 10.0),
                'session': session,
                'factors': {'error': str(e)},
                'model': 'Default'
            }
    
    def detect_yield_anomaly(self, device_id: str, actual_yield: float) -> Dict:
        """Detect if actual yield is anomalous compared to prediction"""
        prediction = self.predict_next_yield(device_id)
        
        predicted = prediction['predicted_yield']
        min_expected, max_expected = prediction['expected_range']
        
        is_anomaly = actual_yield < min_expected or actual_yield > max_expected
        
        if actual_yield < min_expected:
            severity = 'high' if actual_yield < predicted * 0.7 else 'medium'
            message = f"Yield {actual_yield:.1f}L is below expected range ({min_expected:.1f}-{max_expected:.1f}L)"
            recommendation = "Check animal health - possible illness or stress"
        elif actual_yield > max_expected:
            severity = 'low'
            message = f"Yield {actual_yield:.1f}L is above expected range (good!)"
            recommendation = "Excellent performance - maintain current care"
        else:
            severity = 'none'
            message = f"Yield {actual_yield:.1f}L is within expected range"
            recommendation = "Normal production - continue monitoring"
        
        return {
            'is_anomaly': is_anomaly,
            'severity': severity,
            'actual_yield': actual_yield,
            'predicted_yield': predicted,
            'deviation_percent': round(((actual_yield - predicted) / predicted) * 100, 1),
            'message': message,
            'recommendation': recommendation
        }
    
    def retrain_model(self):
        """Retrain the model with latest data"""
        print("🔄 Retraining milk yield predictor...")
        self._train_model()
        print("✅ Milk yield predictor retrained")


# Global instance
milk_yield_predictor = MilkYieldPredictor() if ML_AVAILABLE else None
