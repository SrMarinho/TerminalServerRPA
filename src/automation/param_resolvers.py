import calendar
import re
from datetime import date, timedelta

_FMT = "%d/%m/%Y"


# ---------------------------------------------------------------------------
# DateRange — objeto retornável por resolvers com suporte a chaining
# ---------------------------------------------------------------------------


class DateRange:
    def __init__(self, start: date, end: date):
        self._start = start
        self._end = end

    def first(self) -> str:
        """Primeiro dia do intervalo."""
        return self._start.strftime(_FMT)

    def last(self) -> str:
        """Último dia do intervalo."""
        return self._end.strftime(_FMT)

    def __str__(self) -> str:
        return f"{self._start.strftime(_FMT)}-{self._end.strftime(_FMT)}"

    def __repr__(self) -> str:
        return str(self)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _subtract_months(d: date, months: int) -> date:
    total = d.month - months
    year = d.year + (total - 1) // 12
    month = ((total - 1) % 12) + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def _end_of_month(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


# ---------------------------------------------------------------------------
# Resolver registry
# ---------------------------------------------------------------------------

RESOLVERS: dict = {
    "date": {
        "today": {
            "label": "Hoje",
            "description": "Data de hoje: dd/mm/yyyy.",
            "params": [],
            "fn": lambda: date.today().strftime(_FMT),
        },
        "yesterday": {
            "label": "Ontem",
            "description": "Data de ontem: dd/mm/yyyy.",
            "params": [],
            "fn": lambda: (date.today() - timedelta(days=1)).strftime(_FMT),
        },
        "back": {
            "label": "N dias/meses atrás",
            "description": "Data de início do lookback (N dias ou meses atrás). Use concat para compor ranges.",
            "params": [
                {"name": "days", "type": "number", "label": "Dias", "default": 0},
                {"name": "months", "type": "number", "label": "Meses", "default": 0},
            ],
            "fn": lambda days=0, months=0: (
                _subtract_months(date.today(), int(months)) - timedelta(days=int(days))
            ).strftime(_FMT),
        },
        "month": {
            "label": "Mês atual",
            "description": "Do primeiro ao último dia do mês corrente.",
            "params": [],
            "fn": lambda: DateRange(date.today().replace(day=1), _end_of_month(date.today())),
        },
        "last_month": {
            "label": "Mês anterior",
            "description": "Do primeiro ao último dia do mês anterior.",
            "params": [],
            "fn": lambda: (lambda f: DateRange(f, _end_of_month(f)))(
                (date.today().replace(day=1) - timedelta(days=1)).replace(day=1)
            ),
        },
    }
}


FUNCTIONS: dict = {
    "concat": lambda *args: "".join(str(a) for a in args),
}


FUNCTIONS_META: dict = {
    "concat": {
        "label": "Concatenar",
        "description": "Junta múltiplos valores em string. Ex: =concat(date.back(30), '-', date.today())",
        "params": [],
        "variadic": True,
    },
}


def resolver_meta() -> dict:
    """Metadados sem 'fn' — seguro para expor via API."""
    result: dict = {
        ns: {fn: {k: v for k, v in meta.items() if k != "fn"} for fn, meta in fns.items()}
        for ns, fns in RESOLVERS.items()
    }
    result["__fn__"] = {name: {k: v for k, v in meta.items()} for name, meta in FUNCTIONS_META.items()}
    return result


# ---------------------------------------------------------------------------
# Parser recursivo
# ---------------------------------------------------------------------------


def _split_args(s: str) -> list[str]:
    """Divide args por vírgula respeitando parênteses aninhados."""
    args, current, depth = [], [], 0
    for ch in s:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append("".join(current).strip())
    return [a for a in args if a]


def _coerce(value, param_type: str):
    if param_type == "number":
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    return str(value)


def _parse_expr(s: str):
    """Avalia expressão recursivamente. Retorna valor resolvido."""
    s = s.strip()

    # keyword arg: name=value — marcado como tuple para o caller
    kw_match = re.match(r"^(\w+)=(.+)$", s, re.DOTALL)
    if kw_match and "." not in kw_match.group(1) and "(" not in kw_match.group(1):
        key = kw_match.group(1)
        val = _parse_chained(kw_match.group(2).strip())
        return ("__kw__", key, val)

    # bare fn(args...) — lookup in FUNCTIONS
    bare_match = re.match(r"^(\w+)\((.*)\)$", s, re.DOTALL)
    if bare_match:
        fn_name, args_raw = bare_match.group(1), bare_match.group(2).strip()
        fn = FUNCTIONS.get(fn_name)
        if fn:
            raw_args = _split_args(args_raw) if args_raw else []
            resolved_args = [_parse_chained(a.strip()) for a in raw_args]
            return fn(*resolved_args)

    # ns.fn(args...)
    fn_match = re.match(r"^(\w+)\.(\w+)\((.*)\)$", s, re.DOTALL)
    if fn_match:
        ns, fn_name, args_raw = fn_match.group(1), fn_match.group(2), fn_match.group(3).strip()
        entry = RESOLVERS.get(ns, {}).get(fn_name)
        if not entry:
            return s
        raw_args = _split_args(args_raw) if args_raw else []
        kwargs: dict = {}
        pos_idx = 0
        for raw in raw_args:
            resolved = _parse_expr(raw.strip())
            if isinstance(resolved, tuple) and resolved[0] == "__kw__":
                _, k, v = resolved
                p = next((p for p in entry["params"] if p["name"] == k), None)
                kwargs[k] = _coerce(v, p["type"]) if p else v
            else:
                if pos_idx < len(entry["params"]):
                    p = entry["params"][pos_idx]
                    kwargs[p["name"]] = _coerce(resolved, p["type"])
                pos_idx += 1
        return entry["fn"](**kwargs)

    # número
    try:
        return int(s)
    except (ValueError, TypeError):
        pass
    try:
        return float(s)
    except (ValueError, TypeError):
        pass

    # string literal com aspas
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]

    return s


def _parse_chained(s: str):
    """Avalia expressão com suporte a chaining: expr.method().method()"""
    s = s.strip()
    paren_pos = s.find("(")
    if paren_pos == -1:
        return _parse_expr(s)

    # acha o ) de fechamento da chamada base
    depth, close = 0, -1
    for i in range(paren_pos, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                close = i
                break

    if close == -1:
        return _parse_expr(s)

    base_str = s[: close + 1]
    chain_str = s[close + 1 :]  # ex: ".first()" ou ".first().last()"
    result = _parse_expr(base_str)

    # aplica métodos encadeados
    for m in re.finditer(r"\.(\w+)\(\)", chain_str):
        method = m.group(1)
        if hasattr(result, method) and callable(getattr(result, method)):
            result = getattr(result, method)()
        else:
            break

    return result


def _parse_formula(s: str):
    if not isinstance(s, str) or not s.startswith("="):
        return s
    return str(_parse_chained(s[1:]))


def resolve_params(params: dict) -> dict:
    return {k: _parse_formula(v) if isinstance(v, str) and v.startswith("=") else v for k, v in params.items()}
