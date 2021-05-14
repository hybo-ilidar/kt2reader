#!/usr/bin/env python

import socket
import numpy as np
import pickle
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import sys
import time
import threading
import signal

import kt2

HOST = '192.168.1.168'  # The server's hostname or IP address
PORT = 8282             # The port used by the server

class SIGINT_handler():
    def __init__(self):
        self.dead = False

    def signal_handler(self, signal, frame):
        self.dead = True
        print('You pressed Ctrl+C!')
        print('You pressed Ctrl+C!')

    def is_dead(self):
      return self.dead


class KT2socket:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.sock = None
    self.addr = '' # will server address returnd by socket.recvfrom()
    self.connect(host, port)
  
  def connect(self, host, port):
    self.host = host
    self.port = port
    self.sock = None
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #self.sock.settimeout(0.100)
    self.sock.bind(('0.0.0.0', port))

  def get_datagram(self, length):
      return self.sock.recvfrom(length)

def main(argv):

  handler = SIGINT_handler()
  signal.signal(signal.SIGINT, handler.signal_handler)

  pkt = kt2.Packet()
  plot_data = True

  if plot_data:
    depth_img_array = np.zeros((40, 320), dtype=np.int16)
    depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
    plt.ion()
    fig1, ax1 = plt.subplots()
    ax1.text(0.98, 0.06, f'{0:05d}',
        bbox={'facecolor': 'white', 'alpha': 1.0, 'pad': 2},
        verticalalignment='center', horizontalalignment='right',
        transform=ax1.transAxes,
        color='black', fontsize=8)
    axim1 = ax1.imshow(depth_img_array)
    fig1.canvas.flush_events()

  udp = KT2socket(HOST, PORT)

  #print('game over')
  #if True: exit(0)

  nframe = 0
  nrow = 0
  t0 = time.time()
  queue = []
  rowbeg = False
  rowend = False
  maxrows = 40
  gulping = True
  modulo_display = 100
  while gulping:

    buff, addr = udp.get_datagram(646)
    if pkt.parse(buff):
      #print( pkt.row, len(buff) )
      if pkt.row == 0: rowbeg = True
      if rowbeg:
        if pkt.row >= pkt.pack_maxrows-1: rowend = True
        if plot_data:
          depth_img_array[pkt.row, :] = pkt.image
        if rowend:
          rowbeg = False
          rowend = False
          nframe += 1
          if nframe % 100 == 0:
            t = time.time()
            dt = t - t0
            t0 = t
            fps = float(modulo_display) / dt
            print(f'frame: {nframe} dt: {dt:.3f} fps: {fps:.1f}' )
            if plot_data:
              ax1.text(0.98, 0.06, f'{nframe:05d}',
                  bbox={'facecolor': 'white', 'alpha': 1.0, 'pad': 2},
                  verticalalignment='center', horizontalalignment='right',
                  transform=ax1.transAxes,
                  color='black', fontsize=8)
          if plot_data:
            axim1.set_data(depth_img_array)
            fig1.canvas.flush_events()

        
    if handler.is_dead():
      print('stopping')
      gulping = False
      break
  
if __name__ == "__main__":
  main(sys.argv)

