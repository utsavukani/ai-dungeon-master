import pytest
from unittest.mock import patch
from src.llm.provider import GroqProvider, OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_mocked():
    """OllamaProvider streams and assembles text correctly."""
    provider = OllamaProvider()

    async def mock_stream(*args, **kwargs):
        yield "The cave is dark."
        yield " Watch out for goblins."

    with patch.object(provider, 'generate_response_stream', new=mock_stream):
        response = await provider.generate_response("Look around")
        assert "dark" in response
        assert "goblins" in response


@pytest.mark.asyncio
async def test_groq_provider_no_key():
    """GroqProvider returns an error message when the API key is not set."""
    provider = GroqProvider(api_key="put_your_api_key_here")

    chunks = []
    async for chunk in provider.generate_response_stream("Hello"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert "Error" in chunks[0]
