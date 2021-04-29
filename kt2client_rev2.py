#!/usr/bin/env python3

import socket
import numpy as np
import pickle
import matplotlib.pyplot as plt
import sys
import time
import threading
import signal

import kt2

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

class SIGINT_handler():
    def __init__(self):
        self.SIGINT = False

    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        self.SIGINT = True



class Ringbuf:
  # this thread continually runs, 
  # continually appending to a buffer 
  # main code consumes from the beginning of the buffer
  def __init__(self, conn):
    self.conn = conn
    self.ringbuf = bytearray(b'')
    self.flag_ready = False
    self.flag_go = False
    self.flag_kill = False
    self.flag_ack = False
    self.b2read = 1000
    self.logging = True
    self.log = []

  def reader(self):
    # signal READY to main program
    self.flag_ready = True
    # wait for GO trigger
    while not self.flag_go: continue
    while not self.flag_kill:
      try: 
        buff = self.conn.recv(self.b2read)
      except socket.timeout as e:
        err = e.args[0]
        if err == 'timed out':
          print('timed out')
          continue
        else:
          print(e)
          exit(0)
      else:
        pass
      if len(buff):
        self.ringbuf += buff
        if self.logging: self.log.append( [ 'T', self.b2read, len(buff), len(self.ringbuf) ] )
      else:
        pass
        ##time.sleep(0.001)
    print('Threaded ringbuf reader has ended')
    self.flag_ack = True

  def read(self, num, numpop=None):
    if self.logging: debugging = []
    if numpop==None: numpop=num
    if self.logging:
      if num == numpop: debugging.extend( [ 'E', num, numpop, len(self.ringbuf) ] )
    while len(self.ringbuf) < num:
      if self.logging: debugging.extend( [ 'R', len(self.ringbuf) ] )
      time.sleep(0.001)
    buff_return = self.ringbuf[0:num]
    self.ringbuf = self.ringbuf[numpop:]
    if self.logging: debugging.extend( [ 'X', num, len(self.ringbuf), buff_return[0:8] ] )
    if self.logging: self.log.append(debugging)
    return buff_return

  def swallow(self, num):
    #self.logging.append( [ 'S', num, len(self.ringbuf), self.ringbuf[:num] ] )
    self.ringbuf = self.ringbuf[num:]

  def size(self):
    return len(self.ringbuf)

  def log_dump(self):
    if not self.logging:
      print('Logging is not enabled')
      return
    for log in self.log:
      for f in log:
        if type(f) is bytearray:
          print(f.hex(), end='\t')
        else:
          print(f, end='\t')
      print()

class KT2socket:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.sock = None
    self.connect(host, port)
  
  def connect(self, host, port):
    self.host = host
    self.port = port
    self.sock = None
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.settimeout(2.00)
    while True:
      try:
        self.sock.connect((HOST, PORT))
      except socket.timeout as e:
        err = e.args[0]
        if err == 'timed out':
          print('timed out, trying again in 2 seconds')
          time.sleep(2)
          continue
        else:
          print(e)
          exit(0)
      else:
        break

    #s.setblocking(True)
    self.sock.settimeout(0.100)

def main(argv):

  handler = SIGINT_handler()
  signal.signal(signal.SIGINT, handler.signal_handler)

  syncher = kt2.Syncher()
  packet = kt2.Packet()
  plot_data = True

  if plot_data:
    depth_img_array = np.zeros((80, 320), dtype=np.int16)
    depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
    plt.ion()
    fig1, ax1 = plt.subplots()
    axim1 = ax1.imshow(depth_img_array)

  tcp = KT2socket(HOST, PORT)
  tcp.sock.sendall('G'.upper().encode()) # GO command

  ringbuf = Ringbuf(tcp.sock)
  thread1 = threading.Thread(target=ringbuf.reader)
  thread1.start()
  print('Thread started')
  print('Connected')
  while not ringbuf.flag_ready: pass
  ringbuf.flag_go = True

  nframe = 0
  nrow = 0
  t0 = time.time()
  queue = []
  row0 = False
  row79 = False
  gulping = True
  while gulping:

    # collect serial data
    if syncher.synched:
      if len(buff) == 0:
        buff = ringbuf.read(646)
      if packet.check_sync(buff):
        if buff[4] == 0: row0 = True
        if row0:
          if buff[4] >= 79: row79 = True
          packet.parse(buff)
          data = packet.image
          if plot_data and len(data) == 320:
            if buff[4] < 80:
              depth_img_array[buff[4], :] = data
        if row79:
          row0 = False
          row79 = False
          nframe += 1
          #print('got a frame')
          nframe += 1
          if plot_data:
            axim1.set_data(depth_img_array)
            fig1.canvas.flush_events()
        buff = [] # reset buffer
      else:
        syncher.reset()

    if not syncher.synched:  
      # search for sync
      for n in range(1000):
        sync = ringbuf.read(4,1)
        bret, buff = syncher.search4(sync)
        if bret:
          ringbuf.swallow(3) # swallow three bytes
          buff += ringbuf.read(642)  # rownum byte, type byte, 320 shorts
          break

    if handler.SIGINT:
      print('stopping')
      gulping = False
      break
  
  # kill threaded ringbuf reader
  ringbuf.flag_kill = True
  while not ringbuf.flag_ack: pass
  print('Test Ended')
  ringbuf.log_dump()

if __name__ == "__main__":
  main(sys.argv)

