from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os
import json
import subprocess

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'devices.json')


def get_scripts():
    with open(DATA_FILE) as f:
        return json.load(f)


def run_command(cmd, sid):
    """Run a command and stream each output line back to the client."""
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            socketio.emit('output', line, to=sid)
        returncode = proc.wait()
    except Exception as exc:
        socketio.emit('output', f"Error: {exc}\n", to=sid)
        returncode = -1

    socketio.emit('finished', {'returncode': returncode}, to=sid)


@app.route('/')
def index():
    scripts = get_scripts()
    return render_template('index.html', scripts=scripts)


@socketio.on('run_script')
def run_script(data):
    manufacturer = data.get('manufacturer')
    device = data.get('device')
    script = data.get('script')
    sid = request.sid
    if not manufacturer or not device or not script:
        socketio.emit('output', 'Missing selection\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
        return

    socketio.emit('output', f"Running {script} for {manufacturer} {device}\n", to=sid)
    socketio.start_background_task(run_command, script, sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
