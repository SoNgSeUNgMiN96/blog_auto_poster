import json
from string import Formatter
from typing import Any

from openai import OpenAI

from app.config import Settings


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class ContentGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        api_key = settings.effective_openai_api_key
        self.client = OpenAI(api_key=api_key) if api_key else None

    @staticmethod
    def render_prompt(template: str, variables: dict[str, Any]) -> str:
        parsed_keys = [field_name for _, field_name, _, _ in Formatter().parse(template) if field_name]
        safe_vars = _SafeDict(variables)
        rendered = template.format_map(safe_vars)
        if not parsed_keys:
            return template
        return rendered

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt_template = payload.get("prompt_template", "")
        prompt_variables = payload.get("prompt_variables", {})
        rendered_prompt = self.render_prompt(prompt_template, prompt_variables)
        system_role = payload.get("system_role") or "You generate structured blog content in JSON only."

        if not self.client:
            raise RuntimeError("OPENAI API key is not configured")

        completion = self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0.78,
            messages=[
                {"role": "system", "content": system_role},
                {
                    "role": "user",
                    "content": (
                        f"{rendered_prompt}\n\n"
                        "Return ONLY valid JSON with this schema: "
                        '{"title":"","sections":[{"heading":"","content":""}],"tags":[],"meta_description":""}'
                    ),
                },
            ],
        )

        raw_text = completion.choices[0].message.content or "{}"
        content = self._parse_json(raw_text)
        self._validate_schema(content)
        return content

    @staticmethod
    def _parse_json(raw_text: str) -> dict[str, Any]:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw_text[start : end + 1])
            raise

    @staticmethod
    def _validate_schema(content: dict[str, Any]) -> None:
        if not isinstance(content.get("title"), str):
            raise ValueError("Generated content missing 'title'")
        if not isinstance(content.get("sections"), list):
            raise ValueError("Generated content missing 'sections'")
        if not isinstance(content.get("tags", []), list):
            raise ValueError("Generated content 'tags' should be list")
        if not isinstance(content.get("meta_description", ""), str):
            raise ValueError("Generated content 'meta_description' should be str")
