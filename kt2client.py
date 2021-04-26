#!/usr/bin/env python3

import socket
import numpy as np
import pickle
import matplotlib.pyplot as plt
import sys
import time

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

def main(argv):

  depth_img_array = np.zeros((80, 320), dtype=np.int16)
  depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
  plt.ion()
  fig1, ax1 = plt.subplots()
  axim1 = ax1.imshow(depth_img_array)
  picklesize = len(pickle.dumps(depth_img_array))

  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(2.00)
    while True:
      try:
        s.connect((HOST, PORT))
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
    print('Connected')


    #s.setblocking(True)
    s.settimeout(0.100)
    for i in range(500):
      s.sendall(b'G')
      data=b''
      while True:
        try: 
          if len(data) >= picklesize: break
          data += s.recv(picklesize-len(data))
        except socket.timeout as e:
          err = e.args[0]
          if err == 'timed out':
            print('timed out')
            continue
          else:
            print(e)
            exit(0)
        else:
          continue
      depth_img_array = pickle.loads(data)
      print(i, len(data), depth_img_array[0][0])
      axim1.set_data(depth_img_array)
      fig1.canvas.flush_events()
  
  print('Test Ended')


if __name__ == "__main__":
  main(sys.argv)
