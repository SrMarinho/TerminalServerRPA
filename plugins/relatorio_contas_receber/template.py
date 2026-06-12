import re
from datetime import datetime

TEMPLATE_VARS = [
    {"name": "report_code", "hint": "código do relatório", "source": "relatorio"},
    {"name": "report_desc", "hint": "descrição do relatório"},
    {"name": "now", "hint": "data+hora (%Y%m%d_%H%M%S)"},
    {"name": "date", "hint": "data (%Y%m%d)"},
    {"name": "year", "hint": "ano (%Y)"},
    {"name": "month", "hint": "mês (%m)"},
    {"name": "day", "hint": "dia (%d)"},
    {"name": "time", "hint": "hora (%H%M%S)"},
]

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def render_template(template: str, ctx: dict, *, is_path: bool = False) -> str:
    now = datetime.now()
    base = {
        "now": now.strftime("%Y%m%d_%H%M%S"),
        "date": now.strftime("%Y%m%d"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "time": now.strftime("%H%M%S"),
        **{k: str(v) for k, v in ctx.items() if v is not None},
    }

    def replace(m):
        key, fmt = m.group(1), m.group(2)
        if fmt:
            return now.strftime(fmt)
        return base.get(key, m.group(0))

    result = re.sub(r"\{(\w+)(?::([^}]+))?\}", replace, template)
    if not is_path:
        result = _INVALID_FILENAME_CHARS.sub("_", result)
    return result
