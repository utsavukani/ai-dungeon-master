import json
import os
import re
import uuid
from datetime import datetime
from typing import List, Dict, Optional

import chromadb
from chromadb.utils import embedding_functions

from src.database.database import SessionLocal
from src.database.models import GameTurn, StorySummary, NPC, NPCInteraction


class ChromaMemory:
    """
    Semantic RAG memory powered by ChromaDB + HuggingFace MiniLM embeddings.

    Unlike simple SQL keyword search, this class converts every game turn into
    a 384-dimensional vector (a list of numbers that captures the *meaning* of
    the text). When the player types something new, the same model embeds it and
    ChromaDB finds the stored turns whose vectors are closest — returning
    genuinely related memories even if the exact words don't match.

    Storage: data/chroma_db/  (a local folder, fully offline, no API needed)
    Model  : all-MiniLM-L6-v2 (~80 MB, downloaded once on first run)
    """

    COLLECTION_NAME = "game_turns"

    def __init__(self, persist_dir: str = "data/chroma_db"):
        os.makedirs(persist_dir, exist_ok=True)

        # Persistent client — data survives between game sessions
        self._client = chromadb.PersistentClient(path=persist_dir)

        # HuggingFace embedding function (runs 100 % locally)
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Get-or-create the ChromaDB collection
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},  # cosine similarity for text
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_turn(self, turn_id: str, player_input: str, ai_response: str, turn_number: int, campaign_id: str):
        """
        Embed and store one game turn.

        We concatenate player + DM text so the vector captures the full
        context of that turn, not just one side of the conversation.
        """
        document = f"Player: {player_input}\nDM: {ai_response}"
        self._collection.add(
            documents=[document],
            ids=[turn_id],
            metadatas=[{"turn_number": turn_number, "campaign_id": campaign_id}],
        )

    def retrieve_similar(self, query: str, campaign_id: str, n_results: int = 3) -> List[Dict]:
        """
        Find the n_results turns most semantically similar to *query*.

        Returns a list of dicts with keys: id, document, turn_number, distance.
        distance is in [0, 1] — lower means more similar (cosine distance).
        """
        total = self._collection.count()
        if total == 0:
            return []

        n = min(n_results, total)  # can't ask for more than we have stored
        results = self._collection.query(
            query_texts=[query],
            n_results=n,
            where={"campaign_id": campaign_id}
        )

        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append({
                "id": doc_id,
                "document": results["documents"][0][i],
                "turn_number": results["metadatas"][0][i].get("turn_number", 0),
                "distance": results["distances"][0][i],
            })
        return hits

class WorkingMemory:
    """Enhanced short-term memory with summarization"""
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.memory: List[Dict] = []
        self.turn_summaries: List[Dict] = []

    def add_turn(self, player_input: str, ai_response: str, context: Optional[Dict] = None):
        turn = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "player_input": player_input or "",
            "ai_response": ai_response or "",
            "context": context or {},
            "turn_number": len(self.memory) + 1
        }
        self.memory.append(turn)

        if len(self.memory) > self.max_turns:
            removed_turn = self.memory.pop(0)
            summary = self._create_turn_summary(removed_turn)
            self.turn_summaries.append(summary)
            if len(self.turn_summaries) > 10:
                self.turn_summaries.pop(0)

    def _create_turn_summary(self, turn: Dict) -> Dict:
        return {
            "turn_number": turn.get("turn_number", -1),
            "summary": (
                f"Turn {turn.get('turn_number', 'N/A')}: "
                f"{(turn.get('player_input') or '')[:50]}..."
                f" -> {(turn.get('ai_response') or '')[:100]}..."
            ),
            "key_events": self._extract_key_events(
                turn.get("player_input") or "", turn.get("ai_response") or ""
            ),
            "timestamp": turn.get("timestamp") or datetime.now().isoformat(),
        }

    def _extract_key_events(self, player_input: str, ai_response: str) -> List[str]:
        events: List[str] = []
        characters = re.findall(r"\b[A-Z][a-z]+\b", ai_response)
        locations = re.findall(r"(?:in|at|to) the ([a-z]+)", ai_response.lower())
        items = re.findall(r"(?:find|get|take|give) (?:a |an |the )?([a-z ]+)", player_input.lower())

        if characters:
            events.append(f"met: {', '.join(sorted(set(characters)))}")
        if locations:
            events.append(f"locations: {', '.join(sorted(set(locations)))}")
        if items:
            events.append(f"items: {', '.join(sorted(set(items)))}")
        return events

    def get_recent_context(self) -> str:
        context = "=== Recent Turns (Working Memory) ===\n"
        for summary in self.turn_summaries[-3:]:
            context += f"{summary['summary']}\n"
        for turn in self.memory:
            context += f"Turn {turn.get('turn_number', 'N/A')}: Player: {turn['player_input']}\n"
            context += f"DM: {turn['ai_response']}\n\n"
        return context

    def get_memory(self) -> List[Dict]:
        return self.memory


