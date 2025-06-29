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
be any shell command or script path available on the host. While a script is
running the **Run** button turns into a red **Stop** button. Clicking it sends a
`stop_script` event to the server which terminates the running process and
emits the final `finished` message.

## Label printing

When the **Print** button is used on the label printer page, the browser sends a
`print_label` Socket.IO event containing the HTML for the label. The server
saves the received HTML to `last_label.html` and replies with an `output` message
showing the path. A final `finished` event indicates completion.

## Custom logging

Scripts can append arbitrary data to `configured.json` using
`common.functions.insert_data()`. Pass either a field name and value or any
number of keyword arguments. Each field is stored as a separate entry with its
own timestamp:

```python
from common import functions

# Log a single field
functions.insert_data("serial_number", "abcd1234")

# Or multiple fields at once
functions.insert_data(serial="S1", mac="00:11:22:33:44:55")

# Alternatively update the most recent entry
functions.append_to_last_record({"serial_number": "abcd1234", "mac": "00:11:22:33:44:55"})
```
