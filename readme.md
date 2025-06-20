# Provisioning Pi

This Flask application exposes a small web UI to run provisioning scripts. The
available scripts are defined in `devices.json` and grouped by manufacturer and
model. The UI lets you choose a combination and run the corresponding script.

## Running the app

```bash
pip install -r requirements.txt
python app.py
```

Then browse to `http://localhost:5000`.

## How script execution works

When **Run** is clicked the selected script name is sent to the server over a
Socket.IO channel. The server starts the command in a background thread using
`subprocess.Popen`. Each line of output from the command is emitted back to the
browser via `socketio.emit('output', line)`. When the command finishes the final
return code is sent using the `finished` event. The browser appends the output
and exit status to the console area.

The actual script value is executed directly by the operating system, so it can
be any shell command or script path available on the host.
