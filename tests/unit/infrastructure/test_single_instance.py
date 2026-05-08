from unittest.mock import MagicMock, patch


class TestIsFirstInstance:
    def test_returns_true_when_mutex_created(self):
        from src.infrastructure.single_instance import is_first_instance
        with (
            patch("ctypes.windll.kernel32.CreateMutexW", return_value=MagicMock()),
            patch("ctypes.GetLastError", return_value=0),
        ):
            assert is_first_instance() is True

    def test_returns_false_when_mutex_exists(self):
        from src.infrastructure.single_instance import is_first_instance
        with (
            patch("ctypes.windll.kernel32.CreateMutexW", return_value=MagicMock()),
            patch("ctypes.GetLastError", return_value=0xDE),
        ):
            assert is_first_instance() is False


class TestSaveReadPort:
    def test_roundtrip(self, tmp_path):
        from src.infrastructure.single_instance import read_port, save_port
        with patch("src.infrastructure.single_instance._get_port_path", return_value=tmp_path / "port.txt"):
            save_port(8080)
            assert read_port() == 8080

    def test_read_returns_none_when_missing(self, tmp_path):
        from src.infrastructure.single_instance import read_port
        with patch("src.infrastructure.single_instance._get_port_path", return_value=tmp_path / "port.txt"):
            assert read_port() is None


class TestFocusExisting:
    def test_returns_true_on_success(self):
        from src.infrastructure.single_instance import focus_existing_instance
        with (
            patch("src.infrastructure.single_instance.read_port", return_value=8080),
            patch("socket.create_connection") as mock_conn,
        ):
            mock_conn.return_value.__enter__.return_value = MagicMock()
            assert focus_existing_instance() is True

    def test_returns_false_when_no_port(self):
        from src.infrastructure.single_instance import focus_existing_instance
        with patch("src.infrastructure.single_instance.read_port", return_value=None):
            assert focus_existing_instance() is False

    def test_returns_false_on_connection_error(self):
        from src.infrastructure.single_instance import focus_existing_instance
        with (
            patch("src.infrastructure.single_instance.read_port", return_value=8080),
            patch("socket.create_connection", side_effect=ConnectionRefusedError),
        ):
            assert focus_existing_instance() is False
