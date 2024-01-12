import json
import logging
import sys
import time
from typing import Iterator

import pandas as pd
import queue
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import jsonify


from flask import Flask, Response, render_template, request, stream_with_context





logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

application = Flask(__name__)

directory = 'C:\\NIR\\flask-realtime\\real-time-charts-with-flask\\data'

data_queue = queue.Queue()

class FileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.csv'):
            try:
                df = pd.read_csv(event.src_path)
                result = df.to_dict('records')  # Convert DataFrame to list of dicts
                json_data = json.dumps(result[0])
                data_queue.put(json_data)
            except:
                pass

def watch_csv_file(path):
    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@application.route("/")
def index() -> str:
    return render_template("index.html")




def generate_random_data() -> Iterator[str]:
    """
    The function generates random data and streams it to the client using Server-Sent Events.
    """
    
    if request.headers.getlist("X-Forwarded-For"):
        client_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        client_ip = request.remote_addr or ""
    
    try:
        logger.info(f"Client {client_ip} connected")
        while True:
            json_data = data_queue.get()  # Get json_data from the queue
            yield f"data:{json_data}\n\n"
            print(f"data:{json_data}")
            time.sleep(1)
    except GeneratorExit:
        logger.info(f"Client {client_ip} disconnected")



@application.route("/chart-data")
def chart_data() -> Response:
    """
    The function `chart_data` returns a `Response` object.
    """
    response = Response(stream_with_context(generate_random_data()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


# The code `watchdog_thread = threading.Thread(target=watch_csv_file, args=(directory,))` creates a
# new thread that will execute the `watch_csv_file` function with the `directory` argument.

@application.route('/start-watchdog', methods=['POST'])
def start_watchdog():
    global watchdog_thread
    if not watchdog_thread.is_alive():  # Only start the thread if it's not already running
        watchdog_thread.start()
    return jsonify({'message': 'Watchdog started'}), 200


watchdog_thread = threading.Thread(target=watch_csv_file, args=(directory,))

if __name__ == "__main__":
    application.run(host="0.0.0.0", threaded=True, debug=True)
