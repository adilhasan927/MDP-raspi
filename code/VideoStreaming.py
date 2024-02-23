#!/usr/bin/env python

"""
Note: Code taken from https://blog.miguelgrinberg.com/post/video-streaming-with-flask, then modified.
"""

import io
from flask import Flask, render_template_string, Response
from picamera import PiCamera
from CameraLibraryCode import Camera

app = Flask(__name__)

@app.route('/video_streaming_demo')
def index():
    template = """<html>
<head>
    <title>RPi Camera</title>
  </head>
  <body>
    <h1>RPi Camera</h1>
    <img src="{{ url_for('video_feed') }}">
  </body>
</html>"""
    return render_template_string(template)

def gen(camera):
    """Video streaming generator function."""
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@app.route('/video_feed')
def video_feed():
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)