import numpy as np
import sys
import time
import struct
import serial
import pyftdi.serialext
from pyftdi.ftdi import Ftdi
import io
import platform
import threading
import statistics as stats

class Packet:
  def __init__(self):
    self.int_sync_pattern = int.from_bytes( b'\x5a\xa5\x5a\xa5', byteorder='big')
    self.max_size = 646
    self.pack_sync = '<BBBB'
    self.pack_rownum = '<B'
    self.pack_type = '<B'
    self.pack_image = '<320h'
    self.pack_packet = '<' + self.pack_sync[1:] + self.pack_rownum[1:] \
        + self.pack_type[1:] + self.pack_image[1:]
    self.size_image = struct.calcsize(self.pack_image)
    self.size_packet = struct.calcsize(self.pack_packet)

    self.sync = None
    self.rownum = None
    self.type = None
    self.depth = None
    self.gray = None

  def check_sync(self, buff):
    sync=0
    if len(buff) >= 4:
      sync = int.from_bytes(buff[0:4], byteorder='big')
      #print( hex(sync), hex(self.int_sync_pattern) )
      #print( sync == self.int_sync_pattern )
    return sync == self.int_sync_pattern

  def parse(self, buff):
    self.size = len(buff)
    if len(buff) == self.max_size:
      self.sync = int.from_bytes(buff[0:4], byteorder='big')
      self.rownum = int.from_bytes(buff[4:5], byteorder='little')
      self.type = int.from_bytes(buff[5:6], byteorder='little')
      self.image = list(struct.unpack(self.pack_image, buff[6:]))
    else:
      self.sync = 0
      self.rownum = 0
      self.type = 0
      self.image = []

  def print(self):
    print(self.size, end='\t')
    print(hex(self.sync), end='\t')
    print(self.rownum, end='\t')
    print(self.type, end='\t')
    print(len(self.image), end='\t')
    for val in self.image:
      print(val, end=' ')
    print()


class Ftdi_serial:
  def __init__(self, port_url, baud, timeout):
    self.open(port_url, baud, timeout)
    self.buff = bytearray(b'')
    self.bsize = 1000
    self.bthresh = 100
    self.b2read = 1000
    self.logging = []

    self.ringbuf = bytearray(b'')
    self.ringbuf_ready = False
    self.ringbuf_go = False
    self.ringbuf_kill = False
    self.ringbuf_ack = False

  def open(self, port_url, baud=12000000, timeout=0.001):
    self.port_url = port_url
    self.baud = baud
    self.timeout = timeout
    self.ser = pyftdi.serialext.serial_for_url(
        self.port_url, self.baud, timeout=self.timeout)
    self.ser.bytesize = serial.EIGHTBITS  # number of bits per bytes
    self.ser.parity = serial.PARITY_NONE  # set parity check: no parity
    self.ser.stopbits = serial.STOPBITS_ONE  # number of stop bits
    # self.ser.timeout = None          #block read
    self.ser.xonxoff = False  # disable software flow control
    self.ser.rtscts = False  # disable hardware (RTS/CTS) flow control
    self.ser.dsrdtr = False  # disable hardware (DSR/DTR) flow control
    # self.ser.writeTimeout = 0     #timeout for write

  def close(self):
    self.ser.close()

  def read(self, num, numpop=None):
    debugging = []
    if numpop == None: numpop = num
    debugging.extend(['E', num, numpop, len(self.buff)])
    if len(self.buff) < self.bthresh or len(self.buff) < num:
      while len(self.buff) < self.bsize:
        self.buff += self.ser.read(self.b2read)
        debugging.extend( [ 'R', len(self.buff) ] )
    buff_return = self.buff[0:num]
    self.buff = self.buff[numpop:]
    debugging.extend( [ 'X', num, len(self.buff), buff_return[0:8] ] )
    self.logging.append(debugging)
    return buff_return

  def swallow(self, num):
    self.buff = self.buff[num:]

  @staticmethod
  def list_devices():
    Ftdi.show_devices()

  @staticmethod
  def save_devices(filename):
    ostr = io.StringIO()
    Ftdi.show_devices(None, ostr)
    with open( filename, 'w' ) as fp:
      print(ostr.getvalue().strip(), file=fp)

  # this thread continually runs, continually appending to a buffer 
  # Main code consumed from the beginning of the buffer
  def ringbuf_reader(self):
    # signal READY to main program
    self.ringbuf_ready = True
    # wait for GO trigger
    while not self.ringbuf_go: pass
    while not self.ringbuf_kill:
      buff = self.ser.read(self.b2read)
      if len(buff) != self.b2read:
        #self.logging.append( [ 'T', self.b2read, len(buff), len(self.ringbuf) ] )
        time.sleep(0.001)
      if len(buff):
        self.ringbuf += buff
      if len(buff) == 0:
        time.sleep(0.001)

    print('Threaded ringbuf reader has ended')
    self.ringbuf_ack = True

  def ringbuf_read(self, num, numpop=None):
    #debugging = []
    if numpop==None: numpop=num
    #if num == numpop: debugging.extend( [ 'E', num, numpop, len(self.ringbuf) ] )
    while len(self.ringbuf) < num:
      #debugging.extend( [ 'R', len(self.ringbuf) ] )
      time.sleep(0.001)
    buff_return = self.ringbuf[0:num]
    self.ringbuf = self.ringbuf[numpop:]
    #debugging.extend( [ 'X', num, len(self.ringbuf), buff_return[0:8] ] )
    #self.logging.append(debugging)
    return buff_return

  def ringbuf_swallow(self, num):
    #self.logging.append( [ 'S', num, len(self.ringbuf), self.ringbuf[:num] ] )
    self.ringbuf = self.ringbuf[num:]

  def ringbuf_size(self):
    return len(self.ringbuf)


class Syncher:
  def __init__(self):
    self.reset()

  def reset(self):
    self.synched = False
    self.pattern = [0x5a, 0xa5, 0x5a, 0xa5]
    self.pattern4 = b'\x5a\xa5\x5a\xa5'
    # self.pattern4 = b'\xa5\x5a\xa5\x5a'

  def search4(self, sync):
    if len(sync) == 4:
      if sync == self.pattern4:
        self.synched = True
        return True, self.pattern4
    return False, b''

