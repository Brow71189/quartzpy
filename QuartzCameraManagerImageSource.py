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
import copy
import gettext
import logging

# types
from typing import Any, List

# third party libraries
import numpy

# local libraries
from nion.swift.model import HardwareSource

_ = gettext.gettext

AUTOSTEM_CONTROLLER_ID = "autostem_controller"


class CameraFrameParameters(object):

    def __init__(self, d=None):
        d = d or dict()
        self.exposure_ms = d.get("exposure_ms", 125)
        self.binning = d.get("binning", 1)

    def as_dict(self):
        return {
            "exposure_ms": self.exposure_ms,
            "binning": self.binning,
        }


class CameraAcquisitionTask:

    def __init__(self, hardware_source_id, is_continuous: bool, camera, frame_parameters, display_name):
        self.hardware_source_id = hardware_source_id
        self.is_continuous = is_continuous
        self.__camera = camera
        self.__display_name = display_name
        self.__frame_parameters = None
        self.__pending_frame_parameters = copy.copy(frame_parameters)

    def set_frame_parameters(self, frame_parameters):
        self.__pending_frame_parameters = copy.copy(frame_parameters)

    @property
    def frame_parameters(self):
        return self.__pending_frame_parameters or self.__frame_parameters

    def start_acquisition(self) -> bool:
        self.resume_acquisition()
        return True

    def suspend_acquisition(self) -> None:
        pass

    def resume_acquisition(self) -> None:
        self.__activate_frame_parameters()
        self.__camera.start_live()

    def mark_acquisition(self) -> None:
        self.stop_acquisition()

    def stop_acquisition(self) -> None:
        self.__camera.stop_live()

    def acquire_data_elements(self):
        if self.__pending_frame_parameters:
            self.__activate_frame_parameters()
        assert self.__frame_parameters is not None
        frame_parameters = self.__frame_parameters
        exposure_ms = frame_parameters.exposure_ms
        binning = frame_parameters.binning
        data_element = self.__camera.acquire_image()
        #sub_area = (0, 0), data_element["data"].shape
        data_element["version"] = 1
        #data_element["sub_area"] = sub_area
        data_element["state"] = "complete"
        # add optional calibration properties
        if "spatial_calibrations" in data_element["properties"]:
            data_element["spatial_calibrations"] = data_element["properties"]["spatial_calibrations"]
        else:  # handle backwards compatible case for nionccd1010
            data_element["spatial_calibrations"] = self.__camera.calibration
        if "intensity_calibration" in data_element["properties"]:
            data_element["intensity_calibration"] = data_element["properties"]["intensity_calibration"]
        # grab metadata from the autostem
        autostem = HardwareSource.HardwareSourceManager().get_instrument_by_id(AUTOSTEM_CONTROLLER_ID)
        if autostem:
            try:
                autostem_properties = autostem.get_autostem_properties()
                data_element["properties"]["autostem"] = copy.copy(autostem_properties)
                # TODO: file format: remove extra_high_tension
                high_tension_v = autostem_properties.get("high_tension_v")
                if high_tension_v:
                    data_element["properties"]["extra_high_tension"] = high_tension_v
            except Exception as e:
                print(e)

        data_element["properties"]["hardware_source_name"] = self.__display_name
        data_element["properties"]["hardware_source_id"] = self.hardware_source_id
        data_element["properties"]["exposure"] = exposure_ms / 1000.0
        data_element["properties"]["binning"] = binning
        #data_element["properties"]["valid_rows"] = sub_area[0][0] + sub_area[1][0]
        data_element["properties"]["frame_index"] = data_element["properties"]["frame_number"]
        return [data_element]

    def __activate_frame_parameters(self):
        self.__frame_parameters = self.frame_parameters
        self.__pending_frame_parameters = None
        mode_id = self.__camera.mode
        self.__camera.set_exposure_ms(self.__frame_parameters.exposure_ms, mode_id)
        self.__camera.set_binning(self.__frame_parameters.binning, mode_id)


