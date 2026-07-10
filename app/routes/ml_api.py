"""
ML Disease Detection API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.ml_disease_detector import ml_detector, ML_AVAILABLE

router = APIRouter()

@router.get("/ml/status")
def get_ml_status():
    """Get ML system status and information"""
    if not ML_AVAILABLE:
        return {
            "ml_available": False,
            "message": "ML libraries not installed. Run: pip install scikit-learn pandas numpy"
        }
    
    if ml_detector is None:
        return {
            "ml_available": False,
            "message": "ML detector initialization failed"
        }
    
    return ml_detector.get_model_info()


@router.post("/ml/predict/anomaly/{device_id}")
def predict_anomaly_for_device(device_id: str):
    """
    Predict if the latest reading from a device is anomalous
    """
    if not ML_AVAILABLE or ml_detector is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    
    try:
        # Get latest reading
        recent_readings = ml_detector._get_recent_readings(device_id, limit=1)
        
        if not recent_readings:
            raise HTTPException(status_code=404, detail=f"No readings found for device {device_id}")
        
        reading = recent_readings[0]
        result = ml_detector.predict_anomaly(reading)
        
        return {
            "device_id": device_id,
            "reading_id": reading.get('id'),
            "timestamp": reading.get('received_time'),
            "prediction": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/predict/disease/{device_id}")
def predict_disease_for_device(device_id: str):
    """
    Predict disease for the latest reading from a device
    """
    if not ML_AVAILABLE or ml_detector is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    
    try:
        # Get latest reading
        recent_readings = ml_detector._get_recent_readings(device_id, limit=1)
        
        if not recent_readings:
            raise HTTPException(status_code=404, detail=f"No readings found for device {device_id}")
        
        reading = recent_readings[0]
        result = ml_detector.predict_disease(reading)
        
        return {
            "device_id": device_id,
            "reading_id": reading.get('id'),
            "timestamp": reading.get('received_time'),
            "temperature": reading.get('temperature'),
            "heart_rate": reading.get('heart_rate'),
            "prediction": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/forecast/{device_id}")
def forecast_health(device_id: str, hours_ahead: int = Query(default=24, ge=1, le=72)):
    """
    Forecast future health metrics for a device
    
    Parameters:
    - device_id: Device to forecast
    - hours_ahead: Number of hours to forecast (1-72)
    """
    if not ML_AVAILABLE or ml_detector is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    
    try:
        result = ml_detector.forecast_health(device_id, hours_ahead=hours_ahead)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/retrain")
def retrain_models():
    """
    Retrain ML models with latest data
    
    This should be run periodically (e.g., daily/weekly) to improve accuracy
    """
    if not ML_AVAILABLE or ml_detector is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    
    try:
        ml_detector.retrain_models()
        
        return {
            "status": "success",
            "message": "ML models retrained successfully",
            "model_info": ml_detector.get_model_info()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/predictions/history/{device_id}")
def get_prediction_history(device_id: str, limit: int = Query(default=20, le=100)):
    """
    Get historical ML predictions for a device
    
    This endpoint would return stored predictions if we add prediction logging
    to the database. For now, it returns recent predictions by re-analyzing
    historical data.
    """
    if not ML_AVAILABLE or ml_detector is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    
    try:
        # Get recent readings
        readings = ml_detector._get_recent_readings(device_id, limit=limit)
        
        if not readings:
            raise HTTPException(status_code=404, detail=f"No readings found for device {device_id}")
        
        # Analyze each reading
        predictions = []
        for reading in readings:
            anomaly_pred = ml_detector.predict_anomaly(reading)
            disease_pred = ml_detector.predict_disease(reading)
            
            predictions.append({
                "reading_id": reading.get('id'),
                "timestamp": reading.get('received_time'),
                "temperature": reading.get('temperature'),
                "heart_rate": reading.get('heart_rate'),
                "anomaly": anomaly_pred,
                "disease": disease_pred
            })
        
        return {
            "device_id": device_id,
            "count": len(predictions),
            "predictions": predictions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml/recommendations/{device_id}")
def get_health_recommendations(device_id: str):
    """
    Get AI-powered health recommendations for a device
    """
    if not ML_AVAILABLE or ml_detector is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    
    try:
        # Get latest reading
        recent_readings = ml_detector._get_recent_readings(device_id, limit=1)
        
        if not recent_readings:
            raise HTTPException(status_code=404, detail=f"No readings found for device {device_id}")
        
        reading = recent_readings[0]
        
        # Get predictions
        anomaly = ml_detector.predict_anomaly(reading)
        disease = ml_detector.predict_disease(reading)
        forecast = ml_detector.forecast_health(device_id, hours_ahead=24)
        
        # Compile recommendations
        recommendations = []
        priority = "normal"
        
        # Add disease-specific recommendations
        if disease.get('disease') != 'healthy':
            recommendations.extend(disease.get('recommendations', []))
            priority = "high" if disease.get('probability', 0) > 0.8 else "medium"
        
        # Add anomaly-based recommendations
        if anomaly.get('is_anomaly'):
            recommendations.append(f"Unusual pattern detected: {anomaly.get('explanation')}")
            if priority == "normal":
                priority = "medium"
        
        # Add forecast-based recommendations
        if isinstance(forecast, dict) and forecast.get('risk_level') == 'high':
            recommendations.append(f"Health decline predicted in next 24 hours")
            recommendations.append(f"Expected temperature: {forecast.get('predicted_temperature')}°C")
            priority = "high"
        
        # Default recommendation if healthy
        if not recommendations:
            recommendations = ["Animal appears healthy", "Continue normal monitoring"]
        
        return {
            "device_id": device_id,
            "priority": priority,
            "recommendations": recommendations,
            "current_status": {
                "temperature": reading.get('temperature'),
                "heart_rate": reading.get('heart_rate'),
                "battery": reading.get('battery')
            },
            "predictions": {
                "anomaly": anomaly,
                "disease": disease,
                "forecast": forecast
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