class NPCMemoryManager:
    """Manages individual NPC memories and relationships with PostgreSQL persistence"""
    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id

    def add_or_update_npc(self, name: str, turn_number: int, interaction_context: str = "") -> str:
        base_npc_id = name.lower().strip().replace(" ", "_")
        if not base_npc_id:
            return ""
        
        # Enforce uniqueness of NPC per Campaign!
        npc_id = f"{self.campaign_id}_{base_npc_id}"

        db = SessionLocal()
        try:
            npc = db.query(NPC).filter(NPC.npc_id == npc_id, NPC.campaign_id == self.campaign_id).first()
            if not npc:
                traits = self._infer_personality_traits(interaction_context or "")
                npc = NPC(
                    npc_id=npc_id,
                    campaign_id=self.campaign_id,
                    name=name,
                    first_met_turn=turn_number,
                    personality_traits=traits,
                    last_interaction_turn=turn_number,
                    interaction_count=1,
                    memory_summary=f"First met player on turn {turn_number}"
                )
                db.add(npc)
            else:
                npc.last_interaction_turn = turn_number
                npc.interaction_count += 1
            db.commit()
            return npc_id
        finally:
            db.close()

    def add_npc_interaction(self, npc_id: str, turn_number: int, player_action: str, npc_response: str):
        if not npc_id:
            return

        relationship_change = self._analyze_relationship_change(player_action or "", npc_response or "")
        db = SessionLocal()
        try:
            interaction = NPCInteraction(
                campaign_id=self.campaign_id,
                npc_id=npc_id,
                turn_number=turn_number,
                player_action=player_action or "",
                npc_response=npc_response or "",
                relationship_change=relationship_change
            )
            db.add(interaction)

            if relationship_change != "neutral":
                npc = db.query(NPC).filter(NPC.npc_id == npc_id, NPC.campaign_id == self.campaign_id).first()
                if npc:
                    npc.relationship_status = relationship_change

            db.commit()
        finally:
            db.close()

    def get_npc_memory(self, name: str) -> Optional[Dict]:
        base_npc_id = (name or "").lower().strip().replace(" ", "_")
        if not base_npc_id:
            return None
            
        npc_id = f"{self.campaign_id}_{base_npc_id}"

        db = SessionLocal()
        try:
            npc = db.query(NPC).filter(NPC.npc_id == npc_id, NPC.campaign_id == self.campaign_id).first()
            if not npc:
                return None

            recent_interactions = db.query(NPCInteraction)\
                .filter(NPCInteraction.npc_id == npc_id, NPCInteraction.campaign_id == self.campaign_id)\
                .order_by(NPCInteraction.turn_number.desc())\
                .limit(5).all()

            return {
                "npc_id": npc.npc_id,
                "name": npc.name,
                "first_met_turn": npc.first_met_turn,
                "personality_traits": npc.personality_traits,
                "relationship_status": npc.relationship_status,
                "last_interaction_turn": npc.last_interaction_turn,
                "memory_summary": npc.memory_summary,
                "interaction_count": npc.interaction_count,
                "recent_interactions": [{"action": i.player_action, "response": i.npc_response} for i in recent_interactions]
            }
        finally:
            db.close()

    def _infer_personality_traits(self, context: str) -> str:
        traits: List[str] = []
        ctx = (context or "").lower()
        if any(w in ctx for w in ["merchant", "sell", "buy", "trade"]):
            traits.append("merchant")
        if any(w in ctx for w in ["guard", "soldier", "protect"]):
            traits.append("guard")
        if any(w in ctx for w in ["wise", "old", "sage", "knowledge"]):
            traits.append("wise")
        return ", ".join(traits) if traits else "unknown"

    def _analyze_relationship_change(self, player_action: str, npc_response: str) -> str:
        pa = (player_action or "").lower()
        nr = (npc_response or "").lower()
        if any(w in pa for w in ["help", "give", "assist", "kind"]) or any(
            w in nr for w in ["thank", "grateful", "pleased", "happy"]
        ):
            return "friendly"
        if any(w in pa for w in ["attack", "steal", "threaten", "rude"]) or any(
            w in nr for w in ["angry", "upset", "hostile", "flee"]
        ):
            return "hostile"
        return "neutral"


