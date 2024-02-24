import select
import time
from pathlib import Path
import requests
import jsonpickle

bluetooth_poll = select.poll()
bluetooth_poll_registered = False
bluetooth_path = Path('/dev/rfcomm0')
bluetooth_file = None
out_path = bluetooth_path

stm_poll = select.poll()
stm_poll_registered = False
stm_path = Path('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0002-if00-port0')
stm_file = None

mapping_dict = {
    'Bullseye': 'bullseye',
    'id11': 'one',
    'id12': 'two',
    'id13': 'three',
    'id14': 'four',
    'id15': 'five',
    'id16': 'six',
    'id17': 'seven',
    'id18': 'eight',
    'id19': 'nine',
    'id20': 'letter_a',
    'id21': 'letter_b',
    'id22': 'letter_c',
    'id23': 'letter_d',
    'id24': 'letter_e',
    'id25': 'letter_f',
    'id26': 'letter_g',
    'id27': 'letter_h',
    'id28': 'letter_s',
    'id29': 'letter_t',
    'id30': 'letter_u',
    'id31': 'letter_v',
    'id32': 'letter_w',
    'id33': 'letter_x',
    'id34': 'letter_y',
    'id35': 'letter_z',
    'id36': '',
    'id37': 'down_arrow',
    'id38': 'up_arrow',
    'id39': 'right_arrow',
    'id40': 'left_arrow'
}

while True:
    take_image_this_loop = False
    send_stm_this_loop = False
    stm_command = None

    if not bluetooth_poll_registered:
        if bluetooth_path.exists():
            bluetooth_file = open(bluetooth_path)#open('/dev/rfcomm0')
            bluetooth_poll.register(bluetooth_file)
            bluetooth_poll_registered = True
            print("Bluetooth connected")

    if not stm_poll_registered:
        if stm_path.exists():
            stm_file = open(stm_path)
            stm_poll.register(stm_file)
            stm_poll_registered = True

    poll_out = bluetooth_poll.poll(0.01)
    print("Bluetooth poll", poll_out)
    try:
        print(poll_out[0][1] & select.POLLIN)
    except:
        pass
    if len(poll_out) > 0 and (poll_out[0][1] & select.POLLIN):
        try:
            received_line = bluetooth_file.read()
            print("Bluetooth received")
        except:
            bluetooth_poll_registered = False
            print("Bluetooth disconnected")
            continue
        if received_line != '':
            print("Bluetooth received: {}".format(received_line))
            take_image_this_loop = True
        if received_line.startswith('f'):
            stm_command = 'w'

    if take_image_this_loop:
        print("Taking image with camera and sending for classification")
        res = requests.get(url='http://localhost:5000/do_classification')
        model_out = jsonpickle.decode(res.content)
        if len(model_out['cls']) == 0:
            detected_class = 'None'
        else:
            detected_class = mapping_dict[model_out['names'][str(int(model_out['cls'][0]))]]
        print("First class detected: {}", detected_class)
        #with open(out_path, 'w') as f:
        #    f.write("TARGET, 0, {}".format(detected_class))
    
    take_image_this_loop = False
    
    #continue
    
    poll_out = stm_poll.poll(0.01)
    print("STM poll", poll_out)
    try:
        print(poll_out[0][1] & select.POLLIN)
    except:
        pass
    if len(poll_out) > 0 and (poll_out[0][1] & select.POLLIN):
        try:
            #received_line = stm_file.read(1) + '\n'
            received_line = stm_file.readline()
        except:
            stm_poll_registered = False
            continue
        if received_line != '':
            print("STM received: {}".format(received_line))

    #send_stm_this_loop = False
    send_stm_this_loop = True
    stm_command = 'w8000'
    #stm_command = 'a8090'
    if send_stm_this_loop and stm_poll_registered:
        with open(stm_path, 'wb') as f:
            f.write(b'w\n')
#            f.write(b'{}\n'.format(stm_command))
    
    time.sleep(0.05)