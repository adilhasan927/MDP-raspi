import copy
import select
import time
from pathlib import Path
import requests
import jsonpickle
from TSP.tsp import TSP

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

    bt_received_line = None
    if len(poll_out) > 0 and (poll_out[0][1] & select.POLLIN):
        try:
            bt_received_line = bluetooth_file.readline()
            print(bt_received_line)
            if bt_received_line != '':
                print("Bluetooth received: {}".format(bt_received_line))
            else:
                print("Nothing received")
                stm_received_line = None
        except:
            bluetooth_poll_registered = False
            bluetooth_poll.unregister(bluetooth_file)
            bluetooth_poll = select.poll()
            bluetooth_file = None
            print("{} no longer present".format(bluetooth_path))
    
    return bt_received_line

bluetooth_write_queue = []
def handle_blueooth_writes():
    global bluetooth_write_queue
    if bluetooth_file is not None:
        with open(bluetooth_path, 'wb') as f:
            while len(bluetooth_write_queue) > 0:
                try:
                    to_write = bluetooth_write_queue[0]
                    to_write = to_write.encode(encoding='ascii')
                    f.write(to_write)
                    print("Wrote to Bluetooth: {}".format(to_write))
                    bluetooth_write_queue.pop(0)
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

stm_poll = select.poll()
stm_poll_registered = False
stm_path = Path('/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0002-if00-port0')
stm_file = None

def handle_stm_read():
    global stm_poll
    global stm_poll_registered
    global stm_file

    if not stm_poll_registered:
        print("Attempting to set up STM file")
        if stm_path.exists():
            stm_file = open(stm_path, 'r')#open('/dev/rfcomm0')
            stm_poll.register(stm_file)
            stm_poll_registered = True
            print("{} poll set up".format(stm_path))
        else:
            print("{} not present".format(stm_path))
    
    poll_out = stm_poll.poll(0.01)
    #print("stm poll: {}".format(poll_out))
    try:
        print("{} changed? {}".format(stm_path, poll_out[0][1] & select.POLLIN))
    except:
        pass

    stm_received_line = None
    if len(poll_out) > 0 and (poll_out[0][1] & select.POLLIN):
        try:
            stm_received_line = stm_file.readline()
            print(stm_received_line)
            if stm_received_line != '':
                print("stm received: {}".format(bt_received_line))
            else:
                print("Nothing received")
                stm_received_line = None
        except:
            stm_poll_registered = False
            stm_poll.unregister(stm_file)
            stm_poll = select.poll()
            stm_file = None
            print("{} no longer present".format(stm_path))
    
    return stm_received_line

def perform_stm_write(to_write):
    to_write = to_write.encode(encoding='ascii')
    if stm_path.exists():
        with open(stm_path, 'wb') as f:
            f.write(to_write)
    else:
        with open(Path.home() / 'stm_surrogate_out', 'wb') as f:
            f.write(to_write)
    print("Sent command to STM: {}".format(to_write))

def facing_after_turn(facing, turn):
    face_maping_dict = {
        ('N', 'R'): 'E',
        ('W', 'R'): 'S',
        ('S', 'R'): 'W',
        ('E', 'R'): 'N',
        ('N', 'L'): 'W',
        ('W', 'L'): 'N',
        ('S', 'L'): 'E',
        ('E', 'L'): 'S'
    }
    return face_maping_dict[(facing, turn)]

