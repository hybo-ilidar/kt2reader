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



