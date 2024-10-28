using System;
using System.Text;
using System.Net;
using System.Threading;
using UnityEngine;
using PimDeWitte.UnityMainThreadDispatcher;
using UnityEngine.Windows.Speech;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;

public class HttpServerScript : MonoBehaviour
{
    private HttpListener listener;
    public TMPro.TMP_Text textMeshPro;
    public TMPro.TMP_Text popUpTest;
    private Thread listenerThread;
    private bool serverRunning = false;
    private String currentPrediction;
    public GameObject popUpContainer;
    private DictationRecognizer dictationRecognizer;

    public int port = 8080; // The port the server will listen on
    private Task<HttpResponseMessage> response;

    void Start()
    {
        StartServer();
    }

    void StartServer()
    {
        listener = new HttpListener();
        listener.Prefixes.Add($"http://*:{port}/");
        listenerThread = new Thread(new ThreadStart(ListenForRequests))
        {
            IsBackground = true
        };
        listenerThread.Start();
        serverRunning = true;
        Debug.Log($"HTTP Server started on port {port}");
    }

    void ListenForRequests()
    {
        try
        {
            listener.Start();
            while (serverRunning)
            {
                HttpListenerContext context = listener.GetContext();
                HttpListenerRequest request = context.Request;
                HttpListenerResponse response = context.Response;

                if (request.HttpMethod == "POST")
                {
                    // Read data from the request body
                    using (var reader = new System.IO.StreamReader(request.InputStream, request.ContentEncoding))
                    {
                        string requestData = reader.ReadToEnd();

                        PredictionData predictionData = JsonUtility.FromJson<PredictionData>(requestData);
                        Debug.Log($"Received prediction: {predictionData.prediction}  with propability: {predictionData.probability}");

                        UnityMainThreadDispatcher.Instance().Enqueue(() =>
                        {
                            UpdateCurrentPrediction(predictionData);
                        });

                        byte[] responseBuffer = Encoding.UTF8.GetBytes("Data received successfully");
                        response.ContentLength64 = responseBuffer.Length;
                        response.OutputStream.Write(responseBuffer, 0, responseBuffer.Length);
                        response.OutputStream.Close();
                    }
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"HTTP Server Error: {e.Message}");
        }
    }

    void OnApplicationQuit()
    {
        StopServer();
    }

    void StopServer()
    {
        serverRunning = false;
        if (listener != null && listener.IsListening)
        {
            listener.Stop();
            listener.Close();
        }
        Debug.Log("HTTP Server stopped.");
    }

    void UpdateCurrentPrediction(PredictionData data)
    {
        if (!data.prediction.Equals(currentPrediction))
        {
            textMeshPro.text = data.prediction;
            currentPrediction = data.prediction;
            Debug.Log(currentPrediction);

            if (currentPrediction.Equals("Reading"))
            {

                popUpContainer.SetActive(true);
                popUpTest.text = "Looking for a Word? Simply say it.";
                StartListeningForWord();
                Debug.Log("reading");
            }
            else if (currentPrediction.Equals("Search"))
            {
                popUpTest.text = "Starting Object recognition.";
                popUpContainer.SetActive(true);
                Debug.Log("searching");
            }
            else if (currentPrediction.Equals("Inspection"))
            {
                popUpTest.text = "Do you need additional Information?";
                popUpContainer.SetActive(true);
                Debug.Log("inspecting");
            }
        }
    }


    private void StartListeningForWord()
    {
        dictationRecognizer = new DictationRecognizer();
        dictationRecognizer.DictationResult += DictationRecognizer_DictationResult;
        dictationRecognizer.Start();

    }

    private void DictationRecognizer_DictationResult(string text, ConfidenceLevel confidence)
    {
        popUpTest.text = "Looking for: " + text;

        HttpClient client = new HttpClient()
        {
            BaseAddress = new Uri(" https://api.dictionaryapi.dev/api/v2/entries/en/"),
        };

        HttpResponseMessage result = client.GetAsync(text).Result;
        Debug.Log(result.Content);

        Debug.Log(text);
    }


    public void DisableButton()
    {
        popUpContainer.SetActive(false);
        dictationRecognizer.DictationResult -= DictationRecognizer_DictationResult;
        dictationRecognizer.Stop();
        dictationRecognizer.Dispose();
    }


    [Serializable]
    public class PredictionData
    {
        public string prediction;
        public string probability;
    }
}
