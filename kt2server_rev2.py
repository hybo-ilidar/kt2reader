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
  if len(argv) > 1:
    if argv[1] == 'list':
      kt2.Ftdi_serial.save_devices(ftdifilename)
      kt2.Ftdi_serial.list_devices()
      exit(0)

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

  t0 = time.time()
  queue = []

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
  while not server_shutdown:

    send_serial_data = False
    client_disconnected = False
    listening=0 

    while not client_disconnected:
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
          client_disconnected = True
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
      while not connection_closed:

        # Act upon the following commands from the client:
        # C = close connection
        # Q = close server
        # G = GO, begin sending serial data
        try:
          msg = conn.recv(1024)
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
            client_disconnected = True
        except socket.error as e:
          # Something else happened, handle error, exit, etc.
          print(e)
          connection_closed = True
          client_disconnected = True
        else:
          if len(msg) == 0:
            print('orderly shutdown on server end')
            connection_closed = True
            client_disconnected = True
          else:
            # got a message do something :) 
            print(msg)
            if msg[0] == int.from_bytes(b'G', 'little'): 
              print('GO')
              send_serial_data = True
            elif msg[0] == int.from_bytes(b'C', 'little'): 
              print('CLOSE')
              connection_closed = True
              break
            elif msg[0] == int.from_bytes(b'Q', 'little'): 
              print('QUIT')
              connection_closed = True
              client_disconnected = True
              server_shutdown = True
              break
            else:
              print('DUNNO')
              pass

        if send_serial_data:
          buff = port.read()
          #print(len(buff))
          if len(buff):
            try:
              conn.sendall(buff)
              print('.', end='')
            except socket.error as e:
              print(e)
              print('restarting')
              connection_closed = True
              client_disconnected = True
              send_serial_data = False
              pass

        sys.stdout.flush()

  # kill threaded ringbuf reader
  #port.ringbuf_kill = True
  #while not port.ringbuf_ack: pass
  port.close()

if __name__ == "__main__":
  main(sys.argv)
