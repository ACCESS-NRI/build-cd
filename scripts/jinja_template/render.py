import os
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("."))


def render_using_context(template_path: str, context: dict) -> str:

    template = env.get_template(template_path)
    return template.render(context)
