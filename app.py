import os
from grpc.beta import implementations
import tensorflow as tf
from tensorflow_serving.apis import predict_pb2
#original von sap tuturial
#from tensorflow_serving.apis import prediction_service_pb2

#neue version von google
from tensorflow_serving.apis import prediction_service_pb2_grpc

import json
import requests
import flask
from flask import Flask, globals, request, g

app = Flask(__name__)


MODEL_SERVER_HOST = str('.trial.eu-central-1.aws.ml.hana.ondemand.com')
MODEL_SERVER_PORT = int('443')
MODEL_NAME = str('')
ROOT_CERT = str('-----BEGIN CERTIFICATE-----\n-----END CERTIFICATE-----\n').replace('\\n', '\n')

def get_access_token():
 	url = "https://.authentication.eu10.hana.ondemand.com/oauth/token"
 	querystring = {'grant_type': 'client_credentials'}
 	headers = {
 	'authorization': "Basic ",
 	'content-type': 'application/x-www-form-urlencoded'
 	}
 	response = requests.request('POST', url, headers=headers, params=querystring)
 	return 'Bearer ' + json.loads(response.text)['access_token']

def metadata_transformer(metadata):
    additions = []
    token = get_access_token()
    print token
    additions.append(('authorization', token))
    return tuple(metadata) + tuple(additions)


# Neue Methode wegen API Change von Tensorflow
def make_channel(host, port, ssl_channel):
    # In order to make an https call, use an ssl channel with defaults
    #ssl_channel = implementations.ssl_channel_credentials(None, None, None)
    token = get_access_token()
    print token

    auth_header = (
            'Authorization',
            token)
    auth_plugin = implementations.metadata_call_credentials(
            lambda _, cb: cb([auth_header], None),
            name='sap_creds')

    # compose the two together for both ssl and google auth
    composite_channel = implementations.composite_channel_credentials(
            ssl_channel, auth_plugin)

    return implementations.secure_channel(host, port, composite_channel)

@app.route('/', methods=['POST'])

def main():
    credentials = implementations.ssl_channel_credentials(root_certificates=ROOT_CERT)
    # alter aufruf: channel = implementations.secure_channel(MODEL_SERVER_HOST, MODEL_SERVER_PORT, credentials)

    channel = make_channel(MODEL_SERVER_HOST, MODEL_SERVER_PORT, credentials)

    #alter aufruf: stub = prediction_service_pb2.beta_create_PredictionService_stub(channel, metadata_transformer=metadata_transformer)
    stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)

    # process the first file only
    uploaded_files = globals.request.files.getlist('file')
    data = uploaded_files[0].read()
    #data = open('what.jpg', 'rb').read()

    # See prediction_service.proto for gRPC request/response details.
    # change input type and data shapes according to your model
    request = predict_pb2.PredictRequest()
    request.model_spec.name = MODEL_NAME
    request.model_spec.signature_name = 'predict_images'
    request.inputs['images'].CopyFrom(
        tf.contrib.util.make_tensor_proto(data, shape=[1]))

    #print stub.Predict(request, 100)
    return str(stub.Predict(request, 120))

port = os.getenv('PORT', '5000')
if __name__ == '__main__':
    app.debug = not os.getenv('PORT')
    app.run(host='0.0.0.0', port=int(port), debug=False)
