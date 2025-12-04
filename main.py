
import os
import json
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

# =========================
# تنظیمات اولیه
# =========================
APP = Flask(name)

BASE_DIR = Path(file).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"

APP.config['UPLOAD_FOLDER'] = STORAGE_DIR
APP.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav', 'txt', 'json', 'jpg', 'png'}

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# متغیرهای محیطی
# =========================
BOT_TOKEN = os.getenv('BOT_TOKEN', 'dummy-token')

# =========================
# توابع کمکی
# =========================
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in APP.config['ALLOWED_EXTENSIONS']


def save_file(file, folder: str) -> str:
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())

    folder_path = STORAGE_DIR / folder
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path = folder_path / f"{file_id}_{filename}"
    file.save(file_path)

    return str(file_path)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# =========================
# مسیر روت (جلوگیری از Not Found)
# =========================
@APP.route('/', methods=['GET'])
def index():
    return jsonify({
        "message": "API is running successfully 🚀",
        "available_endpoints": [
            "/health",
            "/profile/<user_id>",
            "/track/upload",
            "/track/<track_id>",
            "/track/search?q=",
            "/edit/upload",
            "/edit/<edit_id>",
            "/edit/search?q=",
            "/file/list/<folder>",
            "/file/download/<folder>/<filename>"
        ]
    })


# =========================
# مدیریت کاربران / پروفایل
# =========================
PROFILE_PATH = STORAGE_DIR / 'profiles.json'
profiles = load_json(PROFILE_PATH)


@APP.route('/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    profile = profiles.get(user_id)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    return jsonify(profile)


@APP.route('/profile/<user_id>', methods=['POST', 'PUT'])
def update_profile(user_id):
    data = request.json

    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Invalid data'}), 400

    profiles[user_id] = data
    save_json(PROFILE_PATH, profiles)

    return jsonify({'status': 'Profile saved', 'user_id': user_id})


# =========================
# مدیریت آهنگ‌ها
# =========================
TRACKS_PATH = STORAGE_DIR / 'tracks.json'
tracks = load_json(TRACKS_PATH)


@APP.route('/track/upload', methods=['POST'])
def upload_track():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    path = save_file(file, 'tracks')
    track_id = str(uuid.uuid4())

    tracks[track_id] = {
        'path': path,
        'name': file.filename
    }

    save_json(TRACKS_PATH, tracks)

    return jsonify({'status': 'uploaded', 'track_id': track_id})


@APP.route('/track/<track_id>', methods=['GET'])
def get_track(track_id):
    track = tracks.get(track_id)

    if not track:
        return jsonify({'error': 'Track not found'}), 404

    return send_file(track['path'], as_attachment=True, download_name=track['name'])


@APP.route('/track/search', methods=['GET'])
def search_track():
    query = request.args.get('q', '').lower()

if not query:
        return jsonify({})

    results = {
        tid: t for tid, t in tracks.items()
        if query in t['name'].lower()
    }

    return jsonify(results)


# =========================
# مدیریت ادیت‌ها
# =========================
EDITS_PATH = STORAGE_DIR / 'edits.json'
edits = load_json(EDITS_PATH)


@APP.route('/edit/upload', methods=['POST'])
def upload_edit():
    data = request.json

    if not data or 'content' not in data:
        return jsonify({'error': 'Invalid edit data'}), 400

    edit_id = str(uuid.uuid4())
    edits[edit_id] = data

    save_json(EDITS_PATH, edits)

    return jsonify({'status': 'edit saved', 'edit_id': edit_id})


@APP.route('/edit/<edit_id>', methods=['GET'])
def get_edit(edit_id):
    edit = edits.get(edit_id)

    if not edit:
        return jsonify({'error': 'Edit not found'}), 404

    return jsonify(edit)


@APP.route('/edit/search', methods=['GET'])
def search_edit():
    query = request.args.get('q', '').lower()

    if not query:
        return jsonify({})

    results = {
        eid: e for eid, e in edits.items()
        if query in str(e).lower()
    }

    return jsonify(results)


# =========================
# مدیریت فایل‌ها
# =========================
@APP.route('/file/list/<folder>', methods=['GET'])
def list_files(folder):
    folder_path = STORAGE_DIR / folder

    if not folder_path.exists() or not folder_path.is_dir():
        return jsonify([])

    files = [f.name for f in folder_path.iterdir() if f.is_file()]

    return jsonify(files)


@APP.route('/file/download/<folder>/<filename>', methods=['GET'])
def download_file(folder, filename):
    file_path = STORAGE_DIR / folder / filename

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_path, as_attachment=True)


# =========================
# تست سلامت
# =========================
@APP.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'bot_token': BOT_TOKEN
    })


# =========================
# مدیریت خطاها
# =========================
@APP.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not Found",
        "message": "This endpoint does not exist. Go to / to see available endpoints."
    }), 404


@APP.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Server Error",
        "message": "Something broke on the server."
    }), 500


# =========================
# اجرای برنامه
# =========================
if name == 'main':
    APP.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=True
    )