class CameraAdapter:

    def __init__(self, hardware_source_id, display_name, camera):
        self.hardware_source_id = hardware_source_id
        self.display_name = display_name
        self.camera = camera
        self.binning_values = camera.binning_values
        self.modes = ["Run", "Tune", "Snap"]
        self.features = dict()
        self.features["is_nion_camera"] = False
        self.features["has_monitor"] = False
        self.processor = None
        self.on_selected_profile_index_changed = None
        self.on_profile_frame_parameters_changed = None

        def low_level_parameter_changed(parameter_name):
            profile_index = self.camera.mode_as_index
            if parameter_name == "exposureTimems" or parameter_name == "binning":
                if callable(self.on_profile_frame_parameters_changed):
                    mode_id = self.camera.mode
                    exposure_ms = self.camera.get_exposure_ms(mode_id)
                    binning = self.camera.get_binning(mode_id)
                    frame_parameters = CameraFrameParameters({"exposure_ms": exposure_ms, "binning": binning})
                    self.on_profile_frame_parameters_changed(profile_index, frame_parameters)
            elif parameter_name == "mode":
                if callable(self.on_selected_profile_index_changed):
                    self.on_selected_profile_index_changed(profile_index)

        self.camera.on_low_level_parameter_changed = low_level_parameter_changed

    def close(self):
        # unlisten for events from the image panel
        self.camera.on_low_level_parameter_changed = None
        self.camera.close()

    def get_initial_profiles(self) -> List[Any]:
        #profiles = list()
        # copy the frame parameters from the camera object to self.__profiles
        def get_frame_parameters(profile_index):
            mode_id = self.modes[profile_index]
            exposure_ms = self.camera.get_exposure_ms(mode_id)
            binning = self.camera.get_binning(mode_id)
            return CameraFrameParameters({"exposure_ms": exposure_ms, "binning": binning})
        return [get_frame_parameters(i) for i in range(3)]

    def get_initial_profile_index(self) -> int:
        return self.camera.mode_as_index

    def set_selected_profile_index(self, profile_index: int) -> None:
        mode_id = self.modes[profile_index]
        self.camera.mode = mode_id

    def set_profile_frame_parameters(self, profile_index: int, frame_parameters: CameraFrameParameters) -> None:
        mode_id = self.modes[profile_index]
        self.camera.set_exposure_ms(frame_parameters.exposure_ms, mode_id)
        self.camera.set_binning(frame_parameters.binning, mode_id)

    @property
    def sensor_dimensions(self):
        return self.camera.sensor_dimensions

    @property
    def readout_area(self):
        return self.camera.readout_area

    @readout_area.setter
    def readout_area(self, readout_area_TLBR):
        self.camera.readout_area = readout_area_TLBR

    def get_expected_dimensions(self, binning):
        return self.camera.get_expected_dimensions(binning)

    def create_acquisition_task(self, frame_parameters):
        acquisition_task = CameraAcquisitionTask(self.hardware_source_id, True, self.camera, frame_parameters, self.display_name)
        return acquisition_task

    def create_record_task(self, frame_parameters):
        record_task = CameraAcquisitionTask(self.hardware_source_id, False, self.camera, frame_parameters, self.display_name)
        return record_task

    def acquire_sequence(self, frame_parameters, n: int):
        mode_id = self.camera.mode
        self.camera.set_exposure_ms(frame_parameters.exposure_ms, mode_id)
        self.camera.set_binning(frame_parameters.binning, mode_id)
        return self.camera.acquire_sequence(n)

    def open_configuration_interface(self):
        self.camera.show_config_window()

    def open_monitor(self):
        self.camera.start_monitor()

    def get_frame_parameters_from_dict(self, d):
        return CameraFrameParameters(d)

    def get_property(self, name):
        return getattr(self.camera, name)

    def set_property(self, name, value):
        setattr(self.camera, name, value)

    def shift_click(self, mouse_position, camera_shape):
        autostem = HardwareSource.HardwareSourceManager().get_instrument_by_id(AUTOSTEM_CONTROLLER_ID)
        if autostem:
            radians_per_pixel = autostem.get_value("TVPixelAngle")
            defocus_value = autostem.get_value("C10")  # get the defocus
            dx = radians_per_pixel * defocus_value * (mouse_position[1] - (camera_shape[1] / 2))
            dy = radians_per_pixel * defocus_value * (mouse_position[0] - (camera_shape[0] / 2))
            logging.info("Shifting (%s,%s) um.\n", dx * 1e6, dy * 1e6)
            autostem.set_value("SShft.x", autostem.get_value("SShft.x") - dx)
            autostem.set_value("SShft.y", autostem.get_value("SShft.y") - dy)

    def tilt_click(self, mouse_position, camera_shape):
        autostem = HardwareSource.HardwareSourceManager().get_instrument_by_id(AUTOSTEM_CONTROLLER_ID)
        if autostem:
            defocus_sign = numpy.sign(autostem.get_value("C10"))  # get the defocus
            radians_per_pixel = autostem.get_value("TVPixelAngle")
            da = radians_per_pixel * (mouse_position[1] - (camera_shape[1] / 2))
            db = radians_per_pixel * (mouse_position[0] - (camera_shape[0] / 2))
            logging.info("Tilting (%s,%s) rad.\n", da, db)
            autostem.set_value("STilt.x", autostem.get_value("STilt.x") - defocus_sign * da)
            autostem.set_value("STilt.y", autostem.get_value("STilt.y") - defocus_sign * db)
