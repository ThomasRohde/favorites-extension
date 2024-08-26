from abc import ABC, abstractmethod
import ollama
from openai import OpenAI
import os
from typing import Optional, Generator, Any
from anthropic import Anthropic, AsyncAnthropic

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

    @abstractmethod
    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = 'phi3.5'):
        self.model = model

    def generate(self, prompt: str) -> str:
        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            return response['response']
        except Exception as e:
            raise RuntimeError(f"Error generating response with Ollama: {str(e)}")

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        try:
            stream = ollama.generate(model=self.model, prompt=prompt, stream=True)
            for chunk in stream:
                yield chunk['response']
        except Exception as e:
            raise RuntimeError(f"Error generating streaming response with Ollama: {str(e)}")

class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = OpenAI()

    def generate(self, prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Error generating response with OpenAI: {str(e)}")

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"Error generating streaming response with OpenAI: {str(e)}")

    def generate_with_metadata(self, prompt: str) -> tuple[str, Any]:
        try:
            response = self.client.chat.completions.with_raw_response.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            completion = response.parse()
            return completion.choices[0].message.content, response.request_id
        except Exception as e:
            raise RuntimeError(f"Error generating response with metadata from OpenAI: {str(e)}")

class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.model = model
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key not found. Please set the ANTHROPIC_API_KEY environment variable.")
        self.client = Anthropic()

    def generate(self, prompt: str) -> str:
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Error generating response with Anthropic: {str(e)}")

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        try:
            stream = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                stream=True,
            )
            for event in stream:
                if event.type == "content_block_delta":
                    yield event.delta.text
        except Exception as e:
            raise RuntimeError(f"Error generating streaming response with Anthropic: {str(e)}")

class LLMService:
    def __init__(self, provider: Optional[LLMProvider] = None):
        if provider is None:
            # Default to Ollama if no provider is specified
            provider = OllamaProvider()
        self.provider = provider

    def generate(self, prompt: str) -> str:
        return self.provider.generate(prompt)

    def generate_stream(self, prompt: str) -> Generator[str, None, None]:
        return self.provider.generate_stream(prompt)

    def generate_with_metadata(self, prompt: str) -> tuple[str, Any]:
        if isinstance(self.provider, OpenAIProvider):
            return self.provider.generate_with_metadata(prompt)
        else:
            return self.generate(prompt), None

# Initialize with default provider (Ollama)
# llm_service = LLMService()

# To use OpenAI provider, uncomment the following line and ensure OPENAI_API_KEY is set
# llm_service = LLMService(OpenAIProvider())

# To use Anthropic provider, uncomment the following line and ensure ANTHROPIC_API_KEY is set
llm_service = LLMService(AnthropicProvider())