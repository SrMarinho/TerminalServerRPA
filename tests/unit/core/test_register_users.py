from src.core.entities.user import User
from src.core.use_cases.register_users_use_case import RegisterUsersUseCase, RegistrationResult


class TestRegistrationResult:
    def test_empty_result(self):
        r = RegistrationResult()
        assert r.success == []
        assert r.errors == []


class TestRegisterUsersUseCase:
    def test_registers_valid_users(self):
        uc = RegisterUsersUseCase()
        users = [
            User("user1", "pass123", "u1@test.com", "User One"),
            User("user2", "pass456", "u2@test.com", "User Two"),
        ]
        result = uc.execute(users)
        assert len(result.success) == 2
        assert result.errors == []

    def test_rejects_invalid_users(self):
        uc = RegisterUsersUseCase()
        users = [User("ab", "123", "bad", "")]
        result = uc.execute(users)
        assert len(result.success) == 0
        assert len(result.errors) == 1
        assert result.errors[0]["user"] == "ab"

    def test_rejects_duplicate_usernames(self):
        uc = RegisterUsersUseCase(existing_usernames={"user1"})
        users = [User("user1", "pass123", "u1@test.com", "User One")]
        result = uc.execute(users)
        assert len(result.success) == 0
        assert "already exists" in result.errors[0]["errors"][0]

    def test_partial_success(self):
        uc = RegisterUsersUseCase()
        users = [
            User("valid", "pass123", "v@test.com", "Valid User"),
            User("x", "123", "bad", ""),
        ]
        result = uc.execute(users)
        assert len(result.success) == 1
        assert len(result.errors) == 1
