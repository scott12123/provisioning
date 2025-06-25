from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os
import json
import subprocess
from datetime import datetime
from threading import Event
import shlex

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'devices.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'configured.json')

# Track running processes by Socket.IO session ID
RUNNING = {}


def get_devices():
    """Load the device definition structure."""
    with open(DATA_FILE) as f:
        return json.load(f)


def log_configuration(manufacturer, device, site_type, config_type, csv_line):
    """Append a configuration record to LOG_FILE."""
    record = {
        "timestamp": int(datetime.utcnow().timestamp()),
        "manufacturer": manufacturer,
        "device": device,
        "site_type": site_type,
        "config_type": config_type,
        "csv": csv_line,
    }
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                data = json.load(f)
        else:
            data = []
    except Exception:
        data = []
    data.append(record)
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_recent_configs(manufacturer, device, site_type, config_type, limit=10):
    """Return the most recent configuration records for the given selection."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE) as f:
            data = json.load(f)
    except Exception:
        return []
    filtered = [
        r for r in data
        if r.get("manufacturer") == manufacturer
        and r.get("device") == device
        and r.get("site_type") == site_type
        and r.get("config_type") == config_type
    ]
    filtered.sort(key=lambda r: r.get("timestamp"), reverse=True)
    return filtered[:limit]

def run_command(script_path, sid):
    """Run a Python script and stream each output line back to the client."""
    cmd = f"python3 {script_path}"
    entry = RUNNING.get(sid)
    if not entry:
        entry = {'stop_event': Event(), 'process': None}
        RUNNING[sid] = entry
    stop_evt = entry['stop_event']
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        entry['process'] = proc
        for line in proc.stdout:
            socketio.emit('output', line, to=sid)
            if stop_evt.is_set():
                try:
                    proc.terminate()
                except Exception:
                    pass
                break
        returncode = proc.wait()
    except Exception as exc:
        socketio.emit('output', f"Error: {exc}\n", to=sid)
        returncode = -1

    RUNNING.pop(sid, None)
    if stop_evt.is_set():
        socketio.emit('output', 'Process terminated\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
    else:
        socketio.emit('finished', {'returncode': returncode}, to=sid)


def run_commands(script, params_list, sid):
    """Run a script for each parameter entry in params_list."""
    entry = RUNNING.get(sid)
    if not entry:
        entry = {'stop_event': Event(), 'process': None}
        RUNNING[sid] = entry
    stop_evt = entry['stop_event']

    last_rc = 0
    for params in params_list:
        if stop_evt.is_set():
            break
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
            entry['process'] = proc
            for line in proc.stdout:
                socketio.emit('output', line, to=sid)
                if stop_evt.is_set():
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    break
            last_rc = proc.wait()
        except Exception as exc:
            socketio.emit('output', f"Error: {exc}\n", to=sid)
            last_rc = -1
            break
        if last_rc != 0 or stop_evt.is_set():
            break

    RUNNING.pop(sid, None)
    if stop_evt.is_set():
        socketio.emit('output', 'Process terminated\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
    else:
        socketio.emit('finished', {'returncode': last_rc}, to=sid)


@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/device-config')
def device_config():
    """Display the device configuration page."""
    devices = get_devices()
    return render_template('device_config.html', devices=devices)


@app.route('/recent-configs')
def recent_configs():
    """Return recent configuration records as JSON."""
    m = request.args.get('manufacturer')
    d = request.args.get('device')
    st = request.args.get('site_type')
    ct = request.args.get('config_type')
    records = get_recent_configs(m, d, st, ct, limit=3)
    return {'configs': records}


@app.route('/all-configs')
def all_configs():
    """Return configuration records as JSON, optionally filtered."""
    m = request.args.get('manufacturer')
    d = request.args.get('device')
    st = request.args.get('site_type')
    ct = request.args.get('config_type')

    if not os.path.exists(LOG_FILE):
        return {'configs': []}
    try:
        with open(LOG_FILE) as f:
            data = json.load(f)
    except Exception:
        data = []

    if all([m, d, st, ct]):
        data = [
            r for r in data
            if r.get('manufacturer') == m
            and r.get('device') == d
            and r.get('site_type') == st
            and r.get('config_type') == ct
        ]

    data.sort(key=lambda r: r.get('timestamp'), reverse=True)
    return {'configs': data}

@app.route('/device-reset')
def device_reset():
    """Display the device configuration page."""
    devices = get_devices()
    return render_template('device_reset.html', devices=devices)

@app.route('/label_printer')
def label_printer():
    """Display the device configuration page."""
    devices = get_devices()
    return render_template('label_printer.html', devices=devices)

@app.route('/telemetry_device')
def telemetry_device():
    """Display the device configuration page."""
    devices = get_devices()
    return render_template('telemetry_device.html', devices=devices)

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

    # Register running task for this session
    RUNNING[sid] = {'stop_event': Event(), 'process': None}

    for line in csv_lines:
        log_configuration(manufacturer, device, site_type, config_type, line)

    if csv_lines:
        socketio.start_background_task(run_commands, script, csv_lines, sid)
    else:
        socketio.start_background_task(run_command, script, sid)


@socketio.on('run_reset')
def run_reset():
    """Run the Cambium reset script without any parameters."""
    sid = request.sid
    socketio.emit('output', 'Running cambium/reset.py\n', to=sid)
    RUNNING[sid] = {'stop_event': Event(), 'process': None}
    socketio.start_background_task(run_command, 'cambium/reset.py', sid)

@socketio.on('configure_tinys3')
def configure_tinys3(data=None):
    """Run the TinyS3 configuration script with optional label printing."""
    sid = request.sid
    print_label = False
    if isinstance(data, dict):
        print_label = bool(data.get('print_label'))
    script = 'victron/tinys3_configuration.py'
    if print_label:
        script += ' --print-label'
    socketio.emit('output', f'Running {script}\n', to=sid)
    RUNNING[sid] = {'stop_event': Event(), 'process': None}
    socketio.start_background_task(run_command, script, sid)


@socketio.on('print_label')
def print_label(data):
    """Run the label printing script with provided text."""
    sid = request.sid
    text = data.get('text', '') if isinstance(data, dict) else ''
    qr = bool(data.get('qr')) if isinstance(data, dict) else False

    if not isinstance(text, str) or not text.strip():
        socketio.emit('output', 'Invalid label text\n', to=sid)
        socketio.emit('finished', {'returncode': -1}, to=sid)
        return

    script = f"print_label.py --text {shlex.quote(text)}"
    if qr:
        script += " --qr"

    socketio.emit('output', f'Running {script}\n', to=sid)
    RUNNING[sid] = {'stop_event': Event(), 'process': None}
    socketio.start_background_task(run_command, script, sid)


@socketio.on('stop_script')
def stop_script():
    """Terminate the currently running script for this session."""
    sid = request.sid
    entry = RUNNING.get(sid)
    if not entry:
        return
    entry['stop_event'].set()
    proc = entry.get('process')
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
