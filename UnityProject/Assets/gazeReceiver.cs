using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using UnityEngine;

public class gazeReceiver : MonoBehaviour
{
        // connect the DtatProvider-Prefab from ARETT in the Unity Editor
    public ConcurrentQueue<Action> _mainThreadWorkQueue = new ConcurrentQueue<Action>();
    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }
}
