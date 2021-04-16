#!/usr/bin/env python

import sys
import time
import struct

import serial
import pyftdi.serialext
from pyftdi.ftdi import Ftdi

class Syncher:
  def __init__(self):
    self.reset()

  def reset(self):
    self.synched = False
    self.accum = b''
    self.state = 0
    self.pattern = [ 0x5a, 0xa5, 0x5a, 0xa5 ]

  def search(self, ch):
    if len(ch):
      chint = int.from_bytes(ch, byteorder='little')
      if self.synched is False:
        if self.state == 0:
          if chint == self.pattern[self.state]:
            self.accum += ch
            self.state = 1
        elif self.state == 1:
          if chint == self.pattern[self.state]:
            self.state = 2
            self.accum += ch
          else:
            self.state = 0
            self.accum = b''
        elif self.state == 2:
          if chint == self.pattern[self.state]:
            self.state = 3
            self.accum += ch
          else:
            self.state = 0
            self.accum = b''
        elif self.state == 3:
          if chint == self.pattern[self.state]:
            self.state = 0
            self.accum += ch
            self.synched = True
          else:
            self.state = 0
            self.accum = b''
        else:
          self.state = 0
          self.synched = False
          self.accum = b''
      # synched up now
      return self.synched, self.accum
    else:
      return False, self.accum

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

  def print(self, ofile=sys.stdout):
    print( self.size, end='\t', file=ofile )
    print( hex(self.sync), end='\t', file=ofile)
    print( self.rownum, end='\t', file=ofile )
    print( self.type, end='\t', file=ofile )
    print( len(self.image), end='\t', file=ofile  )
    for val in self.image:
      print( val, end=' ', file=ofile)
    print(file=ofile)


class KT2_tof_lidar:
  def __init__(self, port, baud=12_000_000, timeout=0.001, ref_time=time.time()):
    self.t0 = ref_time
    self.serial_open(port, baud, timeout)
    self.syncher = Syncher()
    self.packet = Packet()
    self.nframe = 0
    self.nrow = 0
    self.queue = []
    self.row0 = False
    self.row79 = False
    self.enqueue = False

  def serial_open(self, port, baud=12_000_000, timeout=0.001):
    self.port = port
    self.baud = baud
    self.timeout = timeout
    # open serial port
    self.ser = pyftdi.serialext.serial_for_url( self.port, self.baud, timeout=self.timeout)
    # set serial port parameters
    self.ser.bytesize = serial.EIGHTBITS #number of bits per bytes
    self.ser.parity = serial.PARITY_NONE #set parity check: no parity
    self.ser.stopbits = serial.STOPBITS_ONE #number of stop bits
    #self.ser.timeout = None          #block read
    self.ser.xonxoff = False     #disable software flow control
    self.ser.rtscts = False     #disable hardware (RTS/CTS) flow control
    self.ser.dsrdtr = False       #disable hardware (DSR/DTR) flow control
    #self.ser.writeTimeout = 0     #timeout for write

  def serial_close(self):
    self.ser.close()


  def get_frame(self):
    self.nframe = 0
    self.nrow = 0
    self.queue = []
    self.row0 = False
    self.row79 = False
    self.buff = b''
    self.bret = False

    while True:

      for n in range(1000):
        ch = self.ser.read(1)
        self.bret, self.buff = self.syncher.search(ch)
        if self.bret:
          break;

      if self.syncher.synched:
        self.syncher.reset()
        self.buff += self.ser.read(642) # rownum byte, type byte, 320 shorts
        if self.buff[4] == 0: self.row0 = True
        if self.row0:
          if self.enqueue:
            self.queue.append( [ (time.time() - self.t0), self.nframe, self.buff ] )
          self.nrow += 1
          if self.buff[4] >= 79: self.row79 = True
          if self.nrow >= 80: self.row79 = True
        if self.row79:
          self.nframe += 1
          self.nrow = 0
          self.row0=False
          self.row79=False
          yield self.nframe

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

  t0 = time.time()
  kt2 = KT2_tof_lidar('ftdi://ftdi:232h:1/1', ref_time = t0)
  kt2.enqueue = True

  for nframe in kt2.get_frame():
    print(nframe)
    if nframe >= nframes: break


  t1 = time.time()
  dt = t1 - t0
  tframe = dt / float(nframes)
  rate = 1.0 / tframe

  print('number of frames:', nframes)
  print('delta time:', t1-t0 )
  print('period:', tframe )
  print('freq:', rate )

  if kt2.enqueue:
    print('i want to log')
    with open( 'capture.txt', 'w') as capfile:
      print('logging')
      for q in kt2.queue:
        print('{:.6f}'.format(q[0]), end='\t', file=capfile) # time
        print(q[1], end='\t', file=capfile) # frame number
        kt2.packet.parse(q[2]) # data
        kt2.packet.print(capfile)
        #print( 'min:', min( kt2.packet.image ), file=capfile )
        #print( 'max:', max( kt2.packet.image ), file=capfile )

  kt2.serial_close()

if __name__ == "__main__":
  main(sys.argv)


