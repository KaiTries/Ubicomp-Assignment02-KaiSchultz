using System.Collections;
using System.Collections.Generic;
using Palmmedia.ReportGenerator.Core.Logging;
using UnityEngine;

public class NewBehaviourScript : MonoBehaviour
{
    public Rigidbody2D myBody;
    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        if(Input.GetKeyDown(KeyCode.Space) == true && myBody.velocity.y <= 0.2) {
            myBody.velocity = Vector2.up * 3;
        }
        if(gameObject.transform.position.y < -0.5) {
            myBody.velocity = Vector2.zero;
            gameObject.transform.position = new Vector3(0,0,10);
            
        } 
        
    }
}
