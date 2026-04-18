import time
from typing import TypedDict, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class GameState(TypedDict):
    """The central state dictionary passed between all AI agents."""
    player_input: str
    context: str
    turn_number: int

    # Updated by narrator step
    ai_response: str
    response_time: float

    # Updated by extraction step
    extracted_events: Optional[Dict[str, Any]]


class GameAgentWorkflow:
    """Manages the two-step AI workflow: Narrator → Extractor.

    Previously used LangGraph for this sequential pipeline, but since
    the flow never branches we handle it with simple async calls instead,
    removing a heavy production dependency.
    """

    def __init__(self, llm_client, prompt_manager, stream_callback=None):
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.stream_callback = stream_callback

    async def run(self, initial_state: GameState) -> GameState:
        """Execute narrator → extractor sequentially and return the final state."""
        state = dict(initial_state)

        # Step 1: Narrator
        narrator_result = await self.narrator_node(state)
        state.update(narrator_result)

        # Step 2: Extractor
        extractor_result = await self.extraction_node(state)
        state.update(extractor_result)

        return state

    async def narrator_node(self, state: dict) -> dict:
        """Step 1: Generate the main story and stream it to the player."""
        prompt = self.prompt_manager.build_enhanced_game_prompt(
            state["player_input"], state["context"], state["turn_number"]
        )

        start_time = time.time()
        print("\n🎭 DM: ", end="", flush=True)

        ai_response = ""
        async for chunk in self.llm_client.generate_response_stream(prompt):
            print(chunk, end="", flush=True)
            ai_response += chunk
            if self.stream_callback:
                import asyncio
                if asyncio.iscoroutinefunction(self.stream_callback):
                    await self.stream_callback(chunk)
                else:
                    self.stream_callback(chunk)
        print()

        response_time = time.time() - start_time
        return {"ai_response": ai_response, "response_time": response_time}

    async def extraction_node(self, state: dict) -> dict:
        """Step 2: Silently extract structured game mechanics from the DM response."""
        ai_response = state["ai_response"]

        prompt = f'''
RULES — read carefully:
- "added_items": list of item NAMES as plain strings. Example: ["Iron Sword", "Health Potion"]. NOT objects. Only items physically given/found/picked up.
- "removed_items": list of item NAMES as plain strings that were lost/used/sold.
- "new_quests": list of SHORT quest TITLES as plain strings. Example: ["Find the Oak King's Oracle"]. NOT objects. Only formal tasks/goals the player has accepted. DO NOT include story flavor, setting descriptions, or general information.
- "completed_quests": list of quest TITLES as plain strings that were explicitly finished.
- "gold_change": integer only — positive if gained, negative if lost, 0 if no change.
- "damage_taken": integer only — HP damage taken this turn, 0 if none.
- "experience_gained": integer only — XP gained this turn, 0 if none.

DM Response:
"{ai_response}"

Output ONLY this JSON, nothing else:
{{
    "added_items": [],
    "removed_items": [],
    "new_quests": [],
    "completed_quests": [],
    "gold_change": 0,
    "damage_taken": 0,
    "experience_gained": 0
}}
'''
        try:
            raw_dict = await self.llm_client.generate_json(prompt)
            return {"extracted_events": raw_dict}
        except Exception as e:
            logger.error("json_extraction_failed", error=str(e))
            return {"extracted_events": None}
