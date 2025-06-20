from flask import Flask, render_template, request
from flask_socketio import SocketIO
import subprocess
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

REPO_ROOT = os.path.dirname(os.path.abspath(__file__ + '/../'))
SCRIPT_DIRS = {
    'cambium': os.path.join(REPO_ROOT, 'cambium'),
    'mikrotik': os.path.join(REPO_ROOT, 'mikrotik')
}


def get_scripts():
    data = {}
    for manuf, path in SCRIPT_DIRS.items():
        if os.path.isdir(path):
            data[manuf] = [f for f in os.listdir(path) if f.endswith('.py')]
    return data


@app.route('/')
def index():
    scripts = get_scripts()
    return render_template('index.html', scripts=scripts)


@socketio.on('run_script')
def run_script(data):
    manufacturer = data.get('manufacturer')
    script = data.get('script')
    if not manufacturer or not script:
        socketio.emit('output', 'Missing selection\n', to=request.sid)
        return

    path = SCRIPT_DIRS.get(manufacturer)
    script_path = os.path.join(path, script)
    if not os.path.isfile(script_path):
        socketio.emit('output', 'Script not found\n', to=request.sid)
        return

    def run():
        process = subprocess.Popen(
            ['python3', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in process.stdout:
            socketio.emit('output', line, to=request.sid)
        process.wait()
        socketio.emit('finished', {'returncode': process.returncode}, to=request.sid)

    socketio.start_background_task(run)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
