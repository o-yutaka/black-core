from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI


class ContentGenerator:
    def __init__(self, memory_path: str = "memory.json", model: str = "gpt-4.1-mini") -> None:
        self.memory_path = Path(memory_path)
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate(self, topic: str, top_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        style_hints = self._build_style_hints(top_posts)
        seed = random.randint(0, 10_000_000)
        prompt = (
            "You are an elite social media growth operator. Create ONE short post optimized for virality. "
            "Return plain text only, no markdown, no quotes.\n"
            f"Topic: {topic}\n"
            f"High-performing pattern hints: {style_hints}\n"
            "Constraints: <260 chars, specific, energetic, curiosity-driven, avoid repeating old phrasing exactly, "
            "include one concrete claim or mechanism, and optionally include 1-2 hashtags.\n"
            f"Variation seed: {seed}"
        )

        text = self._generate_with_openai(prompt)
        text = self._ensure_variation(text=text, top_posts=top_posts, topic=topic, seed=seed)

        return {
            "topic": topic,
            "content": text,
            "style_hints": style_hints,
            "seed": seed,
        }

    def _generate_with_openai(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=1.0,
            max_output_tokens=160,
        )
        text = response.output_text.strip()
        if not text:
            raise RuntimeError("OpenAI returned empty response text")
        return text.replace("\n", " ").strip()

    def _build_style_hints(self, top_posts: List[Dict[str, Any]]) -> str:
        if not top_posts:
            return "short-hook, strong claim, direct CTA bridge"
        snippets = []
        for post in top_posts[:5]:
            body = post.get("content", "")
            if body:
                snippets.append(body[:120])
        return " | ".join(snippets) if snippets else "short-hook, strong claim"

    def _ensure_variation(self, text: str, top_posts: List[Dict[str, Any]], topic: str, seed: int) -> str:
        normalized_new = " ".join(text.lower().split())
        previous = {" ".join(p.get("content", "").lower().split()) for p in top_posts}
        if normalized_new not in previous:
            return text

        token = hashlib.sha1(f"{topic}-{seed}".encode("utf-8")).hexdigest()[:6]
        variant = f"{text} | Angle shift {token}"
        return variant[:255]


if __name__ == "__main__":
    generator = ContentGenerator()
    memory = json.loads(Path("memory.json").read_text(encoding="utf-8")) if Path("memory.json").exists() else {"posts": []}
    top = sorted(memory.get("posts", []), key=lambda x: x.get("score", 0), reverse=True)[:3]
    print(generator.generate(topic="AI automation for creators", top_posts=top)["content"])
