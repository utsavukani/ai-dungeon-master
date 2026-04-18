from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.game.game_engine import UltimateGameEngine
from src.database.database import SessionLocal
from src.database.models import Campaign
import json
import asyncio

websocket_router = APIRouter()

@websocket_router.websocket("/ws/game/{campaign_id}")
async def websocket_endpoint(websocket: WebSocket, campaign_id: str):
    await websocket.accept()
    
    # Verify campaign exists (for our mock testing, we will just blindly start the engine
    # which will create the campaign_id if handled, or fail gracefully)
    
    try:
        # Initialize the Game Engine per connection to the specific isolated Campaign Session
        game = UltimateGameEngine(campaign_id=campaign_id)
        
        # Custom stream callback to emit tokens real-time over WebSocket
        async def emit_token(chunk: str):
            await websocket.send_json({
                "type": "token",
                "payload": {"text": chunk}
            })

        # Hook the callback into the agent workflow
        game.agent_workflow.stream_callback = emit_token

        # Send initial starting message event
        initial_response = await game.start_game()
        
        # When start_game finishes, send full sync payload
        await websocket.send_json({
            "type": "turn_complete",
            "payload": {
                "ai_response": initial_response,
                "character": game.character_sheet.stats,
                "quests": game.quest_tracker.get_active_quests()
            }
        })
        
        while True:
            # Wait for player input {type: "action", payload: {text: "I go left"}}
            data = await websocket.receive_text()
            event = json.loads(data)
            
            if event.get("type") == "action":
                player_input = event["payload"]["text"]
                
                # Signal frontend we are thinking
                await websocket.send_json({"type": "thinking"})
                
                # Engine processes action and fires stream callbacks
                ai_response = await game.process_player_action(player_input)
                
                # Turn finished - give Frontend full state updates
                await websocket.send_json({
                    "type": "turn_complete",
                    "payload": {
                        "ai_response": ai_response,
                        "character": game.character_sheet.stats,
                        "quests": game.quest_tracker.get_active_quests(),
                        "inventory": game.character_sheet.inventory
                    }
                })

    except WebSocketDisconnect:
        print(f"Client disconnected from campaign {campaign_id}.")
    except Exception as e:
        print(f"WebSocket error in campaign {campaign_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
            await websocket.close()
        except Exception:
            pass
