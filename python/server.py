import http.server
import socketserver
import utils
import pickle
import pandas as pd
import json
from sklearn.preprocessing import MaxAbsScaler
from keras.models import load_model
import warnings
import threading
import time
import requests
import datetime

# Suppress all future warnings, including those from pandas
warnings.simplefilter(action='ignore', category=FutureWarning)

model = load_model('model.keras')
scaler = MaxAbsScaler()
with open('label_encoder.pkl', 'rb') as f:
    label_encoder = pickle.load(f)


# Define the port to run the server on
PORT = 8081
# Global DataFrame to collect all data
ALL_COLLECTED_DATA = pd.DataFrame()
# Global variable to determine the periodic check interval
PERIODIC_CHECK = 5

def getTimeMili(unix_time_ns):
    print(f"Received unix_time_ns: {unix_time_ns}")
    try:
        # Convert nanoseconds to seconds
        unix_time_s = unix_time_ns / 1e3
        # Ensure unix_time_s is within a valid range
        if unix_time_s < 0 or unix_time_s > 2147483647:
            raise ValueError("Invalid unix_time value")
        time = datetime.datetime.fromtimestamp(unix_time_s).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Converted unix_time_s: {time}")
        return time
    except (OSError, ValueError) as e:
        print(f"Error converting unix_time_ns: {e}")
        return None

def send_prediction_to_server(prediction, probability):
    """ Function that sends the prediction to the server. """
    url = "http://localhost:8082"
    headers = {'Content-type': 'application/json'}
    data = {"prediction": prediction, "probability": str(probability)}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    print(response.text)

def send_prediction_to_pod(prediction, probability, endTime):
    """ Function that sends the prediction to the server. """
    url = "http://localhost:8085/classify"
    headers = {'Content-type': 'application/json'}
    if (prediction == "Reading"):
        data = {"classification": "ReadAction","schemaName" : "Read action", "endTime" : endTime, "probability": str(probability)}
    elif (prediction == "Searching"):
        data = {"classification": "SearchAction","schemaName" : "Search action", "endTime" : endTime, "probability": str(probability)}
    else:
        data = {"classification": "CheckAction","schemaName" : "Check action", "endTime" : endTime, "probability": str(probability)}

    response = requests.post(url, data=json.dumps(data), headers=headers)
    print(response.text)


def process_data_async():
    """ Function that runs the computation logic asynchronously. """
    global ALL_COLLECTED_DATA
    currentlyPredicting = False
    while True:
        print("Checking for new data...")
        if len(ALL_COLLECTED_DATA) > 1:
            # Get the timestamps of the most recent and oldest data
            start_timestamp = ALL_COLLECTED_DATA["eyeDataTimestamp"].min()
            end_timestamp = ALL_COLLECTED_DATA["eyeDataTimestamp"].max()
            current_timestamp = int(time.time() * 1000)
            novelty = (current_timestamp - end_timestamp ) / 1000
            time_diff = end_timestamp - start_timestamp

            # check if most recent data is no older than 10 seconds
            # if it is we can drop the data and wait for more
            if novelty < 10 and time_diff > 12000:
                relevant_data = ALL_COLLECTED_DATA[ALL_COLLECTED_DATA["eyeDataTimestamp"] >= (end_timestamp - 12000)]
                features = utils.get_features_for_n_seconds(relevant_data, 10)
                if len(features) != 0:
                    if not currentlyPredicting:
                        feature_set = features[0]
                        feature_set = pd.DataFrame([feature_set])
                        feature_set = feature_set.drop(columns=['duration'])
                        feature_set = scaler.fit_transform(feature_set)

                        # Ensure that the array has at least one row before prediction
                        if len(features) > 0:
                            currentlyPredicting = True
                            print("trying to predict")
                            result = model.predict(feature_set)
                            predicted_classes = result.argmax(axis=1)  # Get class index with highest probability
                            predicted_labels = label_encoder.inverse_transform(predicted_classes)
                            print(result)
                            print(predicted_classes)
                            print(predicted_labels)
                            print(f"Prediction result: {predicted_labels[0]}")
                            # can add check to only send prediciton if passed certainty threshhold
                            if result[0][predicted_classes[0]] > 0.7:
                                # get endTime of the last data point
                                endTime = getTimeMili(end_timestamp)
                                # send_prediction_to_pod(predicted_labels[0], result[0][predicted_classes[0]], endTime)
                                send_prediction_to_server(predicted_labels[0], result[0][predicted_classes[0]])
                            else:
                                print("Prediction not sent, not enough certainty.")
                            PERIODIC_CHECK = 2
                            currentlyPredicting = False
                    
                        else:
                            PERIODIC_CHECK = 5
                            print("No valid features to predict.")
                else:
                    PERIODIC_CHECK = 5
                    print("Not enough data collected yet.")
            else:
                PERIODIC_CHECK = 10
                if novelty > 10:
                    print("Data too old, dropping.")    
                    ALL_COLLECTED_DATA = pd.DataFrame()
                else:
                    print("Not enough data collected yet.")
        else:
            PERIODIC_CHECK = 10
            print("Not enough data collected yet.")

        time.sleep(PERIODIC_CHECK)

data_lock = threading.Lock()
packets_lock = threading.Lock()

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    data_frames = []  # List to collect DataFrames
    concat_interval = 60  # Number of DataFrames to collect before concatenating
    packets = 0

    def decodeARTT(self, post_data_str):
        global ALL_COLLECTED_DATA  # Declare that we are using the global DataFrame
        parsed_data = {}

        for line in post_data_str.split('\n'):
            if line:
                try:
                    key, value = line.split(':',1)
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
        
        with data_lock:
            SimpleHTTPRequestHandler.data_frames.append(df)
            with packets_lock:
                SimpleHTTPRequestHandler.packets += 1
            # Concatenate DataFrames periodically
            if len(SimpleHTTPRequestHandler.data_frames) >= self.concat_interval:
                ALL_COLLECTED_DATA = pd.concat([ALL_COLLECTED_DATA] + SimpleHTTPRequestHandler.data_frames, ignore_index=True)
                print(f"Concatenated {self.concat_interval} DataFrames.")
                SimpleHTTPRequestHandler.data_frames = []  # Reset the list after concatenation
                print("Total packets: ", self.packets)
        return df

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        post_data_str = post_data.decode('utf-8')
        # Process the request in a separate thread
        threading.Thread(target=self.handle_post, args=(post_data_str,)).start()
        
        self.send_response_only(200)
        self.end_headers()

    def handle_post(self, post_data_str):
        self.decodeARTT(post_data_str=post_data_str)

def start_server():
    """ Function that starts the server. """
    with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=process_data_async, daemon=True).start()

    start_server()