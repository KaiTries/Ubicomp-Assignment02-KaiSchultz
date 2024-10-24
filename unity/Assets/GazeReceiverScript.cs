using ARETT;
using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Net.Http;
using System.Threading.Tasks;
using UnityEngine;


public class GazeReceiverScript : MonoBehaviour
{
    // connect the DtatProvider-Prefab from ARETT in the Unity Editor
    public DataProvider DataProvider;
    private ConcurrentQueue<Action> _mainThreadWorkQueue = new ConcurrentQueue<Action>();
    private bool coroutineRunning = false;

    private static readonly HttpClient httpClient = new()
    {
        BaseAddress = new Uri("http://localhost:8081"),
    };

    static async Task PostAsync(HttpClient httpClient, String t)
    {

        using StringContent jsonContent = new(t);

        using HttpResponseMessage response = await httpClient.PostAsync(
            "/",
            jsonContent);

        var jsonResponse = await response.Content.ReadAsStringAsync();

        return;

    }

    // Start is called before the first frame update
    void Start()
    {
    }

    // Update is called once per frame
    void Update()
    {
        // Check if there is something to process
        if (!_mainThreadWorkQueue.IsEmpty)
        {
            // Process all commands which are waiting to be processed
            // Note: This isn't 100% thread save as we could end in a loop when there is still new data coming in.
            //       However, data is added slowly enough so we shouldn't run into issues.
            while (_mainThreadWorkQueue.TryDequeue(out Action action))
            {
                // Invoke the waiting action
                action.Invoke();
            }
        }
    }

    /// <summary>
    /// Starts the Coroutine to get Eye tracking data on the HL2 from ARETT.
    /// </summary>
    public void StartArettData()
    {
        if (coroutineRunning)
        {
            UnsubscribeFromARETTData();
            StopAllCoroutines();
            coroutineRunning = false;
        }
        else
        {
            StartCoroutine(SubscribeToARETTData());
            coroutineRunning = true;
        }
    }

    /// <summary>
    /// Subscribes to newDataEvent from ARETT.
    /// </summary>
    /// <returns></returns>
    private IEnumerator SubscribeToARETTData()
    {
        //*
        _mainThreadWorkQueue.Enqueue(() =>
        {
            DataProvider.NewDataEvent += HandleDataFromARETT;
        });
        //*/

        print("subscribed to ARETT events");
        yield return null;

    }

    /// <summary>
    /// Unsubscribes from NewDataEvent from ARETT.
    /// </summary>
    public void UnsubscribeFromARETTData()
    {
        _mainThreadWorkQueue.Enqueue(() =>
        {
            DataProvider.NewDataEvent -= HandleDataFromARETT;
        });

    }




    /// <summary>
    /// Handles gaze data from ARETT and allows you to do something with it
    /// </summary>
    /// <param name="gd"></param>
    /// <returns></returns>
    public void HandleDataFromARETT(GazeData gd)
    {
        // Some exemplary values from ARETT.
        // for a full list of available data see:
        // https://github.com/AR-Eye-Tracking-Toolkit/ARETT/wiki/Log-Format#gaze-data
        string t = "";
        t += "eyeDataTimestamp:" + gd.EyeDataTimestamp; 
        t += "\nisCalibrationValid:" + gd.IsCalibrationValid;
        t += "\ngazeHasValue:" + gd.GazeHasValue;
        t += "\ngazeDirection_x:" + gd.GazeDirection.x;
        t += "\ngazeDirection_y:" + gd.GazeDirection.y;
        t += "\ngazeDirection_z:" + gd.GazeDirection.z;
        
        Debug.Log(t);

        _ = PostAsync(httpClient, t);

    }

}
