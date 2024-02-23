from picamera import PiCamera
from time import sleep

camera = PiCamera()

camera.start_preview()
camera.capture('/home/pi/code/img.png')
camera.stop_preview()