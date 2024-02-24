import select
import time
from pathlib import Path
import requests
import jsonpickle

bluetooth_poll = select.poll()
bluetooth_poll_registered = False
bluetooth_path = Path('/dev/rfcomm0')
bluetooth_file = None
    
def handle_blueooth_read():
    global bluetooth_poll
    global bluetooth_poll_registered
    global bluetooth_file

    if not bluetooth_poll_registered:
        print("Attempting to set up bluetooth")
        if bluetooth_path.exists():
            bluetooth_file = open(bluetooth_path, 'r')#open('/dev/rfcomm0')
            bluetooth_poll.register(bluetooth_file)
            bluetooth_poll_registered = True
            print("{} poll set up".format(bluetooth_path))
        else:
            print("{} not present".format(bluetooth_path))
    
    poll_out = bluetooth_poll.poll(0.01)
    #print("Bluetooth poll: {}".format(poll_out))
    try:
        print("{} changed? {}".format(bluetooth_path, poll_out[0][1] & select.POLLIN))
    except:
        pass

    received_line = None
    if len(poll_out) > 0 and (poll_out[0][1] & select.POLLIN):
        try:
            received_line = bluetooth_file.readline()
            print(received_line)
            if received_line != '':
                print("Bluetooth received: {}".format(received_line))
            else:
                print("Nothing received")
        except:
            bluetooth_poll_registered = False
            bluetooth_poll.unregister(bluetooth_file)
            bluetooth_poll = select.poll()
            bluetooth_file = None
            print("{} no longer present".format(bluetooth_path))
    
    return received_line

bluetooth_write_queue = []
def handle_blueooth_writes():
    global bluetooth_write_queue
    if bluetooth_file is not None:
        with open(bluetooth_path, 'wb') as f:
            while len(bluetooth_write_queue) > 0:
                try:
                    to_write = bluetooth_write_queue.pop(0)
                    f.write(to_write.encode(encoding='ascii'))
                except:
                    return False
    return True

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
def perform_classification():
    print("Taking image with camera and sending for classification")
    res = requests.get(url='http://localhost:5000/do_classification')
    model_out = jsonpickle.decode(res.content)
    if len(model_out['cls']) == 0:
        detected_class = 'None'
    else:
        detected_class = mapping_dict[model_out['names'][str(int(model_out['cls'][0]))]]
    print("First class detected: {}", detected_class)
    return detected_class

#stm_poll = select.poll()
#stm_poll_registered = False
stm_path = Path('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0002-if00-port0')
#stm_file = None
def perform_stm_write(to_write):
    to_write = to_write.encode(encoding='ascii')
    if stm_path.exists():
        with open(stm_path, 'wb') as f:
            f.write(to_write)
    else:
        with open(Path.home() / 'stm_surrogate_out', 'wb') as f:
            f.write(to_write)
    print("Sent command to STM: {}".format(to_write))

def main_loop():
    while True:
        received_line = handle_blueooth_read()

        to_stm = None
        if received_line == 'f\n':
            to_stm = 'w8000\n'

        if to_stm is not None:
            perform_stm_write(to_stm)

        handle_blueooth_writes()
        
        print("---")
        
        time.sleep(1.0)

main_loop()