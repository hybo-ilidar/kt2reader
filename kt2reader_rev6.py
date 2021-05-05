#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
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

  def parse_2(self, buff):
    # self.size = len(buff)
      if len(buff) == self.max_size:
        # self.sync = int.from_bytes(buff[0:4], byteorder='big')
          # self.rownum = int.from_bytes(buff[4:5], byteorder='little')
          # self.type = int.from_bytes(buff[5:6], byteorder='little')
          self.image = list(struct.unpack(self.pack_image, buff[6:]))
      else:
        # .sync = 0
          # self.rownum = 0
          # self.type = 0
          self.image = []
      return self.image

  def print(self):
    # print(self.size, end='\t')
      # print(hex(self.sync), end='\t')
      print(self.rownum, end='\t')
      # print(self.type, end='\t')
      # print(len(self.image), end='\t')
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


def main(argv):
  ftdifilename = 'ftdi-port-'+platform.node()+'.txt'
  plot_data = True
  capture_data = False
  nframes = 10
  if len(argv) > 1:
    if argv[1] == 'list':
      Ftdi_serial.save_devices(ftdifilename)
      Ftdi_serial.list_devices()
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
    print('Must save port in text file first:', ftdifilename)
    print('First run:')
    print('    ', argv[0],' list')
    print('then edit as required')
    exit(0)

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

  print('Opening port:', portname, 'Description:', portdesc)

  port = Ftdi_serial(portname, baud=12000000, timeout=0.000)

  syncher = Syncher()
  packet = Packet()

  nframe = 0
  nrow = 0
  t0 = time.time()
  queue = []
  rowbeg = False
  rowend = False

  maxrows = 40
  if plot_data:
    depth_img_array = np.zeros((maxrows, 320), dtype=np.int16)
    depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
    plt.ion()
    fig1, ax1 = plt.subplots()
    axim1 = ax1.imshow(depth_img_array)

  thread1 = threading.Thread(target=port.ringbuf_reader)
  thread1.start()

  iloop = 0 # alternate escape method
  while not port.ringbuf_ready: pass
  port.ringbuf_go = True

  buff=[]

  times_parse = []
  times_plot = []

  while True:
    iloop+=1

    if syncher.synched:
      if len(buff) == 0:
        buff = port.ringbuf_read(646)
      if packet.check_sync(buff):
        if buff[4] == 0: rowbeg = True
        if rowbeg:
          if buff[4] >= maxrows-1: rowend = True
          if capture_data:
            queue.append([(time.time() - t0), nframe, buff])
          if plot_data:
            start=time.time()
            data = packet.parse_2(buff)
            if len(data) == 320:
              if buff[4] < maxrows:
                depth_img_array[buff[4], :] = data
            times_parse.extend( [time.time()-start] )
        if rowend:
          rowbeg = False
          rowend = False
          nframe += 1
          if plot_data:
            start=time.time()
            axim1.set_data(depth_img_array)
            fig1.canvas.flush_events()
            times_plot.extend( [time.time()-start] )
        buff = [] # reset buffer
      else:
        syncher.reset()

    if not syncher.synched:  
      # search for sync
      for n in range(1000):
        sync = port.ringbuf_read(4,1)
        bret, buff = syncher.search4(sync)
        if bret:
          port.ringbuf_swallow(3) # swallow three bytes
          buff += port.ringbuf_read(642)  # rownum byte, type byte, 320 shorts
          break


    if nframe >= nframes: break
    #if iloop >= 1000: break

  if capture_data:
    for q in queue:
      # print('{:.6f}'.format(q[0]), end='\t')  # time
        # print(q[1], end='\t')  # frame number
        packet.parse(q[2])  # data
        packet.print()

  for log in port.logging:
    for f in log:
      if type(f) is bytearray:
        print(f.hex(), end='\t')
      else:
        print(f, end='\t')
    print()

  mean = stats.mean(times_parse)
  stdev = stats.stdev(times_parse)
  tmin = min(times_parse)
  tmax = max(times_parse)
  print(f'Tparse,  mean: {mean:.6f}')
  print(f'Tparse, stdev: {stdev:.6f}')
  print(f'Tparse,   max: {tmin:.6f}')
  print(f'Tparse,   min: {tmax:.6f}')
  mean = stats.mean(times_plot)
  stdev = stats.stdev(times_plot)
  tmin = min(times_plot)
  tmax = max(times_plot)
  print(f'T.plot,  mean: {mean:.6f}')
  print(f'T.plot, stdev: {stdev:.6f}')
  print(f'T.plot,   max: {tmin:.6f}')
  print(f'T.plot,   min: {tmax:.6f}')

  #for t in times_parse:
  #  print(f'T.parse: {t:.6f}')
  #for t in times_plot:
  #  print(f'T.plot: {t:.6f}')


  # kill threaded ringbuf reader
  port.ringbuf_kill = True
  while not port.ringbuf_ack: pass
  port.close()

if __name__ == "__main__":
  main(sys.argv)
