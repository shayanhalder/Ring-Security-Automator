# Ring Security Automator

#### A multi-process application that automatically arms or disarms Ring home security using facial recongition running locally on a Raspberry Pi 5. This is used to automate the process of disarming security before entering the house and arming security before leaving the house, both of which are easy to forget especially in a rush.

#### The application consists of two processes: 
* securityController: REST API to remotely arm or disarm security
* facialRecongition: runs a facial recongition model and makes calls to securityController  

## securityController

#### This is a Node.js REST API that allows one to remotely arm or disarm Ring home security. This is done by launching a Chromium instance with Playwright and logging in to the Ring security dashboard with one's credentials. To actually arm or disarm security, it uses Playwright's API to extract the "arm" and "disarm" buttons from the DOM using CSS selectors and automatically clicks them.

#### Session cookies are automatically saved to session.json so the API does not usually need to log back in after being killed. Ring Auth may ocassionally request a two-factor authentication code to log in, and the Node process will prompt the user to enter this code. 
