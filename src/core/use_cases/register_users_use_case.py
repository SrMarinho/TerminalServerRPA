from dataclasses import dataclass, field

from src.core.entities.user import User


@dataclass
class RegistrationResult:
    success: list[User] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


class RegisterUsersUseCase:
    def __init__(self, existing_usernames: set[str] | None = None):
        self._existing = existing_usernames or set()

    def execute(self, users: list[User]) -> RegistrationResult:
        result = RegistrationResult()
        for user in users:
            validation_errors = user.validate()
            if validation_errors:
                result.errors.append({"user": user.username, "errors": validation_errors})
                continue
            if user.username in self._existing:
                result.errors.append({"user": user.username, "errors": ["username already exists"]})
                continue
            result.success.append(user)
            self._existing.add(user.username)
        return result
