from src.automation.pages.contas_receber.reports.base_report import BaseReport
from src.automation.pages.contas_receber.reports.rot_conciliacao_703 import RotConciliacao703

REPORTS: list[BaseReport] = [RotConciliacao703()]
REPORTS_BY_CODE: dict[str, BaseReport] = {r.code: r for r in REPORTS}
