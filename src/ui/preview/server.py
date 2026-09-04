"""Serve the production browser Preview and one selected local video securely."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import token_urlsafe
from threading import Thread
from urllib.parse import unquote, urlparse
from json import dumps, loads
from urllib.request import Request, urlopen
import mimetypes
try:
    import cv2
except ImportError:  # pragma: no cover - optional metadata enhancement
    cv2 = None


class PreviewServer:
    def __init__(self):
        self.root = Path(__file__).resolve().parent
        self.videos = {}
        self.video_metadata = {}
        self.events = {}
        owner = self

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(owner.root), **kwargs)

            def do_GET(self):
                path = unquote(urlparse(self.path).path)
                if path.startswith("/video/"):
                    token = path.removeprefix("/video/")
                    video = owner.videos.get(token)
                    if video is None or not video.is_file():
                        self.send_error(404)
                        return
                    self.path = "/video-file"
                    self._video_path = video
                    self._send_video(video)
                    return
                super().do_GET()

            def do_POST(self):
                path = unquote(urlparse(self.path).path)
                if path.startswith("/event/"):
                    token = path.removeprefix("/event/")
                    length = int(self.headers.get("Content-Length", "0"))
                    try:
                        event = loads(self.rfile.read(length).decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        self.send_error(400)
                        return
                    owner.events[token] = event
                    self.send_response(204)
                    self.end_headers()
                    return
                if path.startswith("/release/"):
                    owner.videos.pop(path.removeprefix("/release/"), None)
                    self.send_response(204)
                    self.end_headers()
                    return
                self.send_error(404)

            def _send_video(self, video):
                total_size = video.stat().st_size
                range_header = self.headers.get("Range")
                start = 0
                end = total_size - 1
                if range_header and range_header.startswith("bytes="):
                    requested = range_header[6:].split(",", 1)[0].split("-", 1)
                    start = int(requested[0] or 0)
                    end = int(requested[1]) if len(requested) > 1 and requested[1] else end
                    if start >= total_size or start > end:
                        self.send_error(416)
                        return
                    end = min(end, total_size - 1)
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{total_size}")
                else:
                    self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(video.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(end - start + 1))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                try:
                    with video.open("rb") as source:
                        source.seek(start)
                        remaining = end - start + 1
                        while remaining:
                            chunk = source.read(min(1024 * 1024, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                except (ConnectionResetError, BrokenPipeError):
                    # Chromium may cancel a media range request during close/reopen.
                    pass

            def log_message(self, *_args):
                return

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def register_video(self, path):
        video = Path(path).resolve()
        if not video.is_file():
            raise FileNotFoundError(video)
        token = token_urlsafe(24)
        self.videos[token] = video
        fps = 0
        frame_count = 0
        if cv2 is not None:
            capture = cv2.VideoCapture(str(video))
            fps = capture.get(cv2.CAP_PROP_FPS) if capture.isOpened() else 0
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) if capture.isOpened() else 0
            capture.release()
        self.video_metadata[token] = {
            "name": video.name,
            "fps": fps if fps > 0 else "",
            "frame_count": frame_count if frame_count > 0 else "",
        }
        return token

    def url(self, token, width, height, palette):
        from urllib.parse import quote
        metadata = self.video_metadata.get(token, {})
        query = f"video=/video/{quote(token)}&name={quote(metadata.get('name', 'video'))}&fps={metadata.get('fps', '')}&frame_count={metadata.get('frame_count', '')}&width={int(width)}&height={int(height)}&palette={quote(dumps(palette, separators=(',', ':')))}"
        return f"http://127.0.0.1:{self.httpd.server_port}/preview.html?{query}"

    def send_event(self, token, event):
        """Send a lifecycle event to the local Preview server."""
        request = Request(
            f"http://127.0.0.1:{self.httpd.server_port}/event/{token}",
            data=dumps(event).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=1):
                pass
        except OSError:
            # The Preview may already have closed its server connection.
            pass

    def close(self):
        self.videos.clear()
        self.video_metadata.clear()
        self.events.clear()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
