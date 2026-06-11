"""
CodeGrapher — Backend (Modularized)
Routes and Application Setup
"""
from flask import (Flask, request, jsonify, send_from_directory,
                   session, Response, make_response)
from flask_cors import CORS
import os, zipfile, tempfile, json, hashlib, uuid, re
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Import our new modules!
from llm import ollama_chat, ollama_health, build_compact_context, OLLAMA_MODEL
from analysis import (analyze_python_file, analyze_java_file, build_graph, 
                      generate_risk_report, generate_markdown_doc)

# ──────────────────────────────────────────────────────
#  APP SETUP
# ──────────────────────────────────────────────────────
app = Flask(__name__,
    static_folder='../frontend/static',
    template_folder='../frontend/templates')

app.secret_key = os.environ.get("SECRET_KEY", "cg-" + hashlib.sha256(b"codegrapher").hexdigest()[:24])
app.config.update(
    SESSION_COOKIE_HTTPONLY = True,
    SESSION_COOKIE_SAMESITE = 'Lax',
    SESSION_COOKIE_SECURE   = False,
    PERMANENT_SESSION_LIFETIME = timedelta(days=30),
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024,
)

CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

ALLOWED_EXTENSIONS = {'.py', '.java', '.zip'}
MAX_FILES_IN_ZIP   = 200

# ──────────────────────────────────────────────────────
#  FILE-BASED DB
# ──────────────────────────────────────────────────────
DATA_DIR      = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE    = DATA_DIR / 'users.json'
SESSIONS_FILE = DATA_DIR / 'sessions.json'

def _load(path):
    if path.exists():
        try: return json.loads(path.read_text('utf-8'))
        except: pass
    return {}

def _save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), 'utf-8')
    tmp.replace(path)

get_users    = lambda: _load(USERS_FILE)
save_users   = lambda u: _save(USERS_FILE, u)
get_sess_db  = lambda: _load(SESSIONS_FILE)
save_sess_db = lambda s: _save(SESSIONS_FILE, s)

def hash_pw(pw: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', pw.encode(), b'cg-salt', 200_000).hex()

def sanitize(s, maxlen=200):
    return s.strip()[:maxlen] if isinstance(s, str) else ''

def uid_from_session():
    return session.get('uid')

def auth_error():
    if not uid_from_session():
        return make_response(jsonify({'error': 'Authentication required'}), 401)
    return None

# ──────────────────────────────────────────────────────
#  AUTH ROUTES
# ──────────────────────────────────────────────────────
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    d     = request.get_json(silent=True) or {}
    name  = sanitize(d.get('name',''), 80)
    email = sanitize(d.get('email',''), 120).lower()
    pw    = d.get('password','')
    if not name or not email or not pw: return jsonify({'error': 'All fields required'}), 400
    if len(pw) < 6: return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email): return jsonify({'error': 'Invalid email address'}), 400
    users = get_users()
    if email in users: return jsonify({'error': 'Email already registered'}), 409
    uid = str(uuid.uuid4())
    users[email] = {
        'uid': uid, 'name': name, 'email': email,
        'pw': hash_pw(pw), 'created': datetime.now(timezone.utc).isoformat()
    }
    save_users(users)
    session.permanent = True
    session.update({'uid': uid, 'email': email, 'name': name})
    return jsonify({'ok': True, 'user': {'uid': uid, 'name': name, 'email': email}})

@app.route('/api/auth/login', methods=['POST'])
def login():
    d     = request.get_json(silent=True) or {}
    email = sanitize(d.get('email',''), 120).lower()
    pw    = d.get('password','')
    users = get_users()
    user  = users.get(email)
    if not user or user['pw'] != hash_pw(pw): return jsonify({'error': 'Invalid email or password'}), 401
    session.permanent = True
    session.update({'uid': user['uid'], 'email': email, 'name': user['name']})
    return jsonify({'ok': True, 'user': {'uid': user['uid'], 'name': user['name'], 'email': email}})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/auth/me')
