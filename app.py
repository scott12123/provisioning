from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'devices.json')


def get_scripts():
    with open(DATA_FILE) as f:
        return json.load(f)


@app.route('/')
def index():
    scripts = get_scripts()
    return render_template('index.html', scripts=scripts)


@socketio.on('run_script')
def run_script(data):
    manufacturer = data.get('manufacturer')
    device = data.get('device')
    script = data.get('script')
    if not manufacturer or not device or not script:
        socketio.emit('output', 'Missing selection\n', to=request.sid)
        return

    socketio.emit('output', f"Running {script} for {manufacturer} {device}\n", to=request.sid)
    socketio.emit('finished', {'returncode': 0}, to=request.sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
