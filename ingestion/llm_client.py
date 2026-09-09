"""
llm_client.py
Week 3: a lightweight gateway-style client, in the same spirit as the
separate LLM Gateway project -- tries providers in priority order,
falls back to the next on failure, and logs token usage per call.

Providers are only added if their API key is present in the environment
(GROQ_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY) -- no keys are
hardcoded. If no key is available at all, calls fall back to MOCK_MODE,
which builds a deterministic answer directly from the retrieved context.
This keeps the RAG plumbing (retrieval -> prompt -> citations) fully
testable offline, without burning API credits or requiring a live key.
"""

import os
import time


class LLMClient:
    def __init__(self):
        self.providers = []
        if os.getenv("GROQ_API_KEY"):
            self.providers.append(("groq", self._call_groq))
        if os.getenv("OPENAI_API_KEY"):
            self.providers.append(("openai", self._call_openai))
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers.append(("anthropic", self._call_anthropic))

        self.usage_log = []

    def _log_usage(self, provider, prompt_tokens, completion_tokens):
        self.usage_log.append({
            "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "timestamp": time.time(),
        })

    def _call_groq(self, prompt):
        import requests
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        self._log_usage("groq", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return text

    def _call_openai(self, prompt):
        import requests
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        self._log_usage("openai", usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        return text

    def _call_anthropic(self, prompt):
        import requests
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        usage = data.get("usage", {})
        self._log_usage("anthropic", usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return text

    def _mock_answer(self, context_chunks):
        self._log_usage("mock", 0, 0)
        if not context_chunks:
            return "No relevant information was found in the client's data for this question."
        lead = context_chunks[0]["text"]
        return f"Based on the retrieved data: {lead}"

    def generate(self, prompt, context_chunks=None):
        """
        Tries each configured provider in order; returns (answer_text, provider_name).
        Falls back to a deterministic mock answer if every provider fails or
        none are configured.
        """
        for name, fn in self.providers:
            try:
                return fn(prompt), name
            except Exception as e:
                print(f"  [llm_client] {name} failed ({e}), trying next provider...")
                continue
        return self._mock_answer(context_chunks or []), "mock"
