import os
import json
import sqlite3
import threading
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import(
    Flask,
    render_template,
    request,
    send_from_directory,
    abort,
    redirect,
    url_for,
    jsonify,
    flash
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)




base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_file_structure(root_path):
    """Recursively scans a directory and returns its structure as a list of dictionaries."""
    file_system = []
    # A set of directories and files to ignore.
    ignore_list = {'.git', '__pycache__', 'node_modules', '.vscode'}

    for item in os.listdir(root_path):
        if item in ignore_list:
            continue

        path = os.path.join(root_path, item)
        
        if os.path.isdir(path):
            file_system.append({
                'type': 'folder',
                'name': item,
                'children': get_file_structure(path)
            })
        else:
            file_system.append({
                'type': 'file',
                'name': item
            })
            
    return file_system


#a flask to ignore web pulling condition
app = Flask(__name__)
app.secret_key = os.getenv("decryption_key")
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
@app.route('/')
@limiter.limit("20 per minute")
def home():
    return render_template("404.html"), 200



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to /login if user is not logged in


# Define a simple user store for demonstration purposes
users = {'admin': {'password': os.getenv("MDB_pass_shadow")}}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    @staticmethod
    def get(user_id):
        if user_id in users:
            return User(user_id)
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Login and Logout Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('files'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/create_folder', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def create_folder():
    data = request.get_json()
    current_path = data.get('path', '')
    foldername = data.get('foldername')

    if not foldername:
        return jsonify({"error": "Folder name is required"}), 400

    full_path = os.path.join(base_dir, current_path, foldername)

    try:
        os.makedirs(full_path)
        return jsonify({"message": "Folder created successfully"}), 200
    except FileExistsError:
        return jsonify({"error": "Folder already exists"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500



#admin panel route
@app.route('/admin', methods=['GET'])
@login_required
@limiter.limit("10 per minute")
def admin_route():
    key = request.args.get("key")
    if key != os.getenv("MDB_pass_shadow"):
        abort(403, description="You are not a admin")
    return render_template("admin.html"), 200


# Route to list files and directories
@app.route("/files", defaults={'req_path': ''})
@app.route("/files/<path:req_path>")
@login_required
@limiter.limit("60 per minute")
def files(req_path):
    abs_path = os.path.join(base_dir, req_path)
    abs_path = os.path.abspath(abs_path)
    if not abs_path.startswith(base_dir):
        return "Access Denied 🛑", 403
    if os.path.isdir(abs_path):
        try:
            files = os.listdir(abs_path)
            files = sorted(files, key=lambda f: (not os.path.isdir(os.path.join(abs_path, f)), f.lower()))
            file_infos = []
            for f in files:
                full_item_path = os.path.join(abs_path, f)
                is_dir = os.path.isdir(full_item_path)
                file_size = os.path.getsize(full_item_path) if not is_dir else None # Get size only for files
                file_infos.append({"name": f, "is_dir": is_dir, "size": file_size}) # Add 'size'
            
            parent_path = os.path.dirname(req_path)
            return render_template("files.html", files=file_infos, current_path=req_path, parent_path=parent_path)
        except Exception as e:
            print(f"Error listing files: {e}")
            return "Error loading files", 500
    else:
        return redirect(url_for("view_file", filepath=req_path))
    

@app.route('/create_file', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def create_file():
    try:
        data = request.get_json()
        current_path = data.get('path', '').strip('/')
        filename = data.get('filename', 'new_file.txt')
        if not filename:
            return jsonify({"error": "Filename cannot be empty"}), 400
        full_path = os.path.abspath(os.path.join(base_dir, current_path, filename))

        if not full_path.startswith(base_dir):
            print("Invalid path:", full_path)
            return jsonify({"error": "Invalid path"}), 400

        if os.path.exists(full_path):
            print("File already exists:", full_path)
            return jsonify({"error": "File already exists"}), 409

        with open(full_path, 'w') as f:
            f.write('')  # create an empty file

        print("File created:", full_path)
        return jsonify({"message": "File created"}), 201

    except Exception as e:
        print("Exception creating file:", str(e))
        return jsonify({"error": str(e)}), 500


# Route to view a file
@login_required
@limiter.limit("10 per minute")
@app.route('/view/<path:filepath>')
def view_file(filepath):
    """
    Determines the file type and renders the main viewer page.
    """
    full_path = os.path.join(base_dir, filepath)
    if not os.path.exists(full_path):
        return "File not found", 404

    content = ""
    file_extension = (os.path.splitext(filepath)[1] or "").lower()
    
    if file_extension == '.db':
        try:
            con = sqlite3.connect(full_path)
            con.row_factory = sqlite3.Row
            cursor = con.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            db_data = []
            for table_name in tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [row['name'] for row in cursor.fetchall()]
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = [dict(row) for row in cursor.fetchall()]
                db_data.append({"name": table_name, "columns": columns, "rows": rows})
            
            content = json.dumps(db_data)
            con.close()
        except Exception as e:
            content = f"Error reading database: {e}"
    elif file_extension in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
        pass  # Image files will be handled by the raw_file route
    else:
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            content = "Cannot display file: Content is not valid UTF-8 text."
    return render_template('viewer.html', filename=filepath, content=content)


@app.route('/raw_file/<path:filepath>')
def serve_raw_file(filepath):
    return send_from_directory(base_dir, filepath, as_attachment=False)


# Route to edit a file
@app.route('/edit/<path:filename>', methods=['GET'])
@login_required
@limiter.limit("10 per minute")
def edit_file(filename):
    abs_path = os.path.join(base_dir, filename)
    if not abs_path.startswith(base_dir) or not os.path.isfile(abs_path):
        return "Invalid file path", 403
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template("editor.html", filename=filename, content=content)
    except Exception as e:
        return f"Error reading file: {str(e)}", 500


# Route to save a file
@app.route('/save', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def save_file():
    data = request.get_json()
    filepath = data.get("filename")
    content = data.get("content")
    abs_path = os.path.abspath(os.path.join(base_dir, filepath))

    if not abs_path.startswith(base_dir):
        return jsonify({"success": False, "message": "Invalid file path"}), 403
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({"success": True, "message": "File saved successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# Route to delete a file or directory
@app.route('/delete_file', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def delete_file():
    import os, shutil
    from flask import request, jsonify

    data = request.get_json()
    current_path = data.get('path', '').strip('/')
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Filename cannot be empty"}), 400
    target_path = os.path.abspath(os.path.join(base_dir, current_path, filename))

    if not target_path.startswith(base_dir):
        return jsonify({"error": "Invalid file path"}), 400
    try:
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        elif os.path.isfile(target_path):
            os.remove(target_path)
        else:
            return jsonify({"error": "File or directory not found"}), 404
        return jsonify({"message": "Deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    req_path = request.form.get('path', '') # Get the current path from the form data

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        full_dir_path = os.path.abspath(os.path.join(base_dir, req_path.strip('/')))
        if not full_dir_path.startswith(base_dir):
            return jsonify({'error': 'Invalid upload path'}), 400
        filename = os.path.basename(file.filename)
        filepath = os.path.join(full_dir_path, filename)

        try:
            file.save(filepath)
            return jsonify({'message': 'File uploaded successfully'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        

# API route to get file structure
@app.route('/api/files')
@login_required
@limiter.limit("10 per minute")
def api_files():
    """Provides the entire file structure as JSON for the viewer modal."""
    structure = get_file_structure(base_dir) 
    return jsonify(structure)


# Route to download a file
@app.route('/download/<path:filepath>')
@login_required
@limiter.limit("10 per minute")
def download_file(filepath):
    abs_path = os.path.join(base_dir, filepath)
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception as e:
        return f"Can't download this file: {str(e)}", 500 


# Route to upload a file
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
