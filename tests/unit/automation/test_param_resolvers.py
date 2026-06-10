from datetime import date

import pytest

import src.automation.param_resolvers as pr
from src.automation.param_resolvers import (
    DateRange,
    _coerce,
    _split_args,
    _subtract_months,
    resolve_params,
    resolver_meta,
)

_FROZEN = date(2024, 3, 15)  # a fixed "today" for deterministic resolver tests


@pytest.fixture
def frozen_today(monkeypatch):
    class _FrozenDate(date):
        @classmethod
        def today(cls):
            return _FROZEN

    monkeypatch.setattr(pr, "date", _FrozenDate)
    return _FROZEN


class TestDateRange:
    def test_first_last_format(self):
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 31))
        assert dr.first() == "01/01/2024"
        assert dr.last() == "31/01/2024"

    def test_str_is_range(self):
        dr = DateRange(date(2024, 1, 1), date(2024, 1, 31))
        assert str(dr) == "01/01/2024-31/01/2024"
        assert repr(dr) == str(dr)


class TestSubtractMonths:
    def test_simple(self):
        assert _subtract_months(date(2024, 6, 15), 1) == date(2024, 5, 15)

    def test_crosses_year_boundary(self):
        assert _subtract_months(date(2024, 1, 10), 3) == date(2023, 10, 10)

    def test_clamps_day_to_shorter_month(self):
        # Mar 31 minus 1 month → Feb, clamp to 29 (2024 is a leap year)
        assert _subtract_months(date(2024, 3, 31), 1) == date(2024, 2, 29)

    def test_clamps_to_non_leap_february(self):
        assert _subtract_months(date(2023, 3, 31), 1) == date(2023, 2, 28)

    def test_zero_months_noop(self):
        assert _subtract_months(date(2024, 6, 15), 0) == date(2024, 6, 15)


class TestSplitArgs:
    def test_top_level_commas(self):
        assert _split_args("a, b, c") == ["a", "b", "c"]

    def test_respects_nested_parens(self):
        assert _split_args("date.back(30), '-', date.today()") == ["date.back(30)", "'-'", "date.today()"]

    def test_empty(self):
        assert _split_args("") == []


class TestCoerce:
    def test_number_valid(self):
        assert _coerce("42", "number") == 42

    def test_number_invalid_defaults_zero(self):
        assert _coerce("abc", "number") == 0

    def test_string_passthrough(self):
        assert _coerce(123, "string") == "123"


class TestResolversFrozen:
    def test_today(self, frozen_today):
        assert resolve_params({"d": "=date.today()"})["d"] == "15/03/2024"

    def test_yesterday(self, frozen_today):
        assert resolve_params({"d": "=date.yesterday()"})["d"] == "14/03/2024"

    def test_back_days(self, frozen_today):
        assert resolve_params({"d": "=date.back(days=10)"})["d"] == "05/03/2024"

    def test_back_months(self, frozen_today):
        assert resolve_params({"d": "=date.back(months=1)"})["d"] == "15/02/2024"

    def test_back_positional(self, frozen_today):
        # first positional param is 'days'
        assert resolve_params({"d": "=date.back(5)"})["d"] == "10/03/2024"

    def test_month_range_chaining(self, frozen_today):
        assert resolve_params({"d": "=date.month().first()"})["d"] == "01/03/2024"
        assert resolve_params({"d": "=date.month().last()"})["d"] == "31/03/2024"

    def test_last_month_range(self, frozen_today):
        assert resolve_params({"d": "=date.last_month().first()"})["d"] == "01/02/2024"
        assert resolve_params({"d": "=date.last_month().last()"})["d"] == "29/02/2024"


class TestFormulaParsing:
    def test_concat(self, frozen_today):
        out = resolve_params({"d": "=concat(date.back(days=10), '-', date.today())"})["d"]
        assert out == "05/03/2024-15/03/2024"

    def test_non_formula_passthrough(self):
        assert resolve_params({"a": "plain", "b": 5, "c": "=date.today()"})["a"] == "plain"

    def test_non_string_untouched(self):
        params = {"n": 42, "flag": True}
        assert resolve_params(params) == {"n": 42, "flag": True}

    def test_unknown_resolver_returns_literal(self):
        # ns.fn not in registry → expression returned as-is (stringified)
        assert resolve_params({"d": "=date.nope()"})["d"] == "date.nope()"

    def test_string_literal_with_quotes(self, frozen_today):
        assert resolve_params({"d": "=concat('x')"})["d"] == "x"

    def test_chaining_on_non_range_breaks_gracefully(self, frozen_today):
        # .first() on a plain string result → method missing → chain breaks, base kept
        out = resolve_params({"d": "=date.today().first()"})["d"]
        assert out == "15/03/2024"


class TestResolverMeta:
    def test_strips_fn(self):
        meta = resolver_meta()
        for fns in meta["date"].values():
            assert "fn" not in fns

    def test_includes_functions_namespace(self):
        meta = resolver_meta()
        assert "__fn__" in meta
        assert "concat" in meta["__fn__"]

    def test_preserves_labels_and_params(self):
        meta = resolver_meta()
        assert meta["date"]["back"]["label"] == "N dias/meses atrás"
        assert any(p["name"] == "days" for p in meta["date"]["back"]["params"])
