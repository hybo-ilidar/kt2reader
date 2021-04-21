#!/usr/bin/env python

import sys
import time
import struct

import serial
import pyftdi.serialext
from pyftdi.ftdi import Ftdi

logger = []

class Syncher:
  def __init__(self):
    self.reset()

  def reset(self):
    self.synched = False
    self.state = 0
    #self.pattern = bytearray([ 0x5a, 0xa5, 0x5a, 0xa5 ]) 
    self.pattern = bytes(bytearray([ 0xa5, 0x5a, 0xa5, 0x5a ]) )

  def search(self, ch):
    logger.append( [hex(ch[0]), self.synched, self.state ] )
    if len(ch):
      if ch[0] == self.pattern[self.state]:
        self.state += 1 
        if self.state >= 4:
          self.state = 0
          self.synched = True
      else:
        self.synched = False
        self.state = 0 
    return self.synched, self.pattern

class Packet:

  def __init__(self):
    self.max_size=646
    self.pack_sync = '<BBBB'
    self.pack_rownum = '<B'
    self.pack_type = '<B'
    self.pack_image = '<320h'
    self.pack_packet = '<' + self.pack_sync[1:] + self.pack_rownum[1:] \
                           + self.pack_type[1:] + self.pack_image[1:]
    self.size_image = struct.calcsize( self.pack_image )
    self.size_packet = struct.calcsize( self.pack_packet )

    self.sync=None
    self.rownum=None
    self.type=None
    self.depth=None
    self.gray=None

  def parse(self, buff):
    self.size = len(buff)
    if len(buff) == self.max_size:
      self.sync = int.from_bytes( buff[0:4], byteorder='big')
      self.rownum = int.from_bytes( buff[4:5], byteorder='little')
      self.type = int.from_bytes( buff[5:6], byteorder='little')
      self.image = list( struct.unpack(self.pack_image, buff[6:]) )
    else:
      self.sync = 0
      self.rownum = 0
      self.type = 0
      self.image = []

  def print(self):
    print( self.size, end='\t' )
    print( hex(self.sync), end='\t')
    print( self.rownum, end='\t' )
    print( self.type, end='\t' )
    print( len(self.image), end='\t'  )
    for val in self.image:
      print( val, end=' ')
    print()

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

  nframes = 1
  if len(argv) > 1:
    if argv[1] == 'help':
      show_help()
      exit(0)

    if argv[1] == 'list':
      Ftdi.show_devices()
      exit(0)

    if argv[1].isdigit():
      nframes = int(argv[1])



  # Example of usual serial ports
  #ser = serial.Serial ('/dev/tty.wchusbserial141230', 3000000 )
  #ser = serial.Serial ('/dev/tty.usbserial-A100RXY3', 1000000 )
  #ser = serial.Serial ('/dev/tty.usbserial-DN01O1MN', 3000000 )
  #ser = serial.Serial ('/dev/cu.usbserial-14720', 115200)
  #ser = serial.Serial ('/dev/ttyS18', 6000000 )
  #ser = serial.Serial ('COM5', 3000000 )
  #ser = serial.Serial ('COM8', 921600 )
  #ser = serial.Serial ('COM18', 7000000 )
  
  # Special URL Scheme for FTDI high speed comms
  #ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:14:1c/1', 12000000)
  #ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:14:e/1', 12000000, timeout=0.001)
  #ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:0:1/1', 12000000, timeout=0.001)
  #ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:1:5/1', 12000000, timeout=0.001)
  #ser = pyftdi.serialext.serial_for_url( 'ftdi://ftdi:232h:1/1', 12000000, timeout=0.001)
  ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:0:1/1', 12000000, timeout=0.001)

  ser.bytesize = serial.EIGHTBITS #number of bits per bytes
  ser.parity = serial.PARITY_NONE #set parity check: no parity
  ser.stopbits = serial.STOPBITS_ONE #number of stop bits
  # ser.timeout = None          #block read
  ser.xonxoff = False     #disable software flow control
  ser.rtscts = False     #disable hardware (RTS/CTS) flow control
  ser.dsrdtr = False       #disable hardware (DSR/DTR) flow control
  #ser.writeTimeout = 0     #timeout for write

  syncher = Syncher()
  packet = Packet()

  nframe = 0
  nrow = 0

  t0 = time.time()
  queue = []
  row0 = False
  row79 = False

  # find beginning of an image (row 0)
  while True:

    for n in range(1000):
      ch = ser.read(1)
      bret, buff = syncher.search(ch)
      if bret:
        break;
        print(n)

    for q in logger:
      print(q)
      exit(0)

    if syncher.synched:
      syncher.reset()
      buff += ser.read(642) # rownum byte, type byte, 320 shorts
      if buff[4] == 0: row0 = True
      if row0:
        #queue.append( [ (time.time() - t0), nframe, buff ] )
        queue.append( [ (time.time() - t0), nframe, buff[4] ] )
        nrow += 1
        if buff[4] >= 79: row79 = True
        if nrow >= 80: row79 = True
      if row79:
        nframe += 1
        nrow = 0
        row0=False
        row79=False

    if nframe >= nframes: break


  t1 = time.time()
  dt = t1 - t0
  tframe = dt / float(nframes)
  rate = 1.0 / tframe

  print('number of frames:', nframes)
  print('delta time:', t1-t0 )
  print('period:', tframe )
  print('freq:', rate )

  ##  for q in queue:
  ##    print('{:.6f}'.format(q[0]), end='\t') # time
  ##    print(q[1], end='\t') # frame number
  ##    packet.parse(q[2]) # data
  ##    packet.print()
  ##    #print( 'min:', min( packet.image ) )
  ##    #print( 'max:', max( packet.image ) )

  for q in queue:
    print('{:.6f}'.format(q[0]), end='\t') # time
    print(q[1], end='\t') # frame number
    print(q[2]) # row number

  ser.close()

if __name__ == "__main__":
  main(sys.argv)


