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

    # load the model
    args = parseArguments()

    config = set_params()
    config['time'] = args.time
    config['sample_rate'] = args.samplerate

    rd.check_arduino(config['port_id'])

    # set up timing
    t0 = time.time()

    # Start all ray objects
    data0 = ss.Data.remote(array_size=[args.time*500*2, config['n_sensors']]) # raw arduino data
    infer_keys = ss.Data.remote() # combined R and L key predictions
    real_keys = ss.Data.remote() # combined R and L keys
    probs0 = ss.Data.remote(array_size=[args.time*500*2, 3])

    # Add arduino data to data0 and data1
    #core count = 1
    sensor0 = ss.arduino_listener.remote(data0, 
                                config['mcu0']['port_id'], 
                                config['mcu0']['baudrate'], 
                                config['mcu0']['n_sensors'],
                                config['sample_rate'],
                                args.time, 
                                t0)


    if args.joint:
        data1 = ss.Data.remote(array_size=[args.time*500*2, config['mcu1']['n_sensors']]) # raw arduino data
        probs1 = ss.Data.remote(array_size=[args.time*500*2, 3])

            #core count = 2
        sensor1 = ss.arduino_listener.remote(data1, 
                                config['mcu1']['port_id'], 
                                config['mcu1']['baudrate'], 
                                config['mcu1']['n_sensors'],
                                config['sample_rate'],
                                args.time, 
                                t0)

        data_agg_width = (config['cmos0']['image_size'][0]*config['cmos0']['image_size'][1]*2)

        data_agg = ss.Data.remote(array_size=
                                    [int(1.5*args.time*config['sample_rate']),
                                    data_agg_width])

        ts_agg = ss.Data.remote(array_size=[args.time*50, 2])

        combined = ss.combine_data_sources.remote(config['sample_rate'], 
                                                args.time,
                                                data_agg,
                                                ts_agg,
                                                t0,
                                                [data0, data1])

        data_to_infer = data_agg

    else:
        data_to_infer = data0


    if args.infer:
        #core count = 3
        i_ = 0
        infer0 = kut.inference_v1.remote(data_to_infer, 
                                    probs0,
                                    infer_keys, 
                                    config, 
                                    t0)

    if args.control:
        config['control'] = True
        kut.key_and_mouse_control_ray.remote(infer_keys, 
                                    config,
                                    t0)

    if args.mouse:
        config['control'] = False
        kut.key_and_mouse_control_ray.remote(infer_keys, 
                                    config,
                                    t0)

    if args.tv:
        kut.control_tv(infer_keys,
                        config,
                        t0)



    print('Firing everything up')

    time.sleep(3)

    
    # Start the big loop
    while time.time() < t0 + args.time:

        # get_time = time.time()
        real_keys_dump, real_keys_ts_dump = ray.get(real_keys.get_keys.remote())
        infer_keys_dump, infer_keys_ts_dump = ray.get(infer_keys.get_keys.remote())
        display_sample_t = time.time() - t0
        display_timestamps.append(display_sample_t)

        real = ''.join(real_keys_dump)
        inferred = ''.join(infer_keys_dump)

        if args.display:

            if len_real < len(real_keys_dump):
                len_real = len(real_keys_dump)
                plot = True

            if len_infer < len(infer_keys_dump):
                len_infer = len(infer_keys_dump)
                plot = True

            if plot:

                if len(real_keys_dump) > config['char_length']:
                    real = real[-config['char_length']:]
                    real_keys_ts_dump_display = real_keys_ts_dump[-config['char_length']:]
                else:
                    real_keys_ts_dump_display = real_keys_ts_dump

                if len(infer_keys_dump) > config['char_length']:
                    inferred = inferred[-config['char_length']:]
                    infer_keys_ts_dump_display = infer_keys_ts_dump[-config['char_length']:]
                else:
                    infer_keys_ts_dump_display = infer_keys_ts_dump

                # plot_time = time.time()
                kut.plot_text(real, real_keys_ts_dump_display, inferred, infer_keys_ts_dump_display, config)
                plot = False
                # print('plot time: ', time.time() - plot_time)

            if cv2.waitKey(5) & 0xFF == 27:
                break

        if time.time() > last_print + 10:
            print('           time: ', round(display_timestamps[-1]), 's  ',
                        ' fr: ', round(1/(display_timestamps[-1] - display_timestamps[-2])))
            last_print = time.time()

        if config['time_between_models'] < time.time() - model_time and args.retrain:

            model_time = time.time()

            print('Dumping data')

            ard_data0, ard_timestamps0 = ray.get(data0.get_data.remote())
            ard_data0 = ard_data0[:len(ard_timestamps0),...]
            

            prob0, prob_ts0 = ray.get(probs0.get_data.remote())
            prob0 = prob0[:len(prob_ts0),...]
            

            save_dic = {}
            save_dic['timestamps_sensor0'] = np.array(ard_timestamps0)
            save_dic['SensorData0'] = ard_data0

            save_dic['keys'] = real_keys_dump
            save_dic['timestamps_keys'] = real_keys_ts_dump
            save_dic['pred_keys_all'] = infer_keys_dump
            save_dic['pred_times_all'] = infer_keys_ts_dump
            save_dic['prob_ts0'] = np.array(prob_ts0)
            save_dic['prob0'] = prob0

            if args.joint:
                ard_data1, ard_timestamps1 = ray.get(data1.get_data.remote())
                ard_data1 = ard_data1[:len(ard_timestamps1),...]
                agg_data, agg_ts = ray.get(data_agg.get_data.remote())
                prob1, prob_ts1 = ray.get(probs1.get_data.remote())
                prob1 = prob1[:len(prob_ts1),...]

                save_dic['timestamps_sensor1'] = np.array(ard_timestamps1)
                save_dic['SensorData1'] = ard_data1
                save_dic['prob_ts1'] = np.array(prob_ts1)
                save_dic['prob1'] = prob1
                save_dic['data_agg'] = agg_data
                save_dic['data_agg_ts'] = np.array(agg_ts)


            save_dic['config'] = config

            filename = dut.set_file_names('_keyboard_inference_v1.pkl')


            with open(config['data_dir'] + filename, 'wb') as f:
                pickle.dump(save_dic, f)

            print('Data saved at ' + config['data_dir'] + filename)

            model_training = train_models_online.remote(config)

            print('Training new model ...')

    ray.shutdown()


if __name__ == '__main__':
    run()