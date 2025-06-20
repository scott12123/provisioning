from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'devices.json')


def get_devices():
    """Load the device definition structure."""
    with open(DATA_FILE) as f:
        return json.load(f)


@app.route('/')
def index():
    devices = get_devices()
    return render_template('index.html', devices=devices)


@socketio.on('run_script')
def run_script(data):
    manufacturer = data.get('manufacturer')
    device = data.get('device')
    site_type = data.get('site_type')
    config_type = data.get('config_type')
    script = data.get('script')

    if not all([manufacturer, device, site_type, config_type, script]):
        socketio.emit('output', 'Missing selection\n', to=request.sid)
        return

    devices = get_devices()
    try:
        available = devices[manufacturer][device][site_type][config_type]
    except KeyError:
        socketio.emit('output', 'Invalid selection\n', to=request.sid)
        return

    if script not in available:
        socketio.emit('output', 'Invalid script\n', to=request.sid)
        return

    socketio.emit('output',
                   f"Running {script} for {manufacturer} {device} ({site_type}/{config_type})\n",
                   to=request.sid)
    socketio.emit('finished', {'returncode': 0}, to=request.sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
