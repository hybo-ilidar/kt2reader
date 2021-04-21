# Installation

Computer needs Python 3 installed

## pySerial

* https://pythonhosted.org/pyserial/index.html

## pyFTDI

Uses the FTDI Python library package, PyFTDI:

* https://pypi.org/project/pyftdi/
* https://eblot.github.io/pyftdi/index.html

As mentioned in the [installation documentation](https://eblot.github.io/pyftdi/installation.html), 
pyFTDI requires `libusb 1.x`. Installing this on Windows can be tricky.
We used the Zadig method described in the instructions with success.

## Python libraries

These python libraries should be installed

```bash
$ pip install pyserial pyftdi
```

## Program 

To open the port using the FTDI library, you need to know the URL name
of the device connected to your system ( see [here])https://eblot.github.io/pyftdi/urlscheme.html) ).
If you just run the program with the `list` option, all available FTDI
devices will be shown:

```bash
$ python kt2reader.py list
Available interfaces:
  ftdi://ftdi:232h:1/1
```

Put this URL in the source code `kt2reader.py`.

Run the program as follows:

```bash
$ python kt2reader.py help
Usage:
kt2reader [help|list|nframes]
Where:
      help   this help message
      list   show available FTDI serial port URLs
   nframes   how many frames to capture, integer, def=1
Output:
   goes to stdout, can be redirected, for example:
      kt2reader 10 > capture.txt
Data fields:
      time   relative time in seconds
    frame#   sequential frame number
      size   size of buffer, should be 646
      sync   sync pattern 0x5a a5 5a a5
      row#   row number, 0 to 79
      type   image type, 0=dist cm

$ python kt2reader.py 4 > capture.txt

```

## Notes 16 Feb 2021

#### About image drawing

Method using opencv-python is shown in program `kt2reader_rev1.py` 
I am not too familiar with opencv in Python. But I had already been
experimenting with using matplotlib to draw images (just from an 
[online example I found](https://stackoverflow.com/questions/17835302/how-to-update-matplotlibs-imshow-window-interactively).

Take a look at this version using matplotlib: `kt2reader_rev2.py`
It might be working, I can't tell 100% because of some network
connection issues.

Also I am testing making a generator `get_frame()` function which yields
between frames. Not sure if this would help or not. 
Not 100% ready yet, but shows the concept: `kt2reader_generator.py`

Note: Using Python 3.7.5 on this Windows computer for testing.
Other versions could be installed if needed to match a different setup.

#### Screen capture examples:

Made with `kt2reader_rev2.py`

![Background](images/image-background.png)
![Hand Waving](images/image-hand-waving.png)

## Notes 19 Apr 2021: Times and Speed Calculations

* UART running 12 Mbaud == 83.333 nsec
* each byte 10 bits: 833.333 nsec <==> 1.2 Mbytes/sec
* one video line is 646 bytes: 538.333 usec <==> 1.858 K-lines/sec
* one video frame: 
  - 80 lines: 51,680 bytes = 50.469 Kibytes
  - 80 lines: 43.067 msec <==> 23.219 frames/sec max

The captured data file can be viewed in an editor or plotted using
`plotcap.py`:

![Captured Timing, beginning time](images/capture-frame-beg-1188.png)
![Captured Timing, enging time](images/capture-frame-end-1718.png)
![Captured Timing, next frame time](images/capture-frame-next-2723.png)

We see about 6 lines of data being read almost simultaneously
This suggests the buffer size of the UART... let's check it:

* FTDI FT232H has 2K buffer

* One frame takes about 60ms to send 
  - 750 usec / line
  - 212 usec gap between lines
* Frame period: about 118.5 ms  <==> 8.44 FPS
  - about 60 msec gap between frames
  - could this be an entire missing frame?

## Testbed

Simple program written to generate test pattern (actually any image
file) and send it from STM32F4 microcontroller.

For example, using Hybo logo file, resize it to 320x80 and make 16-bit
grayscale using `imagemagick`:

```bash
$ convert hybo-logo.png -resize 320x80 hybo-logo-320x80.png
$ convert hybo-logo.png -resize 320x80 -depth 16 -type Grayscale -negate hybo-logo-320x80.png
```

Using a few lines of Python (see `make-array.py`) to generate an array
of pixel data suitable for including in the microprocessor code as 
constant image data (see the resulting file `logo.c`). Programmed this
into an iLidar unit (it was convenient and nearby), used comms from the
User I/O pins through an external FT232H USB-to-serial adaptor to
simulate a KT2 unit.

![Test Pattern captured w/Dr Son's C++ Program](images/test-pattern-capture-dr-son-cpp-program.png)
![Test Pattern captured w/Python Kt2reader](images/test-pattern-python-capture.png)

Was able to match the timing of the real sensor reasonably well. 
This gives a portable and known pattern to be used for serlial link testing.

![Scope Capture, Line Header Details](images/scope-line-header.png)
![Scope Capture, One Line Time](images/scope-one-line-time-536us.png)
![Scope Capture, Line to Line Time](images/scope-line-to-line-806us.png)
![Scope Capture, One Frame Time](images/scope-one-frame-time-65ms.png)
![Scope Capture, Frame to Frame Time](images/scope-frame-to-frame-131ms.png)









