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
import socket
import pickle

import kt2


# Main server, reads bytes from serial port and
# make them available on socket
def main(argv):

  ftdifilename = 'ftdi-port-'+platform.node()+'.txt'
  plot_data = True
  capture_data = False
  nframes = 10
  if len(argv) > 1:
    if argv[1] == 'list':
      kt2.Ftdi_serial.save_devices(ftdifilename)
      kt2.Ftdi_serial.list_devices()
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

  print('Opening port:', portname, 'Description:', portdesc)
  port = kt2.Ftdi_serial(portname, baud=12000000, timeout=0.000)

  syncher = kt2.Syncher()
  packet = kt2.Packet()

  nframe = 0
  nrow = 0
  t0 = time.time()
  queue = []
  row0 = False
  row79 = False

  thread1 = threading.Thread(target=port.ringbuf_reader)
  thread1.start()

  iloop = 0 # alternate escape method
  while not port.ringbuf_ready: pass
  port.ringbuf_go = True

  buff=[]

  times_parse = []
  times_plot = []

  HOST = 'localhost'
  PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
  socket.setdefaulttimeout(20)
  print('socket default timeout:', socket.getdefaulttimeout() )
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind((HOST, PORT))
  print('socket timeout:', s.gettimeout() )
  print('socket blocking:', s.getblocking() )
  s.listen(1)

  server_shutdown = False
  listening=0 
  while not server_shutdown:
    listening+=1
    print('listening for connection', listening)
    try:
      conn, addr = s.accept()
    except socket.timeout as e:
      err = e.args[0]
      if err == 'timed out':
        time.sleep(2)
        continue
      else:
        print(e)
        server_shutdown = True
    print('Connected by', addr)
    #print('socket timeout:', s.gettimeout() )
    #print('socket blocking:', s.getblocking() )
    print('setting...')
    #s.setblocking(False)
    #s.settimeout(0.001)
    #conn.setblocking(False)
    conn.settimeout(0.001)
    print('conn timeout:', conn.gettimeout() )
    print('conn blocking:', conn.getblocking() )

    connection_closed = False

    send_frame = False
    frame = np.zeros((80, 320), dtype=np.int16)
    print( 'frame size:', len(frame))
    print( 'frame pickle size:', len(pickle.dumps(frame)))
    while not connection_closed:

      try:
        msg = conn.recv(1)
      except socket.timeout as e:
        err = e.args[0]
        # this next if/else is a bit redundant, but illustrates how the
        # timeout exception is setup
        if err == 'timed out':
          #time.sleep(0.010)
          pass
        else:
          print(e)
          connection_closed = True
          server_shutdown = True
      except socket.error as e:
        # Something else happened, handle error, exit, etc.
        print(e)
        connection_closed = True
        server_shutdown = True
      else:
        if len(msg) == 0:
          print('orderly shutdown on server end')
          connection_closed = True
          server_shutdown = True
        else:
          # got a message do something :) 
          # send data  conn.sendall(data)
          #print(msg, port.ringbuf_size())
          send_frame = True

      # Otherwise, keep collecting serial data
      if syncher.synched:
        if len(buff) == 0:
          buff = port.ringbuf_read(646)
        if packet.check_sync(buff):
          #print('got a line')
          if buff[4] == 0: row0 = True
          if row0:
            if buff[4] >= 79: row79 = True
            packet.parse(buff)
            if len(packet.image) == 320:
              if buff[4] < 80:
                frame[buff[4], :] = packet.image
          if row79:
            row0 = False
            row79 = False
            nframe += 1
            #print('got a frame')
            if send_frame:
              send_frame = False
              conn.sendall(pickle.dumps(frame))
              frame = np.zeros((80, 320), dtype=np.int16)

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
    sys.stdout.flush()

  # kill threaded ringbuf reader
  port.ringbuf_kill = True
  while not port.ringbuf_ack: pass
  port.close()

if __name__ == "__main__":
  main(sys.argv)
