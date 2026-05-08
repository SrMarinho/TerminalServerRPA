from dataclasses import dataclass, field


@dataclass
class User:
    username: str
    password: str
    email: str
    full_name: str
    roles: list[str] = field(default_factory=list)
    active: bool = True

    def validate(self) -> list[str]:
        errors = []
        if not self.username or len(self.username) < 3:
            errors.append("username must be at least 3 characters")
        if not self.password or len(self.password) < 6:
            errors.append("password must be at least 6 characters")
        if not self.email or "@" not in self.email:
            errors.append("invalid email")
        if not self.full_name:
            errors.append("full name is required")
        return errors
