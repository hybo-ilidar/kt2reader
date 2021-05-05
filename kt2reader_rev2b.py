#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
import sys
import time
import struct
import serial
import pyftdi.serialext
from pyftdi.ftdi import Ftdi
import platform
import io

import kt2

def show_help():
    print('Usage:')
    print('kt2reader [help|list|nframes]')
    print('Where:')
    print('      help   this help message')
    print('      list   show available FTDI serial port URLs')
    print('   nframes   how many frames to capture, integer, def=1')
    print('Output:')
    print('   goes to stdout, can be redirected, for example:')
    print('      kt2reader 10 > capture.txt')
    print('Data fields:')
    print('      time   relative time in seconds')
    print('    frame#   sequential frame number')
    print('      size   size of buffer, should be 646')
    print('      sync   sync pattern 0x5a a5 5a a5')
    print('      row#   row number, 0 to 79')
    print('      type   image type, 0=dist cm')


def main(argv):
    ftdifilename = 'ftdi-port-'+platform.node()+'.txt'
    nframes = 100
    if len(argv) > 1:
        if argv[1] == 'help':
            show_help()
            exit(0)

        if argv[1] == 'list':
          ostr = io.StringIO()
          Ftdi.show_devices(None, ostr)
          with open( ftdifilename, 'w' ) as fp:
            print(ostr.getvalue().strip(), file=fp)
          print(ostr.getvalue().strip())
          print('saved to', ftdifilename)
          exit(0)

        if argv[1].isdigit():
            nframes = int(argv[1])

    portname = ''
    portdesc = ''
    with open(ftdifilename, 'r') as ftdi:
      for line in ftdi:
        fields = line.strip().split(None,1)
        if fields[0].startswith('ftdi:'):
          portname = fields[0]
          portdesc = fields[1]
          break;

    if len(portname) == 0:
      # Example of usual serial ports
      # ser = serial.Serial ('/dev/tty.wchusbserial141230', 3000000 )
      # ser = serial.Serial ('/dev/tty.usbserial-A100RXY3', 1000000 )
      # ser = serial.Serial ('/dev/tty.usbserial-DN01O1MN', 3000000 )
      # ser = serial.Serial ('/dev/cu.usbserial-14720', 115200)
      # ser = serial.Serial ('/dev/ttyS18', 6000000 )
      # ser = serial.Serial ('COM5', 3000000 )
      # ser = serial.Serial ('COM8', 921600 )
      # ser = serial.Serial ('COM18', 7000000 )
      # Special URL Scheme for FTDI high speed comms
      # ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:14:1c/1', 12000000)
      # ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:14:e/1', 12000000, timeout=0.001)
      # ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:0:1/1', 12000000, timeout=0.001)
      # ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:1:5/1', 12000000, timeout=0.001)
      # ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:1/1', 12000000, timeout=0.001)
      # ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:0:1/1', 12000000, timeout=0.001)
      portname = 'ftdi://ftdi:232h:0:1/1'
      portdesc = 'default'


    print('Port:', portname, portdesc)
    ser = pyftdi.serialext.serial_for_url(portname, 12000000, timeout=0.001)
    ser.bytesize = serial.EIGHTBITS  # number of bits per bytes
    ser.parity = serial.PARITY_NONE  # set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE  # number of stop bits
    # ser.timeout = None          #block read
    ser.xonxoff = False  # disable software flow control
    ser.rtscts = False  # disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False  # disable hardware (DSR/DTR) flow control
    # ser.writeTimeout = 0     #timeout for write

    syncher = kt2.Syncher()
    packet = kt2.Packet()

    plot_data = True
    plot_data_cv2 = False

    nframe = 0
    nrow = 0

    t0 = time.time()
    queue = []
    row0 = False
    row79 = False

    if plot_data:
      plt.ion()
      fig1, ax1 = plt.subplots()
      depth_img_array = np.zeros((80, 320), dtype=np.int16)
      depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
      axim1 = ax1.imshow(depth_img_array)

    buff = bytearray(b'')

    while True:
      
      serial_array = ser.read(1000) 
      max_cnt = len(serial_array)
      print('s.', max_cnt, sep='', end=' ')
      for c in serial_array:
        buff.extend(c.to_bytes(1, byteorder='little'))
        ptr = len(buff) - 1 # variable name from c++
        #print( ptr, [hex(v) for v in buff[0:10]] )
        if (    ( ptr > 9000 )
             or ( ptr == 0 and (    (buff[0] != 0x5a) ) )
             or ( ptr == 1 and (    (buff[0] != 0x5a) 
                                 or (buff[1] != 0xa5) ) )
             or ( ptr == 2 and (    (buff[0] != 0x5a) 
                                 or (buff[1] != 0xa5) 
                                 or (buff[2] != 0x5a) ) )
             or ( ptr >= 3 and (    (buff[0] != 0x5a) 
                                 or (buff[1] != 0xa5) 
                                 or (buff[2] != 0x5a) 
                                 or (buff[3] != 0xa5) ) )
           ): buff.pop() # remove last item
        # is the buffer filled:
        if ptr == 646:
          if packet.check_sync(buff):
            print('b.', buff[4], ' t.', buff[5], sep='', end=' ')
            if buff[4] == 0: row0 = True
            if row0:
              #queue.append([(time.time() - t0), nframe, buff])
              packet.parse(buff)
              data = packet.image
              if len(data) == 320:
                #print('buff[4]:', buff[4])
                if buff[4] < 80:
                  depth_img_array[buff[4], :] = data
                nrow += 1
                if buff[4] >= 79: row79 = True
                if nrow >= 80: row79 = True
            if row79:
              nframe += 1
              print('frame', nframe)
              nrow = 0
              row0 = False
              row79 = False
              if plot_data:
                #depth_img_array = depth_img_array / 12000.
                #depth_img_array_big = cv2.resize(depth_img_array, dsize=(1280, 320), interpolation=cv2.INTER_NEAREST)
                #cv2.imshow("test", depth_img_array_big)
                #cv2.waitKey(1)
                #matrix = np.random.randint(0, 100, size=(IMAGE_SIZE, IMAGE_SIZE), dtype=np.uint8)
                axim1.set_data(depth_img_array)
                fig1.canvas.flush_events()
                #print('drawn')
              if plot_data_cv2:
                depth_img_array = depth_img_array / 12000.
                #depth_img_array_big = cv2.resize(depth_img_array, dsize=(1280, 320), interpolation=cv2.INTER_NEAREST)
                cv2.imshow("test", depth_img_array)
          buff = bytearray(b'') # reset the buffer
          print('b.rst', end=' ')

      if nframe >= nframes: break



    ###   t1 = time.time()
    ###   dt = t1 - t0
    ###   tframe = dt / float(nframes)
    ###   rate = 1.0 / tframe

    # print('number of frames:', nframes)
    # print('delta time:', t1 - t0)
    # print('period:', tframe)
    # print('freq:', rate)

    ser.close()


if __name__ == "__main__":
    main(sys.argv)
