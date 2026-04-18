import sys
import os
import time
import json
import re
import asyncio
import structlog
from typing import List
from pydantic import BaseModel, Field

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.game.quest_tracker import QuestTracker
from src.game.character_sheet import CharacterSheet
from src.llm.provider import GroqProvider, PromptManager
from src.memory.memory_manager import EnhancedMemoryManager
from src.game.agent_graph import GameAgentWorkflow

logger = structlog.get_logger()

class GameEvents(BaseModel):
    """Strict JSON schema that the LLM must follow to output state changes."""
    added_items: List[str] = Field(default=[], description="Items the player actually picked up or received")
    removed_items: List[str] = Field(default=[], description="Items the player dropped, lost, or consumed")
    new_quests: List[str] = Field(default=[], description="Strict action items the player has formally accepted as tasks. Exclude general worldbuilding.")
    completed_quests: List[str] = Field(default=[], description="Quests the player has explicitly completed.")
    gold_change: int = Field(default=0, description="Gold earned (positive) or lost (negative)")
    damage_taken: int = Field(default=0, description="Amount of HP damage taken by the player")
    experience_gained: int = Field(default=0, description="XP the player earned")


class UltimateGameEngine:
    """Ultimate AI Dungeon Master strictly bound to a Session/Campaign"""

    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id
        
        from src.database.database import SessionLocal
        from src.database.models import Campaign
        
        # Verify the campaign actually exists — it must be created via the API first
        db = SessionLocal()
        try:
            if not db.query(Campaign).filter(Campaign.id == campaign_id).first():
                raise ValueError(f"Campaign '{campaign_id}' does not exist. Create it via POST /api/campaigns first.")
        finally:
            db.close()

        # All tools now need the campaign_id to isolate their database operations
        self.memory_manager = EnhancedMemoryManager(campaign_id=self.campaign_id)
        self.llm_client = GroqProvider()
        self.prompt_manager = PromptManager()
        self.quest_tracker = QuestTracker(campaign_id=self.campaign_id)
        self.character_sheet = CharacterSheet(campaign_id=self.campaign_id)
        
        self.agent_workflow = GameAgentWorkflow(self.llm_client, self.prompt_manager)
        self.game_started = False
        self.game_stats = {
            'total_turns': 0,
            'avg_response_time': 0,
            'memory_retrievals': 0,
            'npc_interactions': 0,
            'quests_detected': 0,
            'items_found': 0,
            'combat_encounters': 0
        }

    async def start_game(self):
        """Initialize enhanced game session"""
        print("=== ULTIMATE AI DUNGEON MASTER ===")
        print("🗡️  Advanced Features Loaded (Phase 2):")
        print("   • SQLite Persistent Memory & Structlog")
        print("   • Streaming Async LLM Responses")
        print("   • Semantic RAG Memory (ChromaDB)")
        print("   • Pydantic Structured Quest & Item Tracking")
        print("\nStarting your epic adventure...\n")

        initial_prompt = "Create an exciting fantasy RPG opening that: 1. Sets a vivid, immersive location 2. Introduces the player as an adventurer with basic equipment 3. Presents an initial quest or challenge 4. Mentions NPCs the player can interact with 5. Gives 3-4 clear action options. Keep it engaging but under 200 words."
        
        initial_state = await self.agent_workflow.run({
            "player_input": initial_prompt,
            "context": "",
            "turn_number": 0
        })

        initial_response = initial_state["ai_response"]
        logger.info("game_initialized", response_time_s=round(initial_state["response_time"], 2))

        # Process initial response
        self.memory_manager.process_turn("", initial_response)
        self._apply_extracted_events(initial_state["extracted_events"])
        self.game_started = True

        return initial_response

    async def process_player_action(self, player_input: str) -> str:
        """Enhanced action processing with all systems"""
        if not self.game_started:
            return "Please start the game first!"

        # Build RAG Context
        context = self.memory_manager.get_context_for_llm(player_input)
        self.game_stats['memory_retrievals'] += 1
        enhanced_context = f"{context}\n{self._get_character_context()}"

        final_state = await self.agent_workflow.run({
            "player_input": player_input,
            "context": enhanced_context,
            "turn_number": self.memory_manager.turn_counter
        })

        ai_response = final_state["ai_response"]
        response_time = final_state["response_time"]

        # Track and Apply
        self._update_stats(ai_response, response_time)
        self.memory_manager.process_turn(player_input, ai_response)
        self._apply_extracted_events(final_state["extracted_events"])

        logger.info("turn_completed", turn=self.memory_manager.turn_counter, duration_s=round(response_time, 1))
        return ai_response

    def _get_character_context(self) -> str:
        return f"""
=== Character Status ===
Level {self.character_sheet.stats['level']} {self.character_sheet.stats['name']}
Health: {self.character_sheet.stats['health']}/{self.character_sheet.stats['max_health']}
Gold: {self.character_sheet.stats['gold']}
Items: {', '.join(self.character_sheet.inventory[:3])}{'...' if len(self.character_sheet.inventory) > 3 else ''}
Active Quests: {len(self.quest_tracker.get_active_quests())}
"""

    def _apply_extracted_events(self, raw_events: dict):
        """Validates JSON dict with Pydantic and applies mechanics to character/quests"""
        if not raw_events:
            print(f"[Warning: Failed to parse game mechanics this turn]")
            return

        try:
            # 1. Validate using Pydantic (will crash gracefully into except block if invalid)
            events = GameEvents(**raw_events)
            
            # 2. Apply state changes deterministically
            if events.experience_gained > 0:
                result = self.character_sheet.gain_experience(events.experience_gained)
                if 'Level up' in result:
                    logger.info("level_up", msg=result)
                    print(f"🎊 {result}")

            for item in events.added_items:
                result = self.character_sheet.add_item(item)
                if 'Added' in result:
                    logger.info("item_added", item=item)
                    print(f"🎒 Added {item} to inventory!")
                    self.game_stats['items_found'] += 1

            for item in events.removed_items:
                result = self.character_sheet.remove_item(item)
                if 'Removed' in result:
                    print(f"🗑️ Removed {item} from inventory.")

            if events.gold_change != 0:
                self.character_sheet.stats['gold'] += events.gold_change
                self.character_sheet._save()
                print(f"💰 Gold {'gained' if events.gold_change > 0 else 'lost'}: {abs(events.gold_change)}")

            if events.damage_taken > 0:
                result = self.character_sheet.take_damage(events.damage_taken)
                logger.info("damage_taken", damage=events.damage_taken)
                print(f"💔 {result}")

            for quest in events.new_quests:
                success = self.quest_tracker.add_quest(quest, self.memory_manager.turn_counter)
                if success:
                    self.game_stats['quests_detected'] += 1
                    print(f"📋 New Quest: {quest}")

            for quest in events.completed_quests:
                result = self.quest_tracker.complete_quest_by_description(quest, self.memory_manager.turn_counter)
                if result:
                    logger.info("quest_completed", description=result)
                    print(f"🎉 {result}")

        except Exception as e:
            logger.error("json_extraction_failed", error=str(e))
            print(f"[Warning: Failed to parse game mechanics this turn]")

    def _update_stats(self, ai_response: str, response_time: float):
        self.game_stats['total_turns'] += 1
        self.game_stats['avg_response_time'] = (
            (self.game_stats['avg_response_time'] * (self.game_stats['total_turns'] - 1) + response_time) /
            self.game_stats['total_turns']
        )
        if any(name[0].isupper() for name in ai_response.split() if len(name) > 2):
            self.game_stats['npc_interactions'] += 1
        if any(word in ai_response.lower() for word in ['attack', 'fight', 'battle', 'combat', 'sword', 'weapon', 'enemy']):
            self.game_stats['combat_encounters'] += 1

    def get_detailed_stats(self) -> dict:
        return {
            'game_stats': self.game_stats,
            'character_stats': {
                'level': self.character_sheet.stats['level'],
                'health': f"{self.character_sheet.stats['health']}/{self.character_sheet.stats['max_health']}",
                'gold': self.character_sheet.stats['gold'],
                'items': len(self.character_sheet.inventory),
                'abilities': len(self.character_sheet.abilities)
            },
            'quest_stats': self.quest_tracker.get_stats(),
            'memory_stats': {
                'turn_count': self.memory_manager.turn_counter,
                'working_memory_size': len(self.memory_manager.working_memory.get_memory())
            }
        }

    async def run_stability_test(self, num_turns: int = 30) -> dict:
        logger.info("stability_test_start", turns=num_turns)
        print(f"\n🧪 Running {num_turns}-Turn Stability Test...")

        test_actions = [
            "I explore the surrounding area carefully",
            "I search for any interesting items or clues",
            "I approach and talk to any NPCs I see",
            "I examine my equipment and inventory",
            "I look for enemies or dangers nearby"
        ]

        start_test_time = time.time()
        test_results = {'completed_turns': 0, 'errors': 0, 'avg_response_time': 0}

        for i in range(num_turns):
            try:
                action = test_actions[i % len(test_actions)]
                turn_start = time.time()
                
                print(f"\n[Test Action]: {action}")
                await self.process_player_action(action)
                
                response_time = time.time() - turn_start
                test_results['completed_turns'] += 1
                test_results['avg_response_time'] += response_time
            except Exception as e:
                test_results['errors'] += 1
                logger.error("test_error", turn=i+1, error=str(e))
                print(f"❌ Error on turn {i + 1}: {str(e)[:100]}")

        # Finish up
        test_results['avg_response_time'] /= max(1, test_results['completed_turns'])
        logger.info("stability_test_end", results=test_results)
        return test_results


