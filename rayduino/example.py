'''
Script to record Arduino data alongside keystrokes

Ex:

python online_inference_keyboard.py -t 180 -rd

'''


import numpy as np
import pickle
import pathlib
import time
import ray
import argparse
import getch

import rayduino as rd


def set_params():
    '''
    Set parameters for recording
    '''
    config_ = {}
    config_['port_id'] = '/dev/ttyACM1'
    config_['baudrate'] = 115200
    config_['n_sensors'] = 9            # number of reads in a packet

    return config_


def parseArguments():
    parser = argparse.ArgumentParser(conflict_handler='resolve')
    parser.add_argument('-t', '--time', type=int, default=300, help='time to run')
    parser.add_argument('-s', '--samplerate', type=int, default=100, help='sample rate')
    parser.add_argument('-f', '--filename', type=str, default='data.pkl', help='filepath to store data')

    args = parser.parse_args()
    return args 


@ray.remote
def keyboard_listener(data_, time_to_run_, t0 = time.time()):
    '''
    Record keyboard strokes into remote data structure
    '''
    print('Keyboard recording on')
    while time.time() < t0 + time_to_run_:

        key = getch.getche()
        t = time.time() - t0
        data_.add_keys.remote(key, t)


def run():

    if ray.is_initialized():
        ray.shutdown()
        print('shutting down ray from previous session, reinitializing')
        time.sleep(2)
        print('OK, back online')

    args = parseArguments()

    config = set_params()
    config['time'] = args.time
    config['sample_rate'] = args.samplerate
    config['filename'] = args.filename

    rd.check_arduino(config['port_id'])

    # set up timing
    t0 = time.time()

    # Start all ray objects
    data = rd.Data.remote(array_size=[args.time*500*2, config['n_sensors']]) # raw arduino data
    keys = rd.Data.remote() 

    rd.arduino_listener.remote(data, 
                                config['port_id'], 
                                config['baudrate'], 
                                config['n_sensors'],
                                config['sample_rate'],
                                config['time'], 
                                t0)
                            
    keyboard_listener.remote(keys,
                            config['time'],
                            t0)

    print('Firing everything up')

    while time.time() < t0 + args.time:
        pass

    keys_, keys_ts = ray.get(keys.get_keys.remote()) # get keystrokes

    data_, ard_ts = ray.get(data.get_up_to_last.remote())
            
    save_dic = {}
    save_dic['timestamps_sensor'] = np.array(ard_ts)
    save_dic['sensor'] = data_
    save_dic['keys'] = keys_
    save_dic['timestamps_keys'] = keys_ts
    save_dic['config'] = config

    filename = args.filename

    with open(filename, 'wb') as f:
        pickle.dump(save_dic, f)

    print('Data saved at ' + config['data_dir'] + filename)

    ray.shutdown()


if __name__ == '__main__':
    run()