import os
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse
import http.cookies
import mimetypes
import markdown
import threading
from email.utils import encode_rfc2231

# Global configuration
COOKIE_NAME = "easy_fs_auth_token"
mime_types = [
    ("text/markdown", ".md"),
    ("text/plain", ".tex"),
    ("text/plain", ".py"),
    ("text/plain", ".js")
]
for mime_type, ext in mime_types:
    mimetypes.add_type(mime_type, ext)


class FileServerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, directory=None, password=None, **kwargs):
        self.directory = directory
        self.password = password
        self.authenticated = False
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Check authentication
        if self.password and not self.is_authenticated():
            self.request_auth()
            return

        # Serve files or directory listing
        path = unquote(self.path.strip("/"))
        full_path = os.path.join(self.directory, path)

        if os.path.isdir(full_path):
            self.list_directory(full_path)
        elif os.path.isfile(full_path):
            self.serve_file(full_path)
        else:
            self.send_error(404, "File or directory not found")

    def do_POST(self):
        # Handle password authentication
        if self.path == "/login":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            if f"password={self.password}" in post_data:
                # 设置 Cookie 并发送 302 重定向
                self.send_response(302)
                self.send_header("Set-Cookie",
                                 f"{COOKIE_NAME}={self.password}; Path=/; HttpOnly; Max-Age=3600")  # 1 hour
                self.send_header("Location", "/")
                self.end_headers()
            else:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"Incorrect password")

    def is_authenticated(self):
        if not self.password:
            return True
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            cookies = http.cookies.SimpleCookie(cookie_header)
            if cookies.get(COOKIE_NAME) and cookies[COOKIE_NAME].value == self.password:
                return True
        return False

    def request_auth(self):
        self.send_response(401)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html>
            <head><title>Authentication Required</title></head>
            <body>
                <h1>Authentication Required</h1>
                <form method="POST" action="/login">
                    <label>Password: <input type="password" name="password"></label>
                    <button type="submit">Login</button>
                </form>
            </body>
            </html>
        """)

    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "Directory not found")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")  # 指定字符编码为UTF-8
        self.end_headers()

        # Generate HTML for directory listing
        self.wfile.write(b"<html><head><title>Directory listing</title><meta charset='UTF-8'></head><body>")
        self.wfile.write(b"<h1>Directory listing</h1>")
        self.wfile.write(b"<div>")
        self.wfile.write(b'<button onclick="window.history.back()">Back</button>')
        self.wfile.write(b'<button onclick="window.history.forward()">Forward</button>')
        self.wfile.write(b'<button onclick="window.location.href=\'/\'">Home</button>')
        self.wfile.write(b"</div>")
        self.wfile.write(b"<ul>")
        self.wfile.write(b'<li><a href="../">..</a></li>')  # Parent directory
        for entry in entries:
            full_path = os.path.join(path, entry)
            display_name = entry + "/" if os.path.isdir(full_path) else entry
            link = f"{self.path.rstrip('/')}/{entry}".replace("//", "/")
            # 确保文件名被正确编码为UTF-8
            self.wfile.write(f'<li><a href="{link}">{display_name}</a></li>'.encode('utf-8'))
        self.wfile.write(b"</ul>")
        self.wfile.write(b"</body></html>")

    def serve_file(self, path):
        try:
            # 获取文件的 MIME 类型
            mime_type, _ = mimetypes.guess_type(path)
            is_binary = not (mime_type and mime_type.startswith("text"))

            if is_binary:
                # 以二进制模式读取文件内容
                with open(path, 'rb') as f:
                    content = f.read()
            else:
                # 以文本模式读取文件内容
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

            self.send_response(200)

            # 处理 Markdown 文件
            if path.endswith('.md'):
                self.send_header("Content-Type", "text/html; charset=utf-8")  # 设置 charset=utf-8
                self.end_headers()
                # 将 Markdown 转换为 HTML.
                html_content = self.render_markdown(content).encode('utf-8')  # 确保内容以 UTF-8 编码发送
                self.wfile.write(html_content)
                return

            # 处理其他文件
            if mime_type:
                self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
                filename = os.path.basename(path)
                encoded_filename = encode_rfc2231(filename, 'utf-8')
                if mime_type.startswith("text") or mime_type in ["application/pdf", "image/jpeg", "image/png",
                                                                 "text/markdown", "text/plain"]:
                    self.send_header("Content-Disposition", f'inline; filename*=UTF-8\'\'{encoded_filename}')
                else:
                    self.send_header("Content-Disposition", f'attachment; filename*=UTF-8\'\'{encoded_filename}')
            else:
                self.send_header("Content-Type", "application/octet-stream")
                filename = os.path.basename(path)
                encoded_filename = encode_rfc2231(filename, 'utf-8')
                self.send_header("Content-Disposition", f'attachment; filename*=UTF-8\'\'{encoded_filename}')

            self.end_headers()

            if is_binary:
                # 如果是二进制文件，直接写入字节内容
                self.wfile.write(content)
            else:
                # 如果是文本文件，确保内容以 UTF-8 编码发送
                self.wfile.write(content.encode('utf-8'))

        except OSError:
            self.send_error(404, "File not found")

    @staticmethod
    def render_markdown(markdown_content):
        # 使用 markdown 库将 Markdown 转换为 HTML
        html_content = markdown.markdown(markdown_content)
        # 包装成完整的 HTML 文档
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>Markdown Viewer</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
                pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


def run_server(directory, port, password):
    def handler(*args, **kwargs):
        FileServerHandler(*args, directory=directory, password=password, **kwargs)

    httpd = ThreadedHTTPServer(("", port), handler)
    print(f"Serving files from {directory} on port {port}")
    if password:
        print(f"Password protection enabled. Password: {password}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer is shutting down...")
    finally:
        httpd.shutdown()
        httpd.server_close()
        print("Server closed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Python File Server with Authentication")
    parser.add_argument("-d", "--dir", required=True, help="Directory to serve files from")
    parser.add_argument("-p", "--port", type=int, default=80, help="Port to serve on")
    parser.add_argument("-pw", "--password", help="Password for authentication (optional)")
    args = parser.parse_args()

    run_server(args.dir, args.port, args.password)
