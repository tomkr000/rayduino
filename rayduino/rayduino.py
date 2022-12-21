import time
import numpy as np
import pandas as pd
import pyautogui, sys
import serial
import serial.tools.list_ports
import ray
import os
from urllib.request import urlopen
import traceback
import cv2
import matplotlib.pyplot as plt


def get_mcu_serial(port_id_):
    '''
    obtain the serial number of the MCU using the port number
    need to obtain the port number from Arduino UI
    '''
    a=serial.tools.list_ports.comports()
    for w in a:
        if w.device == port_id_:
            return w.serial_number
        else:
            return None

            
def check_arduino(correct_port):
    for p in serial.tools.list_ports.comports():
        if p.device == correct_port:
            return True
    raise Exception("Port not found")


def serial_split(serial_string_):
    '''
    Split the incoming data into ints
    '''
    return [float(x) for x in serial_string_.split(',')]


def get_arduino_data(arduino_, expected_len=9):
    '''
    Reads data from arduino and returns a list of the values.
    Checks if the correct number of values are returned.
    Returns error if incorrect number of values are returned.
    
    Args:
        arduino_ (serial.Serial): serial connection to arduino
        expected_len (int): expected number of values to be returned
        
    Returns:
        data_: list of correct serial values from arduino
    '''
    
    b =arduino_.read_until(b'\n')
    string_n = b.decode()  # decode byte string into Unicode
    string = string_n.rstrip() # remove \n and \r
    try:
        data_ = serial_split(string)
        assert len(data_) == expected_len, 'Serial collection failed'
        return data_
    except:
        print('Serial collection failed')
        return np.array([])


@ray.remote
def arduino_listener(data_, 
                        port_id, 
                        baudrate, 
                        n_sensors,
                        sample_rate_, 
                        time_to_run, 
                        t0):
    '''
    read arduino output on this loop
    '''
    check_arduino(port_id)

    print("Aquiring Streamed Data")
    arduino = serial.Serial(port=port_id, 
                            baudrate=baudrate, 
                            timeout=None)

    time.sleep(2)

    last = 0

    while time.time() - t0 < time_to_run:
        try:
            timestamp_ = time.time() - t0
            sensorVal_ = get_arduino_data(arduino, n_sensors)
            if timestamp_ > last + 1/sample_rate_:
                last = timestamp_
                data_.add_data.remote(np.array(sensorVal_), timestamp_)
                sensorVal_ = get_arduino_data(arduino, n_sensors) # clear the buffer

        except Exception:
            print(traceback.format_exc())


##################################################################################
############################ DATA MANAGEMENT #####################################
##################################################################################


@ray.remote
class Data(object):
    ''''
    remote object to store arduino data, keystrokes, or anything else
    '''
    def __init__(self, array_size=[], dtype='float64'):
        self.array_size = array_size
        self.data = np.array(np.zeros(self.array_size)).astype(dtype)
        self.timestamps = []
        self.keys = []
        print('data init of size ',str(array_size), ' at time ',time.time())

    def get_data(self):
        return self.data, self.timestamps

    def get_last(self):
        return self.data[len(self.timestamps)-1,...], self.timestamps[-1]

    def get_up_to_last(self):
        return self.data[:len(self.timestamps),...], self.timestamps

    def get_window_last(self, window):
        if len(self.timestamps) > window:
            return self.data[len(self.timestamps)-window:len(self.timestamps),...], self.timestamps[-window:]
        else:
            return np.array([]), []

    def add_data(self, data_, timestamps_):
        self.timestamps.append(timestamps_)
        self.data[len(self.timestamps)-1, ...] = data_

    def get_keys(self):
        return self.keys, self.timestamps

    def add_keys(self, keys_, timestamps_):
        self.timestamps.append(timestamps_)
        self.keys.append(keys_)


@ray.remote
def combine_data_sources(sample_rate, 
                                time_to_run,
                                data_,
                                ts_,
                                t0,
                                datas):

    sample_t = 0
    last = time.time()
    print('Combining data')

    while sample_t < time_to_run:

        if time.time() - last > 1/sample_rate:
            
            last = time.time()
            sample_t = time.time() - t0
            sample = np.array([])
            tss = []
            n_good = 0
            try:
                for d_source in datas:
                    dat, ts = ray.get(d_source.get_last.remote())
                    if ts:

                        tss.append(ts)

                        if sample.size == 0:
                            sample = np.array(dat)
                        else:
                            sample = np.hstack([sample, dat])
                        n_good += 1

                if n_good == len(datas):
                    
                    data_.add_data.remote(sample, sample_t)
                    ts_.add_data.remote(np.array(tss), sample_t)
                    

            except Exception:
                print(traceback.format_exc())