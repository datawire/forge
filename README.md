# Skunkworks

The skunkworks project contains a frontend (react GUI) and backend for
a deployment controller for kubernetes.

## Developing

The frontend has a react implementation of a UI for the
controller. The backend has the flask implementation of the
controller.

### Deploying

The `deploy` script has the code necessary to deploy the local code
into whatever kubernetes cluster your kubectl happens to be point at.

NOTE: This will create/overwrite a deployment and a service named blackbird.

### Running the frontend locally:

1. Follow the setup directions in frontend/README.md

2. Set the REACT_APP_BLACKBIRD_RTM environment variable to point to
   wherever you want to run the backend. (If you are running the backend
   locally, this is likely `http://localhost:5000`.)

3. From the frontend directory, run `npm run start`. This should
   automatically open up a new browser tap with app running.

### Running the backend locally:

1. Create a python virtualenv.

2. From your virtualenv in the backend directory run `pip install -r requirements.txt`

3. From your virtualenv in the backend directory run `python app.py`.
   This will run the backend on `http://localhost:5000` by default.
