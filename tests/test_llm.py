import pytest
from unittest.mock import AsyncMock, patch

from src.llm.provider import OpenAIProvider, OllamaProvider

@pytest.mark.asyncio
async def test_ollama_provider_mocked():
    provider = OllamaProvider()
    
    async def mock_stream(*args, **kwargs):
        yield "The cave is dark."
        yield " Watch out for goblins."

    with patch.object(provider, 'generate_response_stream', new=mock_stream):
        response = await provider.generate_response("Look around")
        assert "dark" in response
        assert "goblins" in response

@pytest.mark.asyncio
async def test_openai_provider_mock_no_key():
    # If no key is set, it yields an error
    with patch.dict('os.environ', clear=True):
        provider = OpenAIProvider(api_key=None)
        
        chunks = []
        async for chunk in provider.generate_response_stream("Hello"):
            chunks.append(chunk)
            
        assert "Error:" in chunks[0]
