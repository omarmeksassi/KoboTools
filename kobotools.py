from tempfile import NamedTemporaryFile
import json

from flask import Flask, send_file, send_from_directory, make_response
from flask import request
import requests

from utils.worker import fetch_api_key, kobo_to_excel, ONA_API_URL

app = Flask(__name__)


@app.route('/fetch-token', methods=['POST'])
def fetch_token():
    user = json.loads(request.data)
    token = fetch_api_key(user['username'], user['password'])

    response = make_response(json.dumps({
        'token': token
    }))

    response.headers['content-type'] = "application/json"
    return response


@app.route('/fetch-forms', methods=['POST'])
def fetch_forms():
    user = json.loads(request.data)
    headers = {"Authorization": "Token {}".format(user['token'])}
    data = requests.get("{}/forms".format(ONA_API_URL), headers=headers).json()
    response = make_response(json.dumps(data))
    response.headers['content-type'] = "application/json"
    return response


@app.route('/download-data/<int:pk>', methods=['POST'])
def download_data(pk):
    try:
        token = request.form.get('userToken', '')
        with NamedTemporaryFile(suffix=".xlsx") as temp:
            kobo_to_excel(pk, token, temp.name)

            response = send_file(temp.name)
            temp.delete = True

        return response
    except e:
        print (e)
    return ""


@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


@app.route('/')
def index():
    return send_file('static/index.html')


if __name__ == '__main__':
    app.run(debug=True)
