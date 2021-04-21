#!/usr/bin/env python

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import csv

# These cursor classes are examples from Matplotlib

## RCLOTT: modified this to only show the vertical cursor (time) 
class SnappingCursor:
  """
  A cross hair cursor that snaps to the data point of a line, which is
  closest to the *x* position of the cursor.

  For simplicity, this assumes that *x* values of the data are sorted.
  """
  def __init__(self, ax, line):
    self.ax = ax
    self.horizontal_line = ax.axhline(color='k', lw=0.8, ls='--')
    self.vertical_line = ax.axvline(color='k', lw=0.8, ls='--')
    self.x, self.y = line.get_data()
    self._last_index = None
    # text location in axes coords
    self.text = ax.text(0.05, 0.9, '', transform=ax.transAxes)

  def set_cross_hair_visible(self, visible):
    need_redraw = self.horizontal_line.get_visible() != visible
    self.horizontal_line.set_visible(False)
    need_redraw = self.vertical_line.get_visible() != visible
    self.vertical_line.set_visible(visible)
    self.text.set_visible(visible)
    return need_redraw

  def on_mouse_move(self, event):
    if not event.inaxes:
      self._last_index = None
      need_redraw = self.set_cross_hair_visible(False)
      if need_redraw:
        self.ax.figure.canvas.draw()
    else:
      self.set_cross_hair_visible(True)
      x, y = event.xdata, event.ydata
      index = min(np.searchsorted(self.x, x), len(self.x) - 1)
      if index == self._last_index:
        return  # still on the same data point. Nothing to do.
      self._last_index = index
      x = self.x[index]
      y = self.y[index]
      # update the line positions
      #self.horizontal_line.set_ydata(y)
      self.vertical_line.set_xdata(x)
      #self.text.set_text('x=%1.2f, y=%1.2f' % (x, y))
      self.text.set_text('x=%.3f' % (x))
      self.ax.figure.canvas.draw()

class Cursor:
  """
  A cross hair cursor.
  """
  def __init__(self, ax):
    self.ax = ax
    self.horizontal_line = ax.axhline(color='k', lw=0.8, ls='--')
    self.vertical_line = ax.axvline(color='k', lw=0.8, ls='--')
    # text location in axes coordinates
    self.text = ax.text(0.72, 0.9, '', transform=ax.transAxes)

  def set_cross_hair_visible(self, visible):
    need_redraw = self.horizontal_line.get_visible() != visible
    self.horizontal_line.set_visible(visible)
    self.vertical_line.set_visible(visible)
    self.text.set_visible(visible)
    return need_redraw

  def on_mouse_move(self, event):
    if not event.inaxes:
      need_redraw = self.set_cross_hair_visible(False)
      if need_redraw:
          self.ax.figure.canvas.draw()
    else:
      self.set_cross_hair_visible(True)
      x, y = event.xdata, event.ydata
      # update the line positions
      self.horizontal_line.set_ydata(y)
      self.vertical_line.set_xdata(x)
      self.text.set_text('x=%1.2f, y=%1.2f' % (x, y))
      self.ax.figure.canvas.draw()


class LineCapture:
  def __init__( self, time, frame, line ):
    self.time = time
    self.frame = frame
    self.line = line
  def __str__(self):
    return '{self.time} {self.frame} {self.line}'.format(self=self)
  def __repr__(self):
    return '{self.time} {self.frame} {self.line}'.format(self=self)

def show_help():
  print('Usage:')
  print('plotcap [capture-file]')
  print('Where:')
  print('  capture-file   text file captured by kt2reader programs')

def main( argv ):
  capture = []
  if len(argv) < 2:
    show_help()
    exit(0)

  with open(argv[1], 'r') as fin:
    reader = csv.reader(fin, delimiter='\t')
    nrows=0
    for row in reader:
      time = float(row[0])
      frame = int(row[1])
      line = int(row[4])
      capture.append( LineCapture( time, frame, line ) )
      nrows += 1
      if nrows >= 320: break

  time = []
  value = []
  x = [ cap.time for cap in capture ]
  y = [ cap.line for cap in capture ]

  fig,ax = plt.subplots()
  #ax.plot(x,y)

  #ax.scatter(x,y)
  line, = ax.plot(x,y, 'o')
  #ax.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
  #ax.minorticks_off()
  #xres = 0.25
  #start, stop = ax.get_xlim()
  #ticks = np.arange(start, stop + xres, xres)
  #ax.set_xticks(ticks)

  #from matplotlib.widgets import Cursor
  #cursor = Cursor(ax, useblit=True, color='orange', linewidth=2)

  #cursor = Cursor(ax)
  #fig.canvas.mpl_connect('motion_notify_event', cursor.on_mouse_move)

  snap_cursor = SnappingCursor(ax, line)
  fig.canvas.mpl_connect('motion_notify_event', snap_cursor.on_mouse_move)

  plt.show()

if __name__ == "__main__":
  main(sys.argv)

