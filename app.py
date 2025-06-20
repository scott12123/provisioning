from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os
import json
import subprocess

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'devices.json')


def get_devices():
    """Load the device definition structure."""
    with open(DATA_FILE) as f:
        return json.load(f)

def run_command(script_path, sid):
    """Run a Python script and stream each output line back to the client."""
    cmd = f"python3 {script_path}"  # <-- fix here
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


def run_commands(script, params_list, sid):
    """Run a script for each parameter entry in params_list."""
    last_rc = 0
    for params in params_list:
        cmd = f"python3 {script} {params}"
        socketio.emit('output', f"\n> {cmd}\n", to=sid)
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
            last_rc = proc.wait()
        except Exception as exc:
            socketio.emit('output', f"Error: {exc}\n", to=sid)
            last_rc = -1
            break
        if last_rc != 0:
            break

    socketio.emit('finished', {'returncode': last_rc}, to=sid)


@app.route('/')
def index():
    devices = get_devices()
    return render_template('index.html', devices=devices)


@socketio.on('run_script')
def run_script(data):
    """Validate input and start the selected script."""
    sid = request.sid

    manufacturer = data.get('manufacturer')
    device = data.get('device')
    site_type = data.get('site_type')
    config_type = data.get('config_type')
    script = data.get('script')
    csv_lines = data.get('csv') or []
    if not isinstance(csv_lines, list):
        csv_lines = []

    if not all([manufacturer, device, site_type, config_type, script]):
        socketio.emit('output', 'Missing selection\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
        return

    devices = get_devices()
    try:
        available = devices[manufacturer][device][site_type][config_type]
    except KeyError:
        socketio.emit('output', 'Invalid selection\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
        return

    if script not in available:
        socketio.emit('output', 'Invalid script\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
        return

    socketio.emit(
        'output',
        f"Running {script} for {manufacturer} {device} ({site_type}/{config_type})\n",
        to=sid,
    )

    if csv_lines:
        socketio.start_background_task(run_commands, script, csv_lines, sid)
    else:
        socketio.start_background_task(run_command, script, sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