obstacle_positions = dict()
car_location = dict(x=1, y=1, facing='N')
algo_in_control = False
algo_mode = None
algo_solution = None
algo_commands = None
def main_loop():
    global obstacle_positions
    global car_location
    global algo_in_control
    global algo_mode
    global algo_solution
    global algo_commands
    car_new_location = copy.copy(car_location)

    while True:
        bt_received_line = handle_blueooth_read()
        stm_received_line = handle_stm_read()

        to_stm = None
        if bt_received_line is None:
            pass
        elif bt_received_line == 'run\n':
            algo_in_control = True
            algo_mode = 'run'
        elif bt_received_line == 'pathfinding\n':
            algo_in_control = True
            algo_mode = 'pathfinding'
        elif bt_received_line == 'stop\n':
            algo_in_control = False
        elif bt_received_line.startswith('Obstacle'):
            bt_received_line_parsed = bt_received_line.split(': ')
            bt_received_line_parsed = [i.split(',')[0] for i in bt_received_line_parsed]
            bt_received_line_parsed = bt_received_line_parsed[1:]

            id = bt_received_line_parsed[0]
            if len(bt_received_line_parsed) == 3:
                col = int(bt_received_line_parsed[1])
                row = int(bt_received_line_parsed[2])
            else:
                facing = bt_received_line_parsed[1]
            
            if id not in obstacle_positions:
                obstacle_positions[id] = dict()
            obstacle_positions[id]['col'] = col
            obstacle_positions[id]['row'] = row
            obstacle_positions[id]['facing'] = facing
        elif algo_in_control:
            pass
        elif bt_received_line == 'f\n':
            to_stm = 'w8000\n'
            car_new_location['y'] = car_location['y'] + 1
        elif bt_received_line == 'r\n':
            to_stm = 's8000\n'
            car_new_location['y'] = car_location['y'] - 1
        elif bt_received_line == 'sr\n':
            to_stm = 'd9080\n'
            car_new_location['x'] = car_location['x'] + 1
            car_new_location['y'] = car_location['y'] + 2
            car_new_location['facing'] = facing_after_turn(car_location['facing'], 'R')
        elif bt_received_line == 'sl\n':
            to_stm = 'a9080\n'
            car_new_location['x'] = car_location['x'] - 1
            car_new_location['y'] = car_location['y'] + 2
            car_new_location['facing'] = facing_after_turn(car_location['facing'], 'L')

        facing_to_fullname = {
            'N': 'North',
            'S': 'South',
            'E': 'East',
            'W': 'West'
        }

        if algo_in_control and algo_solution is None:
            algo_solution = TSP(
                initPosition=(
                    car_location['x'],
                    car_location['y'],
                    facing_to_fullname[car_location['facing']]
                ),
                dimX=3, dimY=3, turnRad=2.5
            )
            for key, value in obstacle_positions.items():
                x, y, facing = value['x'], value['y'], value['facing']
                algo_solution.addObstacle((x, y, facing))
            algo_success = algo_solution.calcDubins(0.5)

            if not algo_success:
                algo_in_control = False
                print("Path calculation failed")
            else:
                print("Path calculation succeeded")
                algo_commands = algo_solution.generateCommands()
                for segment in algo_commands:
                    segment.append('SEG_END')
                algo_commands = [j for i in algo_commands for j in i]

        if algo_in_control:
            if len(algo_commands) > 0:
                algo_command = algo_commands.pop(0)
                print("Current algo command: {}".format(algo_command))
            else:
                print("Algorithm done executing")
                algo_in_control = False

            end_of_segment_reached = False
            if algo_commands[0] == 'SEG_END':
                algo_commands.pop(0)
                end_of_segment_reached = True

            end_coord = algo_command[-1]
            car_new_location['x'] = end_coord[0]
            car_new_location['y'] = end_coord[1]
            if algo_command[0] == 'R':
                to_stm = 'd{}{}\n'.format(algo_command[1], algo_command[2])
            elif algo_command[0] == 'L':
                to_stm = 'a{}{}\n'.format(algo_command[1], algo_command[2])
            elif algo_command[0] == 'S' and algo_command[1] > 0:
                to_stm = 'w{}\n'.format(algo_command[1])
            elif algo_command[0] == 'S' and algo_command[1] < 0:
                to_stm = 's{}\n'.format(algo_command[1])

        if to_stm is not None:
            perform_stm_write(to_stm)
            #TODO: Wait for STM ACK
            time.sleep(1.0)

        if algo_in_control and end_of_segment_reached:
            print("End of segment reached, performing classification")
            class_detected = perform_classification()
            print("Class detected: {}".format(class_detected))
            algo_in_control = False

        if stm_received_line:
            print("STM !, performing classification")
            class_detected = perform_classification()
            print("Class detected: {}".format(class_detected))

        if bt_received_line is not None or to_stm is not None:
            bluetooth_write_queue.append('ROBOT, {}, {}, {}\n'.format(
                car_new_location['x'],
                car_new_location['y'],
                car_new_location['facing']
            ))
            car_location = car_new_location
            
            if algo_in_control:
                bluetooth_write_queue.append('STATUS, FOLLOWING ALGO\n')
            else:
                bluetooth_write_queue.append('STATUS, READY\n')
        
        handle_blueooth_writes()
        
        print("---")
        
        time.sleep(0.1)

main_loop()
