"""Pluggable summarization strategies for Summit."""

from abc import ABC, abstractmethod
from typing import Optional
import os
import asyncio
import httpx


class Summarizer(ABC):
    """Base class for text summarization strategies."""
    
    @abstractmethod
    async def summarize(self, text: str, title: str) -> str:
        """
        Summarize the given text.
        
        Args:
            text: The text to summarize
            title: The title/context for the text
            
        Returns:
            A summary string
        """
        pass


class AnthropicSummarizer(Summarizer):
    """AI-powered summarization using Anthropic's Claude."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-haiku-20241022", summary_length: int = 800):
        """
        Initialize Anthropic summarizer.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        import anthropic
        
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY environment variable.")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.summary_length = summary_length
    
    async def summarize(self, text: str, title: str) -> str:
        """Summarize text using Claude API."""
        prompt = f"""Please provide a succinct summary of around {self.summary_length} words of this video transcript.
The video title is: {title}

Transcript:
{text[:50000]}  # Limit to avoid token limits

Focus on the key points and main takeaways.
Write the summary in present tense, as if you are directly conveying the talk's content while it is being given, not talking about the video or transcript itself.
In your response, output only the summary text itself:
- Do NOT include any preamble like 'Summary:' or 'Here is a summary'.
- Do NOT say phrases like 'in this video', 'the speaker says', or 'this talk'.
- Do NOT repeat or restate the talk title.
- Do NOT list the speakers; assume they are handled separately."""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Error with Anthropic summarization: {e}")
            return "Summary unavailable due to an error."


class OpenAISummarizer(Summarizer):
    """AI-powered summarization using OpenAI's GPT models."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", summary_length: int = 800):
        """
        Initialize OpenAI summarizer.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
        """
        from openai import AsyncOpenAI
        
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        self.summary_length = summary_length
    
    async def summarize(self, text: str, title: str) -> str:
        """Summarize text using OpenAI API."""
        prompt = f"""Please provide a succinct summary of around {self.summary_length} words of this video transcript.
The video title is: {title}

Transcript:
{text[:50000]}  # Limit to avoid token limits

Focus on the key points and main takeaways.
In your response, output only the summary text itself:
- Do NOT include any preamble like 'Summary:' or 'Here is a summary'.
- Do NOT repeat or restate the talk title.
- Do NOT list the speakers; assume they are handled separately."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error with OpenAI summarization: {e}")
            return "Summary unavailable due to an error."


class GeminiSummarizer(Summarizer):
    """AI-powered summarization using Google's Gemini."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp", summary_length: int = 800):
        """
        Initialize Gemini summarizer.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Gemini model to use
        """
        import google.generativeai as genai
        
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        self.summary_length = summary_length
    
    async def summarize(self, text: str, title: str) -> str:
        """Summarize text using Gemini API with retry logic."""
        import asyncio
        import time
        
        prompt = f"""Please provide a succinct summary of around {self.summary_length} words of this video transcript.
The video title is: {title}

Transcript:
{text[:50000]}  # Limit to avoid token limits

Focus on the key points and main takeaways.
In your response, output only the summary text itself:
- Do NOT include any preamble like 'Summary:' or 'Here is a summary'.
- Do NOT repeat or restate the talk title.
- Do NOT list the speakers; assume they are handled separately."""
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Extract retry delay from error message if available
                        retry_delay = base_delay * (2 ** attempt)
                        if "retry in" in error_str.lower():
                            try:
                                # Try to extract the suggested delay
                                import re
                                match = re.search(r'retry in (\d+\.?\d*)', error_str.lower())
                                if match:
                                    retry_delay = float(match.group(1))
                            except:
                                pass
                        
                        print(f"Rate limit hit, retrying in {retry_delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(retry_delay)
                        continue
                
                print(f"Error with Gemini summarization: {e}")
                return "Summary unavailable due to an error."
        
        return "Summary unavailable - rate limit exceeded."


class OllamaSummarizer(Summarizer):
    """Summarization using a local Ollama server."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "granite3.3:2b", sequential: bool = True, summary_length: int = 800):
        """Initialize Ollama summarizer.

        Args:
            base_url: Base URL for the Ollama server
            model: Ollama model to use (e.g., "granite3.3:2b")
            sequential: If True, serialize summarize() calls (useful for single-request-at-a-time servers)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.summary_length = summary_length

        # Sequential mode can be enabled either via constructor flag or env var OLLAMA_SEQUENTIAL
        env_seq = os.environ.get("OLLAMA_SEQUENTIAL", "").lower() in ("1", "true", "yes")
        self._sequential = sequential or env_seq
        self._lock: Optional[asyncio.Lock] = asyncio.Lock() if self._sequential else None
        # Use a single async client for efficiency
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def summarize(self, text: str, title: str) -> str:
        """Summarize text, optionally enforcing sequential calls when requested."""
        if self._lock is not None:
            async with self._lock:
                return await self._summarize_once(text, title)
        return await self._summarize_once(text, title)

    async def _summarize_once(self, text: str, title: str) -> str:
        """Summarize text using the Ollama chat API."""
        prompt = f"""Please provide a succinct summary of around {self.summary_length} words of this video transcript.
The video title is: {title}

Transcript:
{text[:50000]}

Focus on the key points and main takeaways.
Write the summary in present tense, as if you are directly conveying the talk's content while it is being given, not talking about the video or transcript itself.
In your response, output only the summary text itself:
- Do NOT include any preamble like 'Summary:' or 'Here is a summary'.
- Do NOT say phrases like 'in this video', 'the speaker says', or 'this talk'.
- Do NOT repeat or restate the talk title.
- Do NOT list the speakers; assume they are handled separately."""

        try:
            response = await self._client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Ollama chat API typically returns {"message": {"role": ..., "content": ...}, ...}
            message = data.get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

            return "Summary unavailable: unexpected Ollama response format."
        except Exception as e:
            print(f"Error with Ollama summarization: {e}")
            return "Summary unavailable due to an error."


def get_summarizer(strategy: str = "anthropic", **kwargs) -> Summarizer:
    """
    Factory function to get a summarizer instance.
    
    Args:
        strategy: Summarization strategy ("openai", "gemini", "anthropic", or "ollama")
        **kwargs: Additional arguments passed to the summarizer constructor
        
    Returns:
        A Summarizer instance
        
    Raises:
        ValueError: If strategy is not recognized
    """
    strategies = {
        "openai": OpenAISummarizer,
        "gemini": GeminiSummarizer,
        "anthropic": AnthropicSummarizer,
        "ollama": OllamaSummarizer,
    }
    
    if strategy not in strategies:
        raise ValueError(f"Unknown strategy: {strategy}. Choose from: {list(strategies.keys())}")
    
    return strategies[strategy](**kwargs)
