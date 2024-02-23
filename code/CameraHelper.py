#!/usr/bin/env python

"""
Note: Code taken from https://blog.miguelgrinberg.com/post/video-streaming-with-flask, then modified.
"""

import io
import time
from flask import Flask, render_template_string, Response, request
from picamera import PiCamera
from CameraLibraryCode import Camera
import numpy as np
import cv2
import datetime
import random as rng
import requests
import jsonpickle

rng.seed(42)

app = Flask(__name__)

latest_frame = [None]
latest_sent_frame = [None]
latest_received_frame = [None]

@app.route('/video_streaming_demo', methods=['GET', 'POST'])
def index():
#    <div style="display:flex;flex-wrap:wrap">
    template = """<html>
    <head>
    <title>RPi Camera</title>
    </head>
    <body>
        <div>
            <h1>RPi Camera</h1>
            <img src="{{ url_for('video_feed') }}">
        </div>
    <form action="/video_streaming_demo" method="post">
        <input type="submit" value="Submit">
    </form>
    <img src="{{ url_for('return_feed')}}">
    </body>
</html>"""
    if request.method == 'POST':
        do_classification()
            
    return render_template_string(template)

def do_classification():
    filename = datetime.datetime.now().__str__() + '.jpg'
    with open(filename, 'wb') as f:
        f.write(latest_frame[0])

        nparr = np.frombuffer(latest_frame[0], np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # cv2.IMREAD_COLOR in OpenCV 3.1

        resized = cv2.resize(img_np, (640, 480))
        frame_to_post = cv2.imencode('.jpg', resized)[1].tobytes()

        latest_sent_frame[0] = frame_to_post

        res = requests.post(url='http://192.168.26.20:4999/image',
                            data=frame_to_post,
                            headers={'Content-Type': 'application/octet-stream'})
        return_dict = jsonpickle.decode(res.content)
        latest_received_frame[0] = return_dict['frame']
        model_out = return_dict['model_out']
        return model_out
    
@app.route('/do_classification', methods=['GET'])
def classification_endpoint():
    model_out = do_classification()
    print(model_out)
    return jsonpickle.encode(model_out)

def gen_video_feed(camera):
    """Video streaming generator function."""
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()

        latest_frame[0] = frame

        nparr = np.frombuffer(frame, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # cv2.IMREAD_COLOR in OpenCV 3.1

        #grayscaled = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        img_np = cv2.resize(img_np, (320, 240))
        succ, nparr_enc = cv2.imencode('.jpg', img_np.astype('uint8'))
        frame = nparr_enc.tobytes()

        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

def gen_return_feed(camera):
    yield b'--frame\r\n'
    while True:
        if latest_received_frame[0] is not None:
            yield b'Content-Type: image/jpeg\r\n\r\n' + latest_received_frame[0] + b'\r\n--frame\r\n'
            time.sleep(1)
        else:
            yield b'--frame\r\n'
            time.sleep(1)

@app.route('/video_feed')
def video_feed():
    return Response(gen_video_feed(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/return_feed')
def return_feed():
    return Response(gen_return_feed(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)