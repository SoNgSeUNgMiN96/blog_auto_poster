from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


class HtmlRenderer:
    def __init__(self, template_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters["md"] = self._markdown_to_html

    @staticmethod
    def _markdown_to_html(value: Any) -> Markup:
        text = str(value or "")
        html = markdown.markdown(
            text,
            extensions=[
                "extra",
                "sane_lists",
                "nl2br",
            ],
            output_format="html5",
        )
        return Markup(html)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)