def me():
    uid = uid_from_session()
    return jsonify({'user': {'uid': uid, 'name': session.get('name'), 'email': session.get('email')} if uid else None})

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    d     = request.get_json(silent=True) or {}
    email = sanitize(d.get('email',''), 120).lower()
    pw    = d.get('new_password','')
    if not email or not pw: return jsonify({'error': 'Email and new password required'}), 400
    if len(pw) < 6: return jsonify({'error': 'Password must be at least 6 characters'}), 400
    users = get_users()
    if email not in users: return jsonify({'ok': True, 'message': 'If that email is registered, the password has been updated.'})
    users[email]['pw'] = hash_pw(pw)
    save_users(users)
    return jsonify({'ok': True, 'message': 'Password updated. You can now sign in.'})

# ──────────────────────────────────────────────────────
#  SESSION PERSISTENCE
# ──────────────────────────────────────────────────────
@app.route('/api/sessions')
def list_sessions():
    if err := auth_error(): return err
    uid  = uid_from_session()
    db   = get_sess_db()
    rows = [s for s in db.values() if s.get('uid') == uid]
    rows.sort(key=lambda x: x.get('updated',''), reverse=True)
    return jsonify({'sessions': [{k: v for k, v in s.items() if k != 'graphData'} for s in rows]})

@app.route('/api/sessions/<sid>', methods=['GET'])
def get_session(sid):
    if err := auth_error(): return err
    db = get_sess_db()
    s  = db.get(sid)
    if not s or s.get('uid') != uid_from_session(): return jsonify({'error': 'Not found'}), 404
    return jsonify({'session': s})

@app.route('/api/sessions/<sid>', methods=['PUT'])
def upsert_session(sid):
    if err := auth_error(): return err
    uid  = uid_from_session()
    db   = get_sess_db()
    data = request.get_json(silent=True) or {}
    s    = db.get(sid, {'sid': sid, 'uid': uid, 'created': datetime.now(timezone.utc).isoformat()})
    if s.get('uid') != uid: return jsonify({'error': 'Forbidden'}), 403
    for k, v in data.items():
        if k not in {'uid', 'sid', 'created'}: s[k] = v
    s['updated'] = datetime.now(timezone.utc).isoformat()
    db[sid] = s
    save_sess_db(db)
    return jsonify({'ok': True})

@app.route('/api/sessions/<sid>', methods=['DELETE'])
def delete_session(sid):
    if err := auth_error(): return err
    uid = uid_from_session()
    db  = get_sess_db()
    if (s := db.get(sid)) and s.get('uid') == uid:
        del db[sid]
        save_sess_db(db)
    return jsonify({'ok': True})

