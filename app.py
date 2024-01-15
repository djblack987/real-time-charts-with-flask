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

from plsmodel import PLSModel


from flask import Flask, Response, render_template, request, stream_with_context





logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

directory = 'data'

headers = 'headers.csv'

data_queue = queue.Queue()

PLS = PLSModel(headers)
PLS.train_model('calibration_231221.csv')

class FileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.csv'):
            try:
                
                PLS.read_csv(event.src_path)
                PLS.predict()
                time = PLS.results_df.iloc[-1]["time"].strftime("%H:%M:%S")
                thc =  PLS.results_df.iloc[-1]["THC"]
                data_dict = {"time": time, "value": thc}
                json_data = json.dumps(data_dict)
                print(json_data)
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
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@app.route("/")
def index() -> str:
    return render_template("index.html", rmse=PLS.rmse, r2=PLS.score, n_lvs=PLS.pls.best_params_["n_components"])




def generate_data() -> Iterator[str]:
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



@app.route("/chart-data")
def chart_data() -> Response:
    """
    The function `chart_data` returns a `Response` object.
    """
    response = Response(stream_with_context(generate_data()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response

@app.route("/save-data", methods=["POST"])
def save_results() -> str:
    """
    The function `save_results` saves the results to a CSV file.
    """
    
    PLS.save_results("results.csv")
    return "Results saved!"

# The code `watchdog_thread = threading.Thread(target=watch_csv_file, args=(directory,))` creates a
# new thread that will execute the `watch_csv_file` function with the `directory` argument.
watchdog_thread = threading.Thread(target=watch_csv_file, args=(directory,))
watchdog_thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", threaded=True, debug=True)
