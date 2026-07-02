#!/usr/bin/env python3
"""Caption editor for Marjan's website. Run: python3 caption-editor.py → http://localhost:8084"""

import http.server
import urllib.parse
import json
import os
import re

WEBSITE_DIR = os.path.expanduser('~/HQ/comms/website')
PROJECTS_DIR = os.path.join(os.path.expanduser('~/HQ/comms/website'), 'projects')
PORT = 8084


def get_projects():
    files = sorted(f[:-5] for f in os.listdir(PROJECTS_DIR) if f.endswith('.html'))
    return files


def parse_project(slug):
    path = os.path.join(PROJECTS_DIR, slug + '.html')
    with open(path, encoding='utf-8') as f:
        content = f.read()

    grid_match = re.search(r'<div class="image-grid">(.*?)</div>', content, re.DOTALL)
    if not grid_match:
        return []

    grid_html = grid_match.group(1)
    images = []
    for m in re.finditer(r'<img\s+([^>]*)>', grid_html):
        attrs = m.group(1)
        src = re.search(r'src="([^"]*)"', attrs)
        alt = re.search(r'alt="([^"]*)"', attrs)
        caption = re.search(r'data-caption="([^"]*)"', attrs)
        if src:
            images.append({
                'src': src.group(1),
                'alt': alt.group(1) if alt else '',
                'caption': (caption.group(1) if caption else '').replace('&quot;', '"'),
            })
    return images


