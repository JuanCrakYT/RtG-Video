"""Regression tests for the browser preview HTTP server."""

import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

# Running python tests/test_preview_server.py puts tests/ rather than the
# repository root on sys.path. Add the root so the src package resolves.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.preview.server import PreviewServer


class PreviewServerTests(unittest.TestCase):
    def setUp(self):
        self.server = PreviewServer()
        self.base_url = f"http://127.0.0.1:{self.server.httpd.server_port}"

    def tearDown(self):
        self.server.close()

    def test_serves_plyr_modules_with_javascript_mime_type(self):
        for path in ("/plyr/plyr.js", "/plyr/config/defaults"):
            with self.subTest(path=path), urlopen(self.base_url + path, timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("javascript", response.headers.get_content_type())

    def test_video_endpoint_supports_byte_ranges(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as file:
            file.write(b"0123456789")
            video_path = Path(file.name)

        try:
            token = self.server.register_video(video_path)
            request = Request(
                f"{self.base_url}/video/{token}",
                headers={"Range": "bytes=2-5"},
            )
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), b"2345")
                self.assertEqual(response.headers.get("Content-Range"), "bytes 2-5/10")
        finally:
            if "token" in locals():
                self.server.release_video(token)
            video_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
