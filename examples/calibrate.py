"""Calibrate an IDS camera.

The script can be used for calibrating the Radiometric charasteristics of
an IDS camera. It samples the camera at varying exposures.
The images are saved as mat files in a folder named using the serial
number of the camera. The info of the camera is also saved in the same
folder.
"""

import ids
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import scipy.io as sio


EXPOSURE_VALUES = (100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 8000000)
GAIN_VALUES = range(0, 101, 20)
IDS_MAX_PIXEL_CLOCK = 30

class camera(object):
    """Wrapper around the camera driver

    The camera is set to use COLOR_BAYER_8 (RAW) mode.
    """
    
    def __init__(self):
        self._cam = ids.Camera(nummem=1)

        self._cam.auto_white_balance = False
        self._cam.continuous_capture = False
        self._cam.auto_exposure = False
        self._cam.exposure = 100    
        self._cam.color_mode = ids.ids_core.COLOR_BAYER_8
        self._cam.gain_boost = False
        self._cam.gain = 0
        
    @property
    def info(self):
        """Return information about the camera in a form of a dict"""

        return self._cam.info.copy()

    def capture(self, exposure_us, gain=0, gain_boost=False, average=10):
        """Capture a frame
        
        Args:
            exposure_us (int): Exposure period in useconds.
            gain (int): Master gain 0-100.
            gain_boost (bool): Whether to use analog gain boost.
            average (int): Number of frames to average.
            
        Retutns:
           image (array): Capture image (or average of images).
           exposure_ud (float): Actual exposure time (in useconds).
           gain (int): Actual gain.
        """
        
        #
        # Set pixelclock. These values are empiric.
        #
        if exposure_us > 1000:
            #
            # Set pixel rate to minimum to allow long exposure times.
            #
            print("Setting pixel clock to {}.".format(
                self._cam.pixelclock_range[0]))
            self._cam.pixelclock = \
                self._cam.pixelclock_range[0]
        else:
            #
            # Set pixel rate to maximum to allow short exposure times.
            #
            print("Setting pixel clock to {}.".format(IDS_MAX_PIXEL_CLOCK))
            self._cam.pixelclock = IDS_MAX_PIXEL_CLOCK

        #
        # Set frame rate.
        #
        self._cam.framerate = min(100, 1e6 / exposure_us)
        
        self._cam.exposure = exposure_us*1e-3
        self._cam.gain = gain
        self._cam.gain_boost = gain_boost
        
        #
        # Enable the camera and dispose of the first frame.
        #
        self._cam.continuous_capture = True
        try:
            _, _ = self._cam.next()
        
            imgs = []
            for i in range(average):
                img_array, meta_data = self._cam.next()
                imgs.append(img_array)
                
        finally:     
            self._cam.continuous_capture = False
        
        if average > 0:
            img = np.mean(imgs, axis=0)
        else:
            img = np.squeeze(imgs).astype(np.float)
        
        return img, self._cam.exposure * 1e3, self._cam.gain


def main():
    
    cam = camera()
    cam_info = cam.info
    
    base_path = os.path.join('results', cam_info['serial_num'])
    if not os.path.isdir(base_path):
        os.makedirs(base_path)
    
    with open(os.path.join(base_path, 'info.json'), 'w') as f:
        json.dump(cam_info, f)

    for gain_boost in (False, True):
        for gain in GAIN_VALUES:
            for exposure in EXPOSURE_VALUES:
                print("exp_{:07}_gain_{:03}_boost_{}".format(
                    exposure, gain, gain_boost))
                data = cam.capture(exposure_us=exposure, gain=gain, gain_boost=gain_boost)
                base_name = "exp_{:07}_gain_{:03}_boost_{}".format(
                    exposure, gain, gain_boost)
                mat_path = os.path.join(base_path, base_name+'.mat')
                sio.savemat(
                    mat_path,
                    dict(array=data[0], exposure=data[1], gain=data[2]),
                    do_compression=False
                )
                 
    plt.imshow(data[0])
    plt.show()
    

if __name__ == '__main__':
    main()

