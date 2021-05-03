#!/usr/bin/env python3
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
import statistics as stats

from PIL import Image
  
class DemoFrame:
  def __init__(self, pngfile = 'hybo-logo-320x80.png'):
    self.image= Image.open(pngfile)
    self.pixels =  ( np.asarray(self.image) / 60 ).astype(int)
    self.width, self.height = self.image.size

  def printme(self):
    for irow, row in enumerate(self.pixels):
      print('  { ', end='' )
      for pix in row:
        print( pix, end=',' )
      print(' }, // row#', irow )

  def shift_rows(self, n):
    return np.roll(self.pixels, n, axis=0)

  def shift_cols(self, n):
    return np.roll(self.pixels, n, axis=1)

  def shift_both(self, n,m):
    return np.roll(self.pixels, (n,m), axis=(0,1))



def main(argv):
    nframe = 0
    nframes = 100
    if len(argv) > 1:
        if argv[1].isdigit():
            nframes = int(argv[1])

    demo = DemoFrame()

    plt.ion()
    fig1, ax1 = plt.subplots()

    depth_img_array = np.zeros((80, 320), dtype=np.int16)
    depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
    axim1 = ax1.imshow(depth_img_array)

    nscrolls = 10
    yshift = int( demo.height / nscrolls )  # 80 / 10
    xshift = int( demo.width / nscrolls )  # 320 / 10
    images_scrolled = []
    for i in range(nscrolls):
      #images_scrolled.append( demo.shift_rows(i * nshift) )
      images_scrolled.append( demo.shift_both((i*yshift),(i*xshift)) )


    start = time.time()
    times_plot = []
    for i in range(nframes):
      t0 = time.time()
      depth_img_array = images_scrolled[ i % nscrolls ]
      axim1.set_data(depth_img_array)
      fig1.canvas.flush_events()
      times_plot.extend( [ (time.time()-t0)*1000.0 ] )


    # breakpoint()

    num = len(times_plot)
    mean = stats.mean(times_plot)
    stdev = stats.stdev(times_plot)
    tmin = min(times_plot)
    tmax = max(times_plot)
    print(f'T.plot,   num: {num}')
    print(f'T.plot,  mean: {mean:.6f}')
    print(f'T.plot, stdev: {stdev:.6f}')
    print(f'T.plot,   min: {tmin:.6f}')
    print(f'T.plot,   max: {tmax:.6f}')

    plt.figure()
    plt.hist(times_plot, density=False, bins=100)
    plt.yscale('log')
    plt.ylabel('count')
    plt.xlabel('display times, milliseconds')
    plt.title('histogram of display times')

    # clip data and make new histogram
    tclip = 100
    times_clipped = []
    for t in times_plot:
      if t < tclip: 
        times_clipped.extend([t])
    num = len(times_clipped)
    mean = stats.mean(times_clipped)
    stdev = stats.stdev(times_clipped)
    tmin = min(times_clipped)
    tmax = max(times_clipped)
    print(f'T.clip,   num: {num}')
    print(f'T.clip,  mean: {mean:.6f}')
    print(f'T.clip, stdev: {stdev:.6f}')
    print(f'T.clip,   min: {tmin:.6f}')
    print(f'T.clip,   max: {tmax:.6f}')

    plt.figure()
    plt.hist(times_clipped, density=False, bins=100)
    plt.yscale('log')
    plt.ylabel('count')
    plt.xlabel('display times, milliseconds')
    plt.title('histogram of clipped (100ms) display times')

    plt.show(block=True)


    # t1 = time.time()
    # dt = t1 - t0
    # tframe = dt / float(nframes)
    # rate = 1.0 / tframe
    # print('number of frames:', nframes)
    # print('delta time:', t1 - t0)
    # print('period:', tframe)
    # print('freq:', rate)


if __name__ == "__main__":
    main(sys.argv)