class EnhancedPersistentMemory:
    """Enhanced long-term memory with PostgreSQL persistence via SQLAlchemy"""
    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id

    def store_turn(self, turn_data: Dict, turn_number: int):
        player_input = (turn_data.get("player_input") or "").strip()
        ai_response = (turn_data.get("ai_response") or "").strip()

        importance = self._calculate_importance(player_input, ai_response)
        entities = self._extract_entities(player_input, ai_response)
        summary = self._create_summary(player_input, ai_response)

        db = SessionLocal()
        try:
            sql_turn = GameTurn(
                campaign_id=self.campaign_id,
                turn_number=turn_number,
                player_input=player_input,
                ai_response=ai_response,
                context=json.dumps(turn_data.get("context", {})),
                importance_score=importance,
                summary=summary,
                key_entities=json.dumps(entities)
            )
            db.add(sql_turn)
            db.commit()
            
            if turn_number % 10 == 0:
                self._create_story_summary(db, turn_number - 9, turn_number)
        finally:
            db.close()

    def retrieve_relevant_turns(self, query: str, limit: int = 5) -> List[Dict]:
        db = SessionLocal()
        try:
            q = (query or "").strip()
            if not q:
                turns = db.query(GameTurn).filter(GameTurn.campaign_id == self.campaign_id).order_by(GameTurn.turn_number.desc()).limit(limit).all()
                return self._rows_to_turn_dicts(turns)

            words = q.lower().split()
            from sqlalchemy import or_, and_
            
            filters = [GameTurn.campaign_id == self.campaign_id]
            for w in words:
                filters.append(or_(
                    GameTurn.player_input.ilike(f"%{w}%"),
                    GameTurn.ai_response.ilike(f"%{w}%"),
                    GameTurn.summary.ilike(f"%{w}%")
                ))
            
            turns = db.query(GameTurn).filter(and_(*filters)).order_by(GameTurn.turn_number.desc()).limit(limit).all()
            
            return self._rows_to_turn_dicts(turns)
        finally:
            db.close()

    def _rows_to_turn_dicts(self, turns: List[GameTurn]) -> List[Dict]:
        results: List[Dict] = []
        for turn in turns:
            data = {
                "id": turn.id,
                "timestamp": turn.timestamp,
                "turn_number": turn.turn_number,
                "player_input": turn.player_input,
                "ai_response": turn.ai_response,
                "context": json.loads(turn.context) if turn.context else {},
                "importance_score": turn.importance_score,
                "summary": turn.summary,
                "key_entities": json.loads(turn.key_entities) if turn.key_entities else [],
                "relevance_score": turn.importance_score * 2
            }
            results.append(data)
        return results

    def _calculate_importance(self, player_input: str, ai_response: str) -> float:
        importance = 1.0
        high = ["fight", "battle", "death", "quest", "treasure", "magic", "dragon", "king", "princess"]
        medium = ["npc", "character", "item", "place", "meet", "find", "discover"]

        text = f"{player_input} {ai_response}".lower()
        if any(w in text for w in high):
            importance += 2.0
        if any(w in text for w in medium):
            importance += 1.0
        if len(ai_response) > 200:
            importance += 0.5
        return min(importance, 5.0)

    def _extract_entities(self, player_input: str, ai_response: str) -> List[str]:
        text = f"{player_input} {ai_response}"
        entities: List[str] = []
        entities.extend(re.findall(r"\b[A-Z][a-z]+\b", text))
        entities.extend(re.findall(r"(?:the|a|an) ([a-z]+ ?[a-z]*)", text.lower()))
        seen = set()
        uniq = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                uniq.append(e)
        return uniq

    def _create_summary(self, player_input: str, ai_response: str) -> str:
        pi = player_input[:50] + ("..." if len(player_input) > 50 else "")
        ar = ai_response[:100] + ("..." if len(ai_response) > 100 else "")
        return f"Player: {pi} -> {ar}"

    def _create_story_summary(self, db, start_turn: int, end_turn: int):
        turns = db.query(GameTurn).filter(
            GameTurn.campaign_id == self.campaign_id,
            GameTurn.turn_number >= start_turn,
            GameTurn.turn_number <= end_turn
        ).order_by(GameTurn.turn_number).all()

        if turns:
            summaries = [t.summary for t in turns if t.summary]
            all_entities = []
            for t in turns:
                if t.key_entities:
                    try:
                        all_entities.extend(json.loads(t.key_entities))
                    except Exception:
                        pass

            story_summary = f"Turns {start_turn}-{end_turn}: " + " | ".join(summaries[:3])
            key_events = []
            seen = set()
            for e in all_entities:
                if e not in seen:
                    seen.add(e)
                    key_events.append(e)
                    if len(key_events) >= 10:
                        break

            summary_record = StorySummary(
                campaign_id=self.campaign_id,
                turn_range=f"{start_turn}-{end_turn}",
                summary=story_summary,
                key_events=json.dumps(key_events)
            )
            db.add(summary_record)
            db.commit()


