import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import AsyncGenerator

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response_stream(self, prompt: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = None, model: str = "llama3.2"):
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model

    async def generate_response_stream(self, prompt: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or self._get_default_system_prompt(),
            "stream": True,
            "options": {"temperature": 0.8, "top_p": 0.9, "num_predict": 250, "num_ctx": 4096}
        }
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=payload, timeout=60.0) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
            except Exception as e:
                yield f"\n[Error connecting to Ollama: {e}]"

    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        response_text = ""
        async for chunk in self.generate_response_stream(prompt, system_prompt):
            response_text += chunk
        return response_text

    async def generate_json(self, prompt: str, system_prompt: str = None) -> dict:
        """Forces Ollama to return raw JSON and parses it instantly."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "You are a strict data extraction parser. Return valid JSON only.",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 100, "num_ctx": 2048}
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                # Parse the raw JSON string that the LLM generated
                return json.loads(data.get("response", "{}"))
            except Exception as e:
                print(f"[JSON Extraction Error: {e}]")
                return {}

    def _get_default_system_prompt(self) -> str:
        return """You are an AI Dungeon Master for a tabletop RPG. You must:
1. Maintain narrative consistency across all interactions
2. Remember and reference past events appropriately
3. Create immersive, engaging story responses
4. Keep responses concise but descriptive
5. Always ask what the player wants to do next
6. Never contradict established story elements"""




class GroqProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model

    async def generate_response_stream(self, prompt: str, system_prompt: str = None) -> AsyncGenerator[str, None]:
        if not self.api_key or self.api_key == "put_your_api_key_here":
            yield "[Error: GROQ_API_KEY clearly not set in environment or .env file]"
            return

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [{"role": "user", "content": prompt}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        else:
            messages.insert(0, {"role": "system", "content": "You are an AI Dungeon Master for a tabletop RPG."})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "stream": True
        }

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=payload, headers=headers, timeout=60.0) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if data["choices"][0]["delta"].get("content"):
                                    yield data["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                yield f"\n[Error connecting to Groq API: {e}]"

    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        response_text = ""
        async for chunk in self.generate_response_stream(prompt, system_prompt):
            response_text += chunk
        return response_text

    async def generate_json(self, prompt: str, system_prompt: str = None) -> dict:
        """Forces Groq to return raw JSON."""
        if not self.api_key or self.api_key == "put_your_api_key_here":
            return {}

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt or "You are a strict data extraction parser. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as e:
                print(f"[JSON Extraction Error: {e}]")
                return {}

class PromptManager:
    """Enhanced prompt management with better consistency prompts"""
    
    @staticmethod
    def build_enhanced_game_prompt(player_input: str, context: str, turn_number: int) -> str:
        prompt = f"""
{context}

=== Current Turn {turn_number} ===
Player Action: {player_input}

CRITICAL INSTRUCTIONS for the Dungeon Master:
1. CONSISTENCY: Always refer to established facts from the context above
2. MEMORY: Reference past events, characters, and locations when relevant
3. NPCS: If mentioning characters, use their established names and relationships
4. CONTINUITY: Make sure your response flows logically from recent events
5. ENGAGEMENT: Ask what the player wants to do next
6. CONCISENESS: Keep responses focused and under 200 words
7. MECHANICS: If the player gains/loses items, gold, health, or experience, state the EXACT numeric value explicitly in your narration (e.g., "You steal 15 gold", "You take 10 damage").

As the Dungeon Master, provide a response that:
- Acknowledges the player's action appropriately
- Describes realistic consequences based on established story elements
- Maintains absolute consistency with all past events mentioned above
- References relevant NPCs and their known relationships/traits
- Sets up the next scene or choice for the player
- Ends by asking what the player wants to do next

Your Response:"""
        return prompt
