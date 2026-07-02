#!/usr/bin/env python3
"""
Gallery Editor — drag-and-drop reordering for the homepage gallery.
Run:  python3 gallery-editor.py
Open: http://localhost:8083
"""

import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(SITE_DIR, 'index.html')
PORT = 8083

ITEM_RE = re.compile(
    r'<a href="([^"]+)" class="gallery-item">\s*'
    r'<img src="([^"]+)" alt="([^"]+)"[^>]*>\s*'
    r'<span class="gallery-item-label">([^<]+)</span>\s*'
    r'</a>',
    re.DOTALL,
)

GALLERY_RE = re.compile(r'<div class="gallery">.*?</div>', re.DOTALL)

MIME = {
    'html': 'text/html; charset=utf-8',
    'jpg':  'image/jpeg',
    'jpeg': 'image/jpeg',
    'png':  'image/png',
    'gif':  'image/gif',
    'webp': 'image/webp',
}


def read_index():
    with open(INDEX_PATH, encoding='utf-8') as f:
        return f.read()


def parse_items(html):
    return [
        {'href': m.group(1), 'src': m.group(2), 'alt': m.group(3), 'label': m.group(4)}
        for m in ITEM_RE.finditer(html)
    ]


def build_gallery(items):
    rows = ['<div class="gallery">']
    for item in items:
        rows.append(
            f'\n      <a href="{item["href"]}" class="gallery-item">\n'
            f'        <img src="{item["src"]}" alt="{item["alt"]}" loading="lazy">\n'
            f'        <span class="gallery-item-label">{item["label"]}</span>\n'
            f'      </a>'
        )
    rows.append('\n\n    </div>')
    return ''.join(rows)


def save_items(items):
    html = read_index()
    html = GALLERY_RE.sub(build_gallery(items), html, count=1)
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(html)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._file('gallery-editor.html', 'text/html; charset=utf-8')
        elif self.path == '/api/gallery':
            self._json(parse_items(read_index()))
        elif self.path.startswith('/images/'):
            self._static(os.path.join(SITE_DIR, self.path.lstrip('/')))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/gallery':
            length = int(self.headers.get('Content-Length', 0))
            try:
                save_items(json.loads(self.rfile.read(length)))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
            except Exception as e:
                self.send_error(500, str(e))

    def _file(self, name, content_type):
        path = os.path.join(SITE_DIR, name)
        with open(path, 'rb') as f:
            data = f.read()
        self._respond(200, content_type, data)

    def _static(self, filepath):
        if not os.path.exists(filepath):
            self.send_error(404)
            return
        ext = filepath.rsplit('.', 1)[-1].lower()
        with open(filepath, 'rb') as f:
            data = f.read()
        self._respond(200, MIME.get(ext, 'application/octet-stream'), data)

    def _json(self, data):
        self._respond(200, 'application/json', json.dumps(data).encode())

    def _respond(self, code, content_type, data):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    os.chdir(SITE_DIR)
    print(f'Gallery editor → http://localhost:{PORT}')
    HTTPServer(('localhost', PORT), Handler).serve_forever()
