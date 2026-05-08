from src.core.entities.user import User


class TestUserValidation:
    def test_valid_user_returns_no_errors(self):
        u = User(username="johndoe", password="secret123", email="john@test.com", full_name="John Doe")
        assert u.validate() == []

    def test_invalid_username(self):
        u = User(username="ab", password="secret123", email="john@test.com", full_name="John Doe")
        assert "username must be at least 3 characters" in u.validate()

    def test_short_password(self):
        u = User(username="johndoe", password="12345", email="john@test.com", full_name="John Doe")
        assert "password must be at least 6 characters" in u.validate()

    def test_invalid_email(self):
        u = User(username="johndoe", password="secret123", email="notanemail", full_name="John Doe")
        assert "invalid email" in u.validate()

    def test_missing_full_name(self):
        u = User(username="johndoe", password="secret123", email="john@test.com", full_name="")
        assert "full name is required" in u.validate()

    def test_multiple_errors(self):
        u = User(username="a", password="b", email="bad", full_name="")
        errors = u.validate()
        assert len(errors) >= 3
