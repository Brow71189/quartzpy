#MIT License
#
#Copyright (c) 2017 Andreas Mittelberger
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

# standard libraries
try:
    from nion.swift.model import HardwareSource
    from Camera import CameraHardwareSource
except:
    pass
from . import quartzcam
from . import QuartzCameraManagerImageSource


def register_camera(hardware_source_id, display_name):
    # create the camera
    camera = quartzcam.Camera()
    #camera_map[hardware_source_id] = camera
    # create the hardware source
    camera_adapter = QuartzCameraManagerImageSource.CameraAdapter(hardware_source_id, display_name, camera)
    hardware_source = CameraHardwareSource.CameraHardwareSource(camera_adapter, None)
    hardware_source.modes = camera_adapter.modes
    # register it with the manager
    HardwareSource.HardwareSourceManager().register_hardware_source(hardware_source)
                
register_camera('quartzcam', 'QPod')