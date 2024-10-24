import requests
import pandas as pd
import utils

DATA = "../data/RawGazeData/01_Inspection.csv"


def get_data(): 
    return pd.read_csv(DATA)


df = get_data()

df = df[['eyeDataTimestamp', 'gazeDirection_x', 'gazeDirection_y', 'gazeDirection_z', 'isCalibrationValid','gazeHasValue']]

def send_data_to_server(data):
    url = "http://localhost:8081"
    try:
        response = requests.post(url,data)
        response.raise_for_status()  # Raise an error for bad status codes
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")
        return None
    return response

#features = utils.get_features_for_n_seconds(df, 10)



for i in range(0, len(df)):
    current = df.iloc[i]
    requeststring = ""
    for key in current.keys():
        requeststring += key + ":" + str(current[key]) + "\n"
    print(requeststring)
    response = send_data_to_server(requeststring)




#print(features)