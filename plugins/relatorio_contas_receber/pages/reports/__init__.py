from .base_report import BaseReport
from .r703_rot_conciliacao import R703RotConciliacao

REPORTS: list[BaseReport] = [R703RotConciliacao()]
REPORTS_BY_CODE: dict[str, BaseReport] = {r.code: r for r in REPORTS}
