import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort
from functools import wraps
from werkzeug.utils import secure_filename
import webbrowser  # 引入 webbrowser 模块

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PASSWORD'] = os.environ.get('FILE_MANAGER_PASSWORD', '142536')
app.config['BASE_DIR'] = os.getcwd()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def safe_join(base, path):
    base = os.path.abspath(base)
    requested_path = os.path.abspath(os.path.join(base, path))
    if not requested_path.startswith(base):
        return None
    return requested_path

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == app.config['PASSWORD']:
            session['logged_in'] = True
            return redirect(url_for('browse'))
        return render_template('login.html', error="Invalid password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('browse'))

@app.route('/browse')
@app.route('/browse/<path:subpath>')
@login_required
def browse(subpath=''):
    current_dir = app.config['BASE_DIR']
    full_path = safe_join(current_dir, subpath)
    
    if not full_path or not os.path.exists(full_path):
        abort(404)
    
    if not os.path.isdir(full_path):
        return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))
    
    files = []
    dirs = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        if os.path.isdir(item_path):
            dirs.append((item, os.path.join(subpath, item) if subpath else item))
        else:
            size = os.path.getsize(item_path)
            files.append((item, size))
    
    parent_dir = os.path.dirname(subpath) if subpath else None
    return render_template('browse.html', 
                         dirs=dirs,
                         files=files,
                         current_path=subpath,
                         parent_dir=parent_dir)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    current_path = request.form.get('current_path', '')
    full_path = safe_join(app.config['BASE_DIR'], current_path)
    
    if not full_path or not os.path.isdir(full_path):
        abort(400)
    
    if 'file' not in request.files:
        return redirect(request.referrer)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.referrer)
    
    filename = secure_filename(file.filename)
    save_path = os.path.join(full_path, filename)
    file.save(save_path)
    return redirect(request.referrer)

@app.route('/delete', methods=['POST'])
@login_required
def delete():
    current_path = request.form.get('current_path', '')
    filename = request.form.get('filename')
    
    full_path = safe_join(app.config['BASE_DIR'], os.path.join(current_path, filename))
    
    if not full_path or not os.path.exists(full_path):
        abort(404)
    
    if os.path.isdir(full_path):
        os.rmdir(full_path)
    else:
        os.remove(full_path)
    
    return redirect(request.referrer)

@app.route('/edit/<path:filename>')
@login_required
def edit(filename):
    full_path = safe_join(app.config['BASE_DIR'], filename)
    
    if not full_path or not os.path.isfile(full_path):
        abort(404)
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return render_template('edit.html', 
                         filename=filename,
                         content=content,
                         current_path=os.path.dirname(filename))

@app.route('/save', methods=['POST'])
@login_required
def save():
    filename = request.form.get('filename')
    content = request.form.get('content')
    
    full_path = safe_join(app.config['BASE_DIR'], filename)
    
    if not full_path or not os.path.isfile(full_path):
        abort(404)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Ensure we don't try to redirect to an empty string
    subpath = os.path.dirname(filename)
    if not subpath:
        subpath = ''
    
    return redirect(url_for('browse', subpath=subpath))

if __name__ == '__main__':
    port = 5000
    lan_ip = "http://127.0.0.1:{}/".format(port)  # 使用本地回环地址
    
    print("Opening browser to:", lan_ip)
    webbrowser.open(lan_ip)
    
    app.run(debug=True, port=port)