from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__) # create a Flask app instance - this is the main entry point for the application
CORS(app) # allows the app to get requests from other domains


@app.route('/')
def home():
    return 'Hello, World!'

#@app.route('/project_name')
#def project_name():
#    return 'Project Name'

@app.route('/project_name')
def project_name():

    project = {
        "name": "Wireless Research",

        "description": "Testing hardware resources",

        "hardware": [

            {
                "name": "HWSet1",
                "capacity": 20,
                "available": 12,
                "checkedOut": 8
            },

            {
                "name": "HWSet2",
                "capacity": 10,
                "available": 6,
                "checkedOut": 4
            }

        ]
    }


    return jsonify(project)

if __name__ == '__main__':
    app.run(debug=True)