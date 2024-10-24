import http.server
import socketserver
import utils
import pickle
import pandas as pd
import json
import numpy as np
from sklearn import svm
from sklearn.preprocessing import MaxAbsScaler
import warnings
import threading
import time
import requests
import datetime

# Suppress all future warnings, including those from pandas
warnings.simplefilter(action='ignore', category=FutureWarning)

# Load the model and the scaler
model = pickle.load(open('finalized_model.sav','rb'))
scaler = MaxAbsScaler()


# Define the port to run the server on
PORT = 8081
# Global DataFrame to collect all data
ALL_COLLECTED_DATA = pd.DataFrame()
# Global variable to determine the periodic check interval
PERIODIC_CHECK = 5

def getTime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')

def send_prediction_to_server(prediction, probability):
    """ Function that sends the prediction to the server. """
    url = "http://localhost:8082"
    headers = {'Content-type': 'application/json'}
    data = {"prediction": prediction, "probability": probability}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    print(response.text)


def process_data_async():
    """ Function that runs the computation logic asynchronously. """
    global ALL_COLLECTED_DATA

    while True:
        print("Checking for new data...")
        if len(ALL_COLLECTED_DATA) > 1:
            # Get the timestamps of the most recent and oldest data
            start_timestamp = ALL_COLLECTED_DATA["eyeDataTimestamp"].min()
            end_timestamp = ALL_COLLECTED_DATA["eyeDataTimestamp"].max()
            time_diff = end_timestamp - start_timestamp


            # check if most recent data is no older than 10 seconds
            # if it is we can drop the data and wait for more




            # Assuming the threshold is 10 seconds (10000 milliseconds) + 2 seconds buffer
            if time_diff > 12000:
                relevant_data = ALL_COLLECTED_DATA[ALL_COLLECTED_DATA["eyeDataTimestamp"] >= (end_timestamp - 12000)]
                features = utils.get_features_for_n_seconds(relevant_data, 10)
                if len(features) == 0:
                    print("No valid features to predict.")
                    continue

                feature_set = features[0]
                feature_set = pd.DataFrame([feature_set])
                feature_set = feature_set[['xDir', 'fixDensPerBB', 'stdFix', 'meanDis', 'maxDis', 'stdDisp', 'maxFix']]
                feature_set = scaler.fit_transform(feature_set)
                feature_set = pd.DataFrame(feature_set, columns=['xDir', 'fixDensPerBB', 'stdFix', 'meanDis', 'maxDis', 'stdDisp', 'maxFix'])

                # Ensure that the array has at least one row before prediction
                if len(features) > 0:
                    result_proba = model.predict_proba(feature_set)
                    result = model.predict(feature_set)
                    print(result_proba)
                    print(result)
                    if max(result_proba[0]) > 0.75:
                        print(f"Prediction result: {result[0]}")
                        send_prediction_to_server(result[0], max(result_proba[0]))
                        PERIODIC_CHECK = 2
                    else:
                        PERIODIC_CHECK = 5
                        print("Prediction probability too low.")
                else:
                    PERIODIC_CHECK = 5
                    print("No valid features to predict.")
            else:
                PERIODIC_CHECK = 5
                print("Not enough data yet.")
        else:
            PERIODIC_CHECK = 10
            print("Not enough data collected yet.")

        time.sleep(PERIODIC_CHECK)

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    window = []

    def decodeARTT(self, post_data_str):
        global ALL_COLLECTED_DATA  # Declare that we are using the global DataFrame
        parsed_data = {}
        for line in post_data_str.split('\n'):
            if line:
                try:
                    key, value = line.split(':',1)
                    print("Key:", key, " Vaylue: ", value)
                    if key.strip() in ['gazeDirection_x', 'gazeDirection_y', 'gazeDirection_z']:
                        parsed_data[key.strip()] = float(value.strip())
                    elif key.strip() == 'eyeDataTimestamp':
                        parsed_data[key.strip()] = int(value.strip())
                    else:
                        parsed_data[key.strip()] = True if value.strip() == 'True' else False
                except ValueError:
                    print(f"Error parsing line: {line}")
                    continue
        df = pd.DataFrame([parsed_data])
        print(f"{parsed_data['eyeDataTimestamp']} - new data received.")
        ALL_COLLECTED_DATA = pd.concat([ALL_COLLECTED_DATA, df], ignore_index=True)
        return df

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        post_data_str = post_data.decode('utf-8')
        self.decodeARTT(post_data_str=post_data_str)
        self.send_response_only(200)
        self.end_headers()

def start_server():
    """ Function that starts the server. """
    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=process_data_async, daemon=True).start()

    start_server()