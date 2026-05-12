# Explicit imports for PyInstaller compatibility
# Each task module must be imported here to be bundled in the .exe
from src.automation.tasks.bulk_user_registration_task import BulkUserRegistrationTask  # noqa: F401
from src.automation.tasks.exemplo_task import ExemploTask  # noqa: F401
from src.automation.tasks.report_generation import GeracaoRelatorio  # noqa: F401
