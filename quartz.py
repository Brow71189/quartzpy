#!/usr/bin/python

import sys
import time
import serial
import argparse
import numpy as np


class QPOD:
    """ Class for managing the QPOD controller"""
    def __init__(self):
        """ initializes nothing """
        self.AT_CONST=16.68e12
        self.DENS_QUARZ=2.648
        self.PI=3.1416
        self.FREQ_INIT = 6e6
        self.density = 1
        self.z_ratio = 1
        #print("QPOD initialized")
        # self.ser=0


    def openconnection(self, serialport='/dev/ttyUSB0'):
        """ open serial connection to QPOD controller """
        # connect to serial interface
        # configure the serial connections (the parameters differs on the device you
        # are connecting to)
        # global ser
        try:
            self.ser = serial.Serial(
                port=serialport,
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            self.gateperiod='2500000'
            self.measurementperiod='25000000'
            self.comm('B' + self.gateperiod)
            self.comm('C' + self.measurementperiod)
            #print("Connection fine.")
        except Exception as e:
            print("Could not connect to serial device. Reason: {}".format(str(e)))


    def closeconnection(self):
        """ close serial connection to QPOD """
        self.ser.close()
        #print('Serial Connection closed.')


    def comm(self, command='A1'):
        """ reads answer from QPOD """
        sendstring = '!' + command +'\r\n'
        self.ser.write(sendstring.encode('ASCII'))
        #time.sleep(0.1)
        answer = self.ser.readline()
        #while self.ser.inWaiting() > 0:
        #    answer += self.ser.read(1).decode()
        return answer

    def readthickness(self, return_freq=False):

        response=self.comm('A1')[2:]
        freq=200.0*float(self.gateperiod)/float(response)
        # Calculate thickness
        thickness=(self.AT_CONST*self.DENS_QUARZ)/(self.PI*freq*self.density*self.z_ratio)
        # Calculate thickness in Angstrom
        #thickness *= 1e-6
        # Correct for z-ratio
        thickness *= np.arctan(self.z_ratio * np.tan(self.PI*(self.FREQ_INIT - freq)/self.FREQ_INIT))
        if return_freq:
            return (thickness, freq)
        else:
            return thickness    

def main():
    # cli parser config
#    parser = argparse.ArgumentParser(description='Handle QPOD')
#    switch = parser.add_mutually_exclusive_group(required=True)
#    switch.add_argument('--read', help='read thickness',
#                        required=False)



#    args = parser.parse_args()
    # print args.on, args.offA
    qp=QPOD()
    qp.openconnection()
#    if args.read:
        #print("Starting READ-Procedure")
        #qp.readthickness()
    print(qp.readthickness())
    qp.closeconnection()



if __name__ == "__main__":
    main()

