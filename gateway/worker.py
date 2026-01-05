"""
CPU-based echo worker for M1 - simulates streaming LLM responses.
"""
import asyncio
import random
from typing import AsyncGenerator


class EchoWorker:
    """
    Simple echo worker that simulates LLM inference by echoing back
    the input with some variation. Used for M1 to test the service
    infrastructure before connecting real engines.
    """
    
    def __init__(self):
        self.min_delay = 0.05  # Minimum delay between tokens (seconds)
        self.max_delay = 0.15  # Maximum delay between tokens
    
    async def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """
        Generate a non-streaming response.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Echo with variation
        words = prompt.split()
        response_words = []
        
        # Add a prefix
        response_words.append("Echo:")
        
        # Echo back words with some variation
        for i, word in enumerate(words[:max_tokens]):
            if random.random() > 0.3:  # 70% chance to echo
                response_words.append(word)
            else:  # 30% chance to add variation
                response_words.append(f"[{word}]")
        
        # Add some additional tokens
        additional = ["This", "is", "a", "simulated", "response", "from", "the", "echo", "worker."]
        response_words.extend(additional[:max(0, max_tokens - len(response_words))])
        
        return " ".join(response_words[:max_tokens])
    
    async def generate_stream(self, prompt: str, max_tokens: int = 100) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response token by token.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Yields:
            Token strings
        """
        # Simulate initial processing delay (prefill)
        await asyncio.sleep(0.1)
        
        # Generate response
        words = prompt.split()
        response_words = []
        
        # Add prefix
        response_words.append("Echo:")
        
        # Echo back words
        for word in words[:max_tokens]:
            if random.random() > 0.3:
                response_words.append(word)
            else:
                response_words.append(f"[{word}]")
        
        # Add additional tokens
        additional = ["This", "is", "a", "simulated", "streaming", "response."]
        response_words.extend(additional[:max(0, max_tokens - len(response_words))])
        
        # Stream tokens with delay
        for word in response_words[:max_tokens]:
            yield word + " "
            delay = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)

