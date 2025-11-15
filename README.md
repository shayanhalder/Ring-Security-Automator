# Ring Security Automator

A multi-process application that automatically arms or disarms Ring home security using facial recongition running locally on a Raspberry Pi 5. This is used to automate the process of disarming security before entering the house and arming security before leaving the house, both of which are easy to forget especially in a rush.

The application consists of two processes: 
* securityController: REST API to remotely arm or disarm security
* facialRecongition: runs a facial recongition model and makes calls to securityController  

## securityController

This is a Node.js REST API that allows one to remotely arm or disarm Ring home security. This is done by launching a Chromium instance with Playwright and logging in to the Ring security dashboard with one's credentials. To actually arm or disarm security, it uses Playwright's API to extract the "arm" and "disarm" buttons from the DOM using CSS selectors and automatically clicks them.

Session cookies are automatically saved to session.json so the API does not usually need to log back in after being killed. Ring Auth may ocassionally request a two-factor authentication code to log in, and the Node process will prompt the user to enter this code. 

## facialRecognition

This is a Python process that identifies authorized members using facial recognition. It keeps track of which authorized members are currently inside the house. If someone is the last person to the leave the house, then it will arm the security with the securityController API. Likewise, if someone is the first person to enter the house, then it will disarm the security. 

To add an authorized member, create a directory under known_faces with the name of the person and add at least 15 JPEG images of them. The images should have variety in the angle they're taken, with a few full side profile shots and others with the face tilted slightly up or down.

Run `python train_embeddings.py` and it will use the buffalo_l facial recognition library to identify the face in each image, creating an average numpy embedding for each person that is stored in `face_encodings.npy`. 

Execute script `./run.sh` to start the entire application. 