class EnhancedMemoryManager:
    """Manages all memory systems (Working, Episodic, Vector, NPC) per Campaign"""

    def __init__(self, campaign_id: str):
        self.campaign_id = campaign_id
        self.working_memory = WorkingMemory(max_turns=5)
        self.persistent_memory = EnhancedPersistentMemory(campaign_id=self.campaign_id)
        self.npc_memory = NPCMemoryManager(campaign_id=self.campaign_id)
        self.chroma_memory = ChromaMemory()
        self.turn_counter = 0
        self._load_state()

    def _load_state(self):
        """Restore turn counter and working memory from SQL"""
        db = SessionLocal()
        try:
            latest_turn = db.query(GameTurn).filter(GameTurn.campaign_id == self.campaign_id)\
                .order_by(GameTurn.turn_number.desc()).first()
            if latest_turn:
                self.turn_counter = latest_turn.turn_number
                # Load last 5 turns into working memory
                recent_turns = db.query(GameTurn).filter(GameTurn.campaign_id == self.campaign_id)\
                    .order_by(GameTurn.turn_number.desc()).limit(5).all()
                recent_turns.reverse()
                for t in recent_turns:
                    ctx = json.loads(t.context) if t.context else {}
                    self.working_memory.add_turn(t.player_input, t.ai_response, ctx)
        finally:
            db.close()

    def process_turn(self, player_input: str, ai_response: str, context: Optional[Dict] = None):
        self.turn_counter += 1

        # Process NPCs mentioned in this turn
        self._process_npcs_in_turn(player_input or "", ai_response or "")

        # Add to working memory
        self.working_memory.add_turn(player_input or "", ai_response or "", context)

        # Store in persistent memory
        turn_id = str(uuid.uuid4())
        turn_data = {
            "id": turn_id,
            "timestamp": datetime.now().isoformat(),
            "player_input": player_input or "",
            "ai_response": ai_response or "",
            "context": context or {},
        }
        # Store in SQL database
        self.persistent_memory.store_turn(turn_data, self.turn_counter)
        # Store in ChromaDB vector index
        self.chroma_memory.add_turn(
            turn_id=turn_id,
            player_input=player_input or "",
            ai_response=ai_response or "",
            turn_number=self.turn_counter,
            campaign_id=self.campaign_id
        )

    def _process_npcs_in_turn(self, player_input: str, ai_response: str):
        npc_names = re.findall(r"\b([A-Z][a-z]+ ?[A-Z]?[a-z]*)\b", ai_response or "")
        for name in npc_names:
            if len(name.split()) <= 2 and name not in {"You", "The", "Player"}:
                npc_id = self.npc_memory.add_or_update_npc(name, self.turn_counter, ai_response or "")
                self.npc_memory.add_npc_interaction(npc_id, self.turn_counter, player_input or "", ai_response or "")

    def get_context_for_llm(self, current_input: str) -> str:
        context = ""
        context += self.working_memory.get_recent_context()

        # Semantic RAG retrieval (NEW)
        # ChromaDB finds turns conceptually related to the campaign
        chroma_hits = self.chroma_memory.retrieve_similar(current_input or "", self.campaign_id, n_results=3)
        if chroma_hits:
            context += "\n=== Relevant Past Events (Semantic Search) ===\n"
            for hit in chroma_hits:
                similarity_pct = round((1 - hit["distance"]) * 100, 1)
                context += (
                    f"Turn {hit['turn_number']} "
                    f"(similarity: {similarity_pct}%): {hit['document'][:200]}...\n"
                )
        # ── Fallback: keyword SQL search ──────────────────────────────────────
        # Still run the old retrieval too — if chroma has no hits yet (first
        # few turns before the model warms up), SQL ensures we never return
        # an empty context.
        elif True:
            relevant_turns = self.persistent_memory.retrieve_relevant_turns(current_input or "", limit=3)
            if relevant_turns:
                context += "\n=== Relevant Past Events ===\n"
                for t in relevant_turns:
                    imp = t.get("importance_score", 1.0)
                    summ = t.get("summary", "")
                    tn = t.get("turn_number", "?")
                    context += f"Turn {tn} (importance: {imp:.1f}): {summ}\n"

        # NPC context (unchanged)
        relevant_turns = self.persistent_memory.retrieve_relevant_turns(current_input or "", limit=3)
        context += self._get_npc_context(current_input or "", relevant_turns or [])

        return context

    def _get_npc_context(self, current_input: str, relevant_turns: List[Dict]) -> str:
        npc_context = ""
        potential_npcs = re.findall(r"\b[A-Z][a-z]+\b", current_input or "")

        for t in relevant_turns:
            for ent in t.get("key_entities", []):
                if isinstance(ent, str) and ent and ent[0].isupper():
                    potential_npcs.append(ent)

        for npc_name in sorted(set(potential_npcs)):
            mem = self.npc_memory.get_npc_memory(npc_name)
            if mem:
                npc_context += f"\n=== {mem['name']} (NPC Memory) ===\n"
                npc_context += f"Relationship: {mem['relationship_status']}\n"
                npc_context += f"Traits: {mem['personality_traits']}\n"
                npc_context += f"Memory: {mem['memory_summary']}\n"
                npc_context += f"Interactions: {mem['interaction_count']} times\n"

        return npc_context