# ──────────────────────────────────────────────────────
#  ANALYZE ROUTE
# ──────────────────────────────────────────────────────
@app.route('/api/analyze', methods=['POST'])
def analyze():
    if err := auth_error(): return err
    if 'file' not in request.files: return jsonify({'error': 'No file uploaded'}), 400

    uploaded = request.files['file']
    filename = uploaded.filename or ''
    if not any(filename.lower().endswith(e) for e in ALLOWED_EXTENSIONS):
        return jsonify({'error': 'Only .py, .java, and .zip files allowed'}), 400

    tmp_dir    = tempfile.mkdtemp()
    saved_path = os.path.join(tmp_dir, filename)
    uploaded.save(saved_path)

    all_files_data, language, errors = {}, None, []
    files_processed = 0

    def process(filepath, rel_name):
        nonlocal language, files_processed
        if files_processed >= MAX_FILES_IN_ZIP: return
        ext = Path(rel_name).suffix.lower()
        if ext == '.py':    fn, lang = analyze_python_file, 'python'
        elif ext == '.java': fn, lang = analyze_java_file,   'java'
        else: return
        if language is None: language = lang
        data, e = fn(filepath, rel_name)
        if e: errors.append(f"{rel_name}: {e}")
        if data: all_files_data[rel_name] = data
        files_processed += 1

    if filename.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(saved_path, 'r') as z:
                for zi in z.infolist():
                    if '..' in zi.filename or zi.filename.startswith('/'): return jsonify({'error': 'Unsafe zip'}), 400
                z.extractall(tmp_dir)
        except zipfile.BadZipFile:
            return jsonify({'error': 'Invalid zip file'}), 400
        for root, dirs, files in os.walk(tmp_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__','node_modules')]
            for f in files:
                full = os.path.join(root, f)
                rel  = os.path.relpath(full, tmp_dir)
                if rel != filename: process(full, rel)
    else:
        process(saved_path, filename)

    if not all_files_data: return jsonify({'error': f'No analyzable files. {"; ".join(errors)}'}), 400

    graph    = build_graph(all_files_data, language)
    summary  = {
        'language':          language,
        'files':             list(all_files_data.keys()),
        'total_files':       len(all_files_data),
        'total_functions':   sum(len(fd['functions']) for fd in all_files_data.values()),
        'total_classes':     sum(len(fd['classes'])   for fd in all_files_data.values()),
        'total_call_edges':  len([e for e in graph['edges'] if e['type'] == 'calls']),
        'errors':            errors,
    }
    risk    = generate_risk_report(all_files_data, graph, language)
    md_doc  = generate_markdown_doc(all_files_data, graph, risk, summary, language)

    compact_files = {}
    for k, v in all_files_data.items():
        compact_files[k] = {
            'classes': v['classes'],
            'imports': v['imports'],
            'loc_total': v.get('loc_total', 0),
            'source': v.get('source', ''),
            'functions': {
                fk: {
                    'name': fd['name'], 'args': fd.get('args', []), 'calls': fd.get('calls', []),
                    'class_name': fd.get('class_name'), 'complexity': fd.get('complexity', 1),
                    'lineno': fd.get('lineno', 0), 'is_async': fd.get('is_async', False),
                    'has_db_io': fd.get('has_db_io', False),
                } for fk, fd in v.get('functions', {}).items()
            }
        }

    return jsonify({
        'graph': graph, 'summary': summary, 'risk_report': risk, 
        'markdown_doc': md_doc, 'files_data': compact_files,
    })

# ──────────────────────────────────────────────────────
#  OLLAMA STATUS & CHAT
# ──────────────────────────────────────────────────────
@app.route('/api/ollama/status')
def ollama_status_route():
    if err := auth_error(): return err
    return jsonify(ollama_health())

@app.route('/api/chat', methods=['POST'])
def chat():
    if err := auth_error(): return err

    data          = request.get_json(silent=True) or {}
    messages      = data.get('messages', [])
    summary       = data.get('summary', {})
    files_data    = data.get('files_data', {})

    messages = [
        m for m in messages
        if isinstance(m, dict) and m.get('role') in ('user', 'assistant') and isinstance(m.get('content'), str)
    ][-6:]
    
    user_query = messages[-1]['content'] if messages else ""
    compact_ctx = build_compact_context(summary, files_data, user_query)

    system = (
        f"You are an expert code analyst. Read the context below.\n\n"
        f"--- START OF CONTEXT ---\n"
        f"{compact_ctx}\n"
        f"--- END OF CONTEXT ---\n\n"
        f"CRITICAL RULES:\n"
        f"1. The 'EXTRACTED CALL GRAPH' above is 100% accurate. Use it to answer what functions call.\n"
        f"2. Use the 'RELEVANT RAW SOURCE CODE' to explain the exact logic.\n"
        f"3. DO NOT give generic textbook definitions.\n"
        f"4. If the context says '(No specific file matched)', you MUST reply EXACTLY with: 'This function is not defined in the uploaded codebase. It is likely a built-in function or an external library call.' Do not write another word."
    )

    try:
        reply = ollama_chat(system, messages)
        return jsonify({'reply': reply, 'model': OLLAMA_MODEL})
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503

# ──────────────────────────────────────────────────────
#  DOWNLOAD & STATIC ROUTES
# ──────────────────────────────────────────────────────
@app.route('/api/download/docs', methods=['POST'])
def download_docs():
    if err := auth_error(): return err
    data = request.get_json(silent=True) or {}
    md   = data.get('markdown', '')
    name = sanitize(data.get('filename','documentation'),60).replace(' ','_')
    if not md: return jsonify({'error': 'No markdown content'}), 400
    return Response(md, mimetype='text/markdown',
        headers={'Content-Disposition': f'attachment; filename="{name}_docs.md"'})

@app.route('/')
def index():
    return send_from_directory('../frontend/templates', 'index.html')

@app.route('/static/<path:path>')
def static_files(path):
    static_root = Path(app.static_folder).resolve()
    requested   = (static_root / path).resolve()
    if not str(requested).startswith(str(static_root)): return jsonify({'error': 'Forbidden'}), 403
    return send_from_directory(app.static_folder, path)

@app.after_request
def security_headers(resp):
    resp.headers.update({
        'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block', 'Referrer-Policy': 'strict-origin-when-cross-origin',
    })
    return resp

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG','0') == '1', port=5000, host='127.0.0.1')