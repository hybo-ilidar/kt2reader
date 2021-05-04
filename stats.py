#!/usr/bin/env python

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import csv
import kt2

class DisplayTimes:
  def __init__( self, tlast, tcopy, tmake, tdraw ):
    self.tlast = tlast
    self.tcopy = tcopy
    self.tmake = tmake
    self.tdraw = tdraw
  def __str__(self):
    return '{self.tlast} {self.tcopy} {self.tmake} {self.tlast}'.format(self=self)
  def __repr__(self):
    return '{self.tlast} {self.tcopy} {self.tmake} {self.tlast}'.format(self=self)

class CaptureTimes:
  def __init__( self, tlast ):
    self.tlast = tlast
  def __str__(self):
    return '{self.tlast}'.format(self=self)
  def __repr__(self):
    return '{self.tlast}'.format(self=self)


def show_help():
  print('Usage:')
  print('plotcap [capture-file]')
  print('Where:')
  print('  capture-file   text file captured by kt2reader programs')

def main( argv ):
  capture = []
  display = []
  if len(argv) < 2:
    show_help()
    exit(0)

  with open(argv[1], 'r') as fin:
    reader = csv.reader(fin, delimiter=' ')
    nrows=0
    for row in reader:
      if len(row) == 0: continue

      if row[0] == 'Done.': #this is serial capture data
        tlast = float(row[2]) / 1000.0
        capture.append( CaptureTimes( tlast ) )

      if row[0] == 'Plotted': #this is display plot times
        tlast = float(row[2]) / 1000.0
        tcopy = float(row[3]) / 1000.0
        tmake = float(row[4]) / 1000.0
        tdraw = float(row[5]) / 1000.0
        display.append( DisplayTimes( tlast, tcopy, tmake, tdraw ) )
            
           
  #fig,ax = plt.subplots()
  if len(capture):
    print('Capture', len(capture), 'items' )
    captimes = kt2.Mystats( [ cap.tlast for cap in capture ] )
    captimes.name = 'Serial Capture Frame Times, msec'
    captimes.summary()
    captimes.plot(plt)
  else:
    print('Capture   no data')

  if len(display):
    print('Display', len(display), 'items' )
    disptlast = kt2.Mystats( [ disp.tlast for disp in display ] )
    disptcopy = kt2.Mystats( [ disp.tcopy for disp in display ] )
    disptmake = kt2.Mystats( [ disp.tmake for disp in display ] )
    disptdraw = kt2.Mystats( [ disp.tdraw for disp in display ] )

    disptlast.name = 'Display Loop Time, msec'
    disptlast.summary()
    disptlast.plot(plt)
    disptcopy.name = 'Display Loop, Time Copying Data Time, msec'
    disptcopy.summary()
    disptcopy.plot(plt)
    disptmake.name = 'Display Loop, Time Making Images, msec'
    disptmake.summary()
    disptmake.plot(plt)
    disptdraw.name = 'Display Loop, Time Drawing Image, msec'
    disptdraw.summary()
    disptdraw.plot(plt)




  else:
    print('Display   no data')


  plt.show()

if __name__ == "__main__":
  main(sys.argv)