def save_captions(slug, updates):
    path = os.path.join(PROJECTS_DIR, slug + '.html')
    with open(path, encoding='utf-8') as f:
        content = f.read()

    for update in updates:
        src = update['src']
        caption = update['caption'].strip()
        escaped_src = re.escape(src)

        def replace_img(m):
            tag = m.group(0)
            tag = re.sub(r'\s*data-caption="[^"]*"', '', tag)
            if caption:
                safe = caption.replace('"', '&quot;')
                tag = tag[:-1] + f' data-caption="{safe}">'
            return tag

        content = re.sub(r'<img\s[^>]*src="' + escaped_src + r'"[^>]*>', replace_img, content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


ADMIN_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Caption Editor</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f4f4f4; color: #222; }
    .layout { display: flex; height: 100vh; }

    .sidebar { width: 210px; background: #fff; border-right: 1px solid #ddd; padding: 20px 12px; overflow-y: auto; flex-shrink: 0; }
    .sidebar h2 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #999; margin-bottom: 10px; padding: 0 8px; }
    .sidebar button {
      display: block; width: 100%; text-align: left; background: none; border: none;
      padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; color: #444;
      margin-bottom: 2px; line-height: 1.3;
    }
    .sidebar button:hover { background: #f0f0f0; }
    .sidebar button.active { background: #222; color: #fff; }

    .main { flex: 1; padding: 28px 32px; overflow-y: auto; }
    .main-title { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
    .empty-state { color: #999; font-style: italic; margin-top: 40px; }

    .image-row {
      display: flex; align-items: center; gap: 14px;
      background: #fff; padding: 12px; border-radius: 8px;
      border: 1px solid #e2e2e2; margin-bottom: 10px;
    }
    .image-row img { width: 110px; height: 72px; object-fit: cover; border-radius: 4px; flex-shrink: 0; background: #eee; }
    .image-row img.missing { display: flex; align-items: center; justify-content: center; font-size: 11px; color: #aaa; }
    .image-info { flex: 1; }
    .filename { font-size: 11px; color: #aaa; margin-bottom: 5px; }
    .image-info input {
      width: 100%; padding: 8px 10px; border: 1px solid #ccc;
      border-radius: 6px; font-size: 13px; color: #222;
    }
    .image-info input:focus { outline: none; border-color: #555; }
    .image-info input::placeholder { color: #bbb; }

    .save-bar {
      position: sticky; bottom: 0; background: #f4f4f4;
      padding: 16px 0 4px; display: flex; align-items: center; gap: 12px;
    }
    .save-btn {
      background: #222; color: #fff; border: none;
      padding: 11px 26px; border-radius: 7px; font-size: 14px;
      cursor: pointer; font-weight: 500;
    }
    .save-btn:hover { background: #000; }
    .save-btn:disabled { background: #aaa; cursor: default; }
    .toast {
      display: none; padding: 9px 14px; border-radius: 6px;
      font-size: 13px; font-weight: 500;
    }
    .toast.ok { display: inline; background: #d4edda; color: #155724; }
    .toast.error { display: inline; background: #f8d7da; color: #721c24; }
  </style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <h2>Projects</h2>
    <div id="project-list"></div>
  </aside>
  <main class="main" id="main">
    <p class="empty-state">← Pick a project to edit captions</p>
  </main>
</div>
<script>
let currentProject = null;

async function loadProjects() {
  const res = await fetch('/api/projects');
  const projects = await res.json();
  const list = document.getElementById('project-list');
  projects.forEach(slug => {
    const btn = document.createElement('button');
    btn.textContent = slug.replace(/-/g, ' ');
    btn.dataset.slug = slug;
    btn.onclick = () => selectProject(slug);
    list.appendChild(btn);
  });
}

async function selectProject(slug) {
  currentProject = slug;
  document.querySelectorAll('.sidebar button').forEach(b =>
    b.classList.toggle('active', b.dataset.slug === slug)
  );

  const main = document.getElementById('main');
  main.innerHTML = '<p class="empty-state">Loading…</p>';

  const res = await fetch('/api/project/' + slug);
  const images = await res.json();

  if (!images.length) {
    main.innerHTML = '<p class="empty-state">No images found in this project.</p>';
    return;
  }

  const title = slug.replace(/-/g, ' ');
  let html = '<div class="main-title">' + title + '</div>';

  images.forEach((img, i) => {
    const parts = img.src.split('/');
    const filename = parts[parts.length - 1];
    const staticSrc = '/static/' + img.src.replace('../', '');
    const escaped = img.caption.replace(/"/g, '&quot;');
    html += `
      <div class="image-row">
        <img src="${staticSrc}" alt="${img.alt}">
        <div class="image-info">
          <div class="filename">${filename}</div>
          <input type="text" data-src="${img.src}" value="${escaped}" placeholder="Paste caption here…">
        </div>
      </div>`;
  });

  html += `
    <div class="save-bar">
      <button class="save-btn" onclick="saveCaptions()">Save captions</button>
      <span class="toast" id="toast"></span>
    </div>`;

  main.innerHTML = html;
}

async function saveCaptions() {
  const btn = document.querySelector('.save-btn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  const inputs = document.querySelectorAll('.image-info input');
  const updates = Array.from(inputs).map(input => ({
    src: input.dataset.src,
    caption: input.value
  }));

  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project: currentProject, updates })
  });

  const toast = document.getElementById('toast');
  if (res.ok) {
    toast.className = 'toast ok';
    toast.textContent = 'Saved!';
  } else {
    toast.className = 'toast error';
    toast.textContent = 'Error saving — check the terminal';
  }
  setTimeout(() => { toast.className = 'toast'; }, 3000);

  btn.disabled = false;
  btn.textContent = 'Save captions';
}

loadProjects();
</script>
</body>
</html>
'''


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, rel_path):
        full_path = os.path.join(os.path.expanduser('~/HQ/comms/website'), rel_path)
        if not os.path.isfile(full_path):
            self.send_response(404)
            self.end_headers()
            return
        ext = os.path.splitext(full_path)[1].lower()
        types = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'
        }
        content_type = types.get(ext, 'application/octet-stream')
        with open(full_path, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ('/', '/admin'):
            self.send_html(ADMIN_HTML)
        elif path == '/api/projects':
            self.send_json(get_projects())
        elif path.startswith('/api/project/'):
            slug = path[len('/api/project/'):]
            try:
                self.send_json(parse_project(slug))
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
        elif path.startswith('/static/'):
            rel = urllib.parse.unquote(path[len('/static/'):])
            self.serve_file(rel)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/save':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            try:
                save_captions(body['project'], body['updates'])
                self.send_json({'ok': True})
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    print(f'Caption editor → http://localhost:{PORT}')
    server = http.server.HTTPServer(('', PORT), Handler)
    server.serve_forever()
