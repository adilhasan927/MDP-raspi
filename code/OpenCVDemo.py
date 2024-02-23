#!/usr/bin/env python

"""
Note: Code taken from https://blog.miguelgrinberg.com/post/video-streaming-with-flask, then modified.
"""

import io
from flask import Flask, render_template_string, Response
from picamera import PiCamera
from CameraLibraryCode import Camera
import numpy as np
import cv2
import random as rng

rng.seed(42)

app = Flask(__name__)

@app.route('/video_streaming_demo')
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
        <div>
            <h1>Cropped bounding box</h1>
            <img src="{{ url_for('cropped_video_feed') }}">
        </div>
        <div>
            <h1>OpenCV Output</h1>
            <img src="{{ url_for('debug_video_feed') }}">
        </div>
        </body>
</html>"""
    return render_template_string(template)

def gen_video_feed(camera):
    """Video streaming generator function."""
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

latest_opencv_crop = [None]

def gen_cropped_video_feed(camera):
    """Video streaming generator function."""
    yield b'--frame\r\n'
    while True:
        if latest_opencv_crop[0] is None:
            yield b'--frame\r\n'
        else:
            cropped = latest_opencv_crop[0]

            #grayscaled = -cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY) + 255

            hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)
            saturation = hsv[:,:,[2]]

            thresholded = np.where(saturation > 64, saturation, 0)
            
            contours, hierarchy = cv2.findContours(thresholded, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:
                c = max(contours, key = cv2.contourArea)
                x,y,w,h = cv2.boundingRect(c)

                padding = 24
                x = x - padding
                y = y - padding
                w = w + padding*2
                h = h + padding*2

                pts1 = np.float32([[x, y], [x, y+h],
                                [x+w, y], [x+w, y+h]])                
                pts2 = np.float32([[0, 0], [0, 240],
                                [224, 0], [224, 240]])
                
                # Apply Perspective Transform Algorithm
                matrix = cv2.getPerspectiveTransform(pts1, pts2)
                cropped_again = cv2.warpPerspective(cropped, matrix, (224, 240))
                
                drawing = cv2.cvtColor(thresholded, cv2.COLOR_GRAY2RGB)
                cv2.drawContours(drawing, contours, -1, (0,255,0), 3)
            else:
                drawing = cv2.cvtColor(thresholded, cv2.COLOR_GRAY2RGB)
                cropped_again = cropped

            concatted = cv2.hconcat([cropped,
                                     cv2.cvtColor(saturation, cv2.COLOR_GRAY2RGB),
                                     cv2.cvtColor(thresholded, cv2.COLOR_GRAY2RGB),
                                     drawing,
                                     cropped_again])

            succ, nparr_enc = cv2.imencode('.jpg', concatted.astype('uint8'))
            frame = nparr_enc.tobytes()

            yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

def gen_debug_video_feed(camera):
    """Video streaming generator function."""
    yield b'--frame\r\n'
    while True:
        frame = camera.get_frame()

        # CV2 starts here
        nparr = np.frombuffer(frame, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # cv2.IMREAD_COLOR in OpenCV 3.1

        grayscaled = -cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY) + 255
        #blurred = cv2.blur(grayscaled, (3, 3))
        #succ, thresholded = cv2.threshold(grayscaled, 200, 255, cv2.THRESH_BINARY)

        thresholded = np.where(grayscaled > 200, grayscaled, 0)
        
        canny = cv2.Canny(thresholded, 255/3, 255, 30)
        #mask = canny != 0
        #dst = src * (mask[:,:,None].astype(src.dtype))

        element = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11), (-1, -1))
        dilated = cv2.dilate(canny, element)
        dilated = cv2.copyMakeBorder(dilated[10:-10,10:-10], 10, 10, 10, 10, cv2.BORDER_CONSTANT, None, 255)

        dilated_inv = dilated == 0
        numLabels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated_inv.astype('uint8'), 4)
        labels = labels.astype('uint8')

        areas = stats[:,cv2.CC_STAT_AREA]
        area_sort = np.argsort(areas)[::-1]

        drawing = np.zeros((dilated.shape[0], dilated.shape[1]), dtype=np.uint8)
        if len(area_sort) > 0:
            drawing = np.where(labels == area_sort[1], 255, 0).astype('uint8')

        contours, hierarchy = cv2.findContours(drawing, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            c = max(contours, key = cv2.contourArea)
            x,y,w,h = cv2.boundingRect(c)

            pts1 = np.float32([[x, y], [x, y+h],
                            [x+w, y], [x+w, y+h]])
            pts2 = np.float32([[0, 0], [0, 512],
                            [256, 0], [256, 512]])
            
            # Apply Perspective Transform Algorithm
            matrix = cv2.getPerspectiveTransform(pts1, pts2)
            cropped = cv2.warpPerspective(img_np, matrix, (256, 512))[16:256,16:-16]

            latest_opencv_crop[0] = cropped
        else:
            latest_opencv_crop[0] = None

        #contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        #closed_contours = [contour for contour in contours if cv2.isContourConvex(contour)]
        #contour_areas = [cv2.contourArea(contour) for contour in contours]
        #area_sort = np.argsort(contour_areas)[::-1]
        
        #drawing = np.zeros((dilated.shape[0], dilated.shape[1]), dtype=np.uint8)
        #for idx in area_sort[1:3]:
        #    cv2.drawContours(drawing, contours, idx, 255, 1)

        #bboxes = [cv2.boundingRect(i) for i in closed_contours]

        #for contour, bbox in zip(closed_contours, bboxes):
        #    color = (rng.randint(0,256), rng.randint(0,256), rng.randint(0,256))
        #    cv2.drawContours(drawing, [contour], 0, color)
        #    cv2.rectangle(drawing,
        #                  (int(bbox[0]), int(bbox[1])), 
        #                  (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])),
        #                  color, 2)

        #concatted = cv2.vconcat([
        #    cv2.hconcat([grayscaled, thresholded]),
        #    cv2.hconcat([dilated, drawing])])
        concatted = drawing
        
        succ, nparr_enc = cv2.imencode('.jpg', concatted.astype('uint8'))
        frame = nparr_enc.tobytes()
        # CV2 ends here

        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n--frame\r\n'

@app.route('/video_feed')
def video_feed():
    return Response(gen_video_feed(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cropped_video_feed')
def cropped_video_feed():
    return Response(gen_cropped_video_feed(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/debug_video_feed')
def debug_video_feed():
    return Response(gen_debug_video_feed(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)