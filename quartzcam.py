#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 11 09:39:15 2017

@author: microscope
"""

from . import quartz
import time
import numpy as np

class Camera(object):
    def __init__(self):
        self.quartz = quartz.QPOD()
        self.quartz.openconnection()
        self.time_to_show = 300 #s
        self.values = []
        self.timestamps = []
        self.mode = 'Run'
        self.mode_as_index = 0
        self.exposure_ms = 0
        self.binning = 1
        self.sensor_dimensions = (512,512)
        self.readout_area = self.sensor_dimensions
        self.binning_values = [1]
        self.frame_number = 0
        self.starttime = time.time()
        self.thickness = self.quartz.readthickness()
        self.rate = 0
        self.zero_thickness = self.thickness
        self.update_info_function = None
        
    @property
    def density(self):
        return self.quartz.density
    
    @density.setter
    def density(self, density):
        self.quartz.density = density
        
    @property
    def z_ratio(self):
        return self.quartz.z_ratio
    
    @z_ratio.setter
    def z_ratio(self, z_ratio):
        self.quartz.z_ratio = z_ratio
        
    def set_exposure_ms(self, exposure_ms, mode_id):
        self.exposure_ms = exposure_ms

    def get_exposure_ms(self, mode_id):
        return self.exposure_ms

    def set_binning(self, binning, mode_id):
        self.binning = binning

    def get_binning(self, mode_id):
        return self.binning

    def get_expected_dimensions(self, binning):
        return self.sensor_dimensions
    
    def start_live(self):
#        self.starttime = time.time()
#        self.values = []
#        self.timestamps = []
#        self.set_zero()
        pass
    
    def stop_live(self):
        pass
        
    def acquire_image(self):
        data_element = {}
        data_element['properties'] = {}
        self.thickness, frequency = self.quartz.readthickness(return_freq=True)
        now = time.time()
        self.values.append(self.thickness - self.zero_thickness)
        self.timestamps.append(now)
        if len(self.values) > 2:
            self.rate = (self.values[-1] - self.values[-2]) / (self.timestamps[-1] - self.timestamps[-2])
        
        if callable(self.update_info_function):
            self.update_info_function(self.values[-1], self.rate, frequency)
            
        if self.time_to_show > 0 and self.timestamps[0] < now - self.time_to_show:
            start_index = np.argmin(np.abs(np.array(self.timestamps) - (now - self.time_to_show)))
        else:
            start_index = 0
        data_element['data'] = np.array(self.values[start_index:], dtype=np.float32)
        spatial_calibration = [{'offset': self.timestamps[start_index] - self.starttime, 'scale': (now - self.timestamps[start_index]) / len(data_element['data']), 'units': 's'}]
        intenstiy_calibration = {'offset': 0, 'scale': 1, 'units': 'Angstrom'}
        data_element['properties']['spatial_calibrations'] = spatial_calibration
        data_element['properties']['intensity_calibration'] = intenstiy_calibration
        data_element['properties']['frame_number'] = self.frame_number
        self.frame_number += 1
        time.sleep(1)
        
        return data_element
        
    def set_zero(self):
        self.zero_thickness = self.thickness
        
    def close(self):
        self.quartz.closeconnection()
        
class QuartzControllerPanelDelegate(object):

    def __init__(self, api):
        self.__api = api
        self.panel_id = 'QuartzController-Panel'
        self.panel_name = 'QuartzController'
        self.panel_positions = ['left', 'right']
        self.panel_position = 'right'
        self.quartzcam = None
        
    @property
    def quartzcam_data_item(self):
        return self.__api.get_data_item_for_hardware_source('quartzcam')

    def close(self):
        pass

    def create_panel_widget(self, ui, document_controller):
        self.quartzcam = self.__api.get_hardware_source_by_id('quartzcam', '1')._hardware_source._CameraHardwareSource__camera_adapter.camera
        
        def zero_button_clicked():
            self.quartzcam.set_zero()

        def z_ratio_finished(text):
            if len(text) > 0:
                try:
                    z_ratio = float(text)
                except ValueError:
                    pass
                else:
                    self.quartzcam.z_ratio = z_ratio
                    
            z_ratio_field.text = '{:.2f}'.format(self.quartzcam.z_ratio)

        def density_finished(text):
            if len(text) > 0:
                try:
                    density = float(text)
                except ValueError:
                    pass
                else:
                    self.quartzcam.density = density
            
            density_field.text = '{:.2f}'.format(self.quartzcam.density)

        def time_finished(text):
            if len(text) > 0:
                try:
                    time_to_show = float(text)
                except ValueError:
                    pass
                else:
                    self.quartzcam.time_to_show = time_to_show
            
            time_field.text = '{:.0f}'.format(self.quartzcam.time_to_show)
            
        def update_info_labels(thickness, rate, frequency):
            def update_labels():
                thickness_label.text = '{:.2f}'.format(thickness)
                rate_label.text = '{:.1f}'.format(rate)
                frequency_label.text = '{:.1f}'.format(frequency*1e6)
                
            self.__api.queue_task(update_labels)

        column = ui.create_column_widget()
        
        time_row = ui.create_row_widget()
        time_row.add_spacing(5)
        time_row.add(ui.create_label_widget('Time to show: '))
        time_field = ui.create_line_edit_widget()
        time_field.on_editing_finished = time_finished
        time_row.add(time_field)
        time_row.add_spacing(10)
        zero_button = ui.create_push_button_widget('Zero')
        zero_button.on_clicked = zero_button_clicked
        time_row.add(zero_button)
        time_row.add_spacing(5)
        time_row.add_stretch()
        
        parameters_row = ui.create_row_widget()
        parameters_row.add_spacing(5)
        parameters_row.add(ui.create_label_widget('Density (g/cm³): '))
        density_field = ui.create_line_edit_widget()
        density_field.on_editing_finished = density_finished
        parameters_row.add(density_field)
        parameters_row.add_spacing(10)
        parameters_row.add(ui.create_label_widget('Z-ratio: '))
        z_ratio_field = ui.create_line_edit_widget()
        z_ratio_field.on_editing_finished = z_ratio_finished
        parameters_row.add(z_ratio_field)
        parameters_row.add_spacing(5)
        parameters_row.add_stretch()
        
        info_row = ui.create_row_widget()
        info_row.add_spacing(5)
        info_row.add(ui.create_label_widget('Thickness: '))
        thickness_label = ui.create_label_widget('--')
        info_row.add(thickness_label)
        info_row.add(ui.create_label_widget(' A'))
        info_row.add_spacing(10)
        info_row.add(ui.create_label_widget('Rate: '))
        rate_label = ui.create_label_widget('--')
        info_row.add(rate_label)
        info_row.add(ui.create_label_widget(' A/s'))
        info_row.add_spacing(5)
        info_row.add_stretch()
        
        frequency_row = ui.create_row_widget()
        frequency_row.add_spacing(5)
        frequency_row.add(ui.create_label_widget('Frequency: '))
        frequency_label = ui.create_label_widget('--')
        frequency_row.add(frequency_label)
        frequency_row.add(ui.create_label_widget(' Hz'))
        frequency_row.add_spacing(5)
        frequency_row.add_stretch()
        
        column.add_spacing(5)
        column.add(time_row)
        column.add_spacing(5)
        column.add(parameters_row)
        column.add_spacing(5)
        column.add(info_row)
        column.add_spacing(5)
        column.add(frequency_row)
        column.add_spacing(5)
        column.add_stretch()
        
        density_finished('')
        z_ratio_finished('')
        time_finished('')
        
        self.quartzcam.update_info_function = update_info_labels

        return column


class QuartzControllerExtension(object):
    extension_id = 'univie.quartzcontroller'

    def __init__(self, api_broker):
        api = api_broker.get_api(version='1', ui_version='1')
        self.__panel_ref = api.create_panel(QuartzControllerPanelDelegate(api))

    def close(self):
        self.__panel_ref.close()
        self.__panel_ref = None