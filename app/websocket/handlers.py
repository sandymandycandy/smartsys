from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List, Dict
import json
import asyncio

router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and add new connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        async with self._lock:
            connections = self.active_connections.copy()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"⚠️  Error sending to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)

# Global connection manager
manager = ConnectionManager()

# Store the main event loop reference
_main_loop = None

def set_event_loop(loop):
    """Set the main event loop reference (called from main.py)"""
    global _main_loop
    _main_loop = loop

def setup_websocket(app):
    """Setup WebSocket endpoint"""
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                # Keep connection alive and handle client messages
                data = await websocket.receive_text()
                
                # Echo back or handle commands
                try:
                    message = json.loads(data)
                    if message.get('type') == 'ping':
                        await websocket.send_json({'type': 'pong', 'timestamp': message.get('timestamp')})
                except:
                    await websocket.send_json({'type': 'pong'})
                    
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await manager.disconnect(websocket)

def broadcast_update(data: Dict):
    """
    Called by LoRa service to broadcast new data
    This is thread-safe and can be called from background threads
    """
    global _main_loop
    
    if _main_loop is None:
        # Try to get the running loop
        try:
            _main_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop in current thread - this is expected from background threads
            # We'll try to use the stored loop reference
            pass
    
    if _main_loop is not None:
        try:
            # Schedule the coroutine in the main event loop from this thread
            asyncio.run_coroutine_threadsafe(manager.broadcast(data), _main_loop)
        except Exception as e:
            print(f"⚠️  Could not broadcast update: {e}")
    # Silently skip if no loop is available (normal during startup)