async def main():
    """Ultimate game interface"""
    game = UltimateGameEngine()

    print("🎮 ULTIMATE AI DUNGEON MASTER")
    print("Commands: quit, stats, character, quests, inventory, eval, help\n")

    await game.start_game()

    while True:
        try:
            player_input = input("\n🎭 You: ").strip()

            if player_input.lower() == 'quit':
                print("Thanks for playing the Ultimate AI Dungeon Master!")
                break
            elif player_input.lower() == 'stats':
                print(json.dumps(game.get_detailed_stats(), indent=2))
            elif player_input.lower() == 'character':
                game.character_sheet.display_sheet()
            elif player_input.lower() in ('quests', 'quest'):
                game.quest_tracker.display_quests()
            elif player_input.lower() == 'inventory':
                for i, item in enumerate(game.character_sheet.inventory, 1):
                    print(f"  {i}. {item}")
            elif player_input.lower() == 'eval':
                await game.run_stability_test(5)
            elif player_input.lower() == 'help':
                print("Commands: quit, stats, character, quests, inventory, eval, help")
            else:
                await game.process_player_action(player_input)

        except KeyboardInterrupt:
            print("\nAdventure interrupted! Thanks for playing!")
            break
        except Exception as e:
            logger.error("unhandled_game_error", exc_info=True)
            print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
