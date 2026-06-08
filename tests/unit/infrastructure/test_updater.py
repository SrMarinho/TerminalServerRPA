from unittest.mock import MagicMock, patch


class TestCheckForUpdate:
    def test_returns_release_when_newer(self):
        from src.infrastructure.updater import check_for_update

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"tag_name": "v2.0.0", "html_url": "https://...", "assets": []}
        with patch("httpx.get", return_value=mock_resp):
            release = check_for_update("1.0.0")
            assert release is not None
            assert release.version == "2.0.0"

    def test_returns_none_when_same_version(self):
        from src.infrastructure.updater import check_for_update

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"tag_name": "v1.0.0", "html_url": "https://...", "assets": []}
        with patch("httpx.get", return_value=mock_resp):
            release = check_for_update("1.0.0")
            assert release is None

    def test_returns_none_on_http_error(self):
        from src.infrastructure.updater import check_for_update

        with patch("httpx.get", side_effect=Exception("network error")):
            release = check_for_update("1.0.0")
            assert release is None


class TestDownloadAsset:
    def test_downloads_file(self, tmp_path):
        from src.infrastructure.updater import _download_asset

        dest = tmp_path / "test.exe"
        asset = {"url": "https://api.github.com/.../assets/1", "name": "test.exe"}
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.iter_bytes.return_value = [b"hello", b"world"]
        with patch("httpx.stream", return_value=mock_resp):
            result = _download_asset(asset, dest)
            assert result == dest
            assert dest.read_bytes() == b"helloworld"

    def test_returns_none_on_failure(self, tmp_path):
        from src.infrastructure.updater import _download_asset

        asset = {"url": "https://api.github.com/.../assets/1", "name": "test.exe"}
        with patch("httpx.stream", side_effect=Exception("download failed")):
            result = _download_asset(asset, tmp_path / "test.exe")
            assert result is None

    def test_raises_on_http_error(self, tmp_path):
        from src.infrastructure.updater import _download_asset

        asset = {"url": "https://api.github.com/.../assets/1", "name": "test.exe"}
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.raise_for_status.side_effect = Exception("HTTP 404")
        with patch("httpx.stream", return_value=mock_resp):
            result = _download_asset(asset, tmp_path / "test.exe")
            assert result is None
