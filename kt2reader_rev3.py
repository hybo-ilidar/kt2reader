#!/usr/bin/env python3
import cv2
import numpy as np
import matplotlib.pyplot as plt
import sys
import time
import struct
import serial
import pyftdi.serialext
from pyftdi.ftdi import Ftdi


class Syncher:
    def __init__(self):
        self.reset()

    def reset(self):
        self.synched = False
        self.accum = b''
        self.state = 0
        self.pattern = [0x5a, 0xa5, 0x5a, 0xa5]

    def search(self, ch):
        if len(ch):
            chint = int.from_bytes(ch, byteorder='little')
            if self.synched is False:
                if self.state == 0:
                    if chint == self.pattern[self.state]:
                        self.accum += ch
                        self.state = 1
                elif self.state == 1:
                    if chint == self.pattern[self.state]:
                        self.state = 2
                        self.accum += ch
                    else:
                        self.state = 0
                        self.accum = b''
                elif self.state == 2:
                    if chint == self.pattern[self.state]:
                        self.state = 3
                        self.accum += ch
                    else:
                        self.state = 0
                        self.accum = b''
                elif self.state == 3:
                    if chint == self.pattern[self.state]:
                        self.state = 0
                        self.accum += ch
                        self.synched = True
                    else:
                        self.state = 0
                        self.accum = b''
                else:
                    self.state = 0
                    self.synched = False
                    self.accum = b''
            # synched up now
            return self.synched, self.accum
        else:
            return False, self.accum


class Packet:
    def __init__(self):
        self.max_size = 646
        self.pack_sync = '<BBBB'
        self.pack_rownum = '<B'
        self.pack_type = '<B'
        self.pack_image = '<320h'
        self.pack_packet = '<' + self.pack_sync[1:] + self.pack_rownum[1:] \
                           + self.pack_type[1:] + self.pack_image[1:]
        self.size_image = struct.calcsize(self.pack_image)
        self.size_packet = struct.calcsize(self.pack_packet)

        self.sync = None
        self.rownum = None
        self.type = None
        self.depth = None
        self.gray = None

    def parse(self, buff):
        self.size = len(buff)
        if len(buff) == self.max_size:
            self.sync = int.from_bytes(buff[0:4], byteorder='big')
            self.rownum = int.from_bytes(buff[4:5], byteorder='little')
            self.type = int.from_bytes(buff[5:6], byteorder='little')
            self.image = list(struct.unpack(self.pack_image, buff[6:]))
        else:
            self.sync = 0
            self.rownum = 0
            self.type = 0
            self.image = []

    def parse_2(self, buff):
        # self.size = len(buff)
        if len(buff) == self.max_size:
            # self.sync = int.from_bytes(buff[0:4], byteorder='big')
            # self.rownum = int.from_bytes(buff[4:5], byteorder='little')
            # self.type = int.from_bytes(buff[5:6], byteorder='little')
            self.image = list(struct.unpack(self.pack_image, buff[6:]))
        else:
            # .sync = 0
            # self.rownum = 0
            # self.type = 0
            self.image = []
        return self.image

    def print(self):
        # print(self.size, end='\t')
        # print(hex(self.sync), end='\t')
        print(self.rownum, end='\t')
        # print(self.type, end='\t')
        # print(len(self.image), end='\t')
        for val in self.image:
            print(val, end=' ')
        print()


def main(argv):
    nframes = 500
    if len(argv) > 1:
        if argv[1] == 'list':
            Ftdi.show_devices()
            exit(0)

        if argv[1].isdigit():
            nframes = int(argv[1])

    ser = pyftdi.serialext.serial_for_url('ftdi://ftdi:232h:1/1', 12000000, timeout=0.001) # 12000000
    ser.bytesize = serial.EIGHTBITS  # number of bits per bytes
    ser.parity = serial.PARITY_NONE  # set parity check: no parity
    ser.stopbits = serial.STOPBITS_ONE  # number of stop bits
    # ser.timeout = None          #block read
    ser.xonxoff = False  # disable software flow control
    ser.rtscts = False  # disable hardware (RTS/CTS) flow control
    ser.dsrdtr = False  # disable hardware (DSR/DTR) flow control
    # ser.writeTimeout = 0     #timeout for write

    syncher = Syncher()
    packet = Packet()

    nframe = 0
    nrow = 0
    t0 = time.time()
    queue = []
    row0 = False
    row79 = False

    depth_img_array = np.zeros((80, 320), dtype=np.int16)
    depth_img_array[0, 0] = 3000 # this value allow imshow to initialise it's color scale
    plt.ion()
    fig1, ax1 = plt.subplots()
    axim1 = ax1.imshow(depth_img_array)

    # find beginning of an image (row 0)
    while True:
        for n in range(1000):
            ch = ser.read(1)
            bret, buff = syncher.search(ch)
            if bret:
                break

        if syncher.synched:
            syncher.reset()
            buff += ser.read(642)  # rownum byte, type byte, 320 shorts
            if buff[4] == 0: row0 = True
            if row0:
                # queue.append([(time.time() - t0), nframe, buff])
                data = packet.parse_2(buff)
                print("buff[4]: " + str(buff[4]))
                if len(data) == 320:
                  if buff[4] < 79:
                    depth_img_array[buff[4], :] = data
                  if buff[4] >= 79: row79 = True
            if row79:
                row0 = False
                row79 = False
                nframe += 1

                # depth_img_array = depth_img_array / 12000.
                # depth_img_array_big = cv2.resize(depth_img_array, dsize=(1280, 320), interpolation=cv2.INTER_NEAREST)
                # cv2.imshow("test", depth_img_array)
                # cv2.waitKey(1)

                # matrix = np.random.randint(0, 100, size=(IMAGE_SIZE, IMAGE_SIZE), dtype=np.uint8)
                axim1.set_data(depth_img_array)
                fig1.canvas.flush_events()
                # print('drawn')

        if nframe >= nframes: break

    # for q in queue:
    #     # print('{:.6f}'.format(q[0]), end='\t')  # time
    #     # print(q[1], end='\t')  # frame number
    #     packet.parse(q[2])  # data
    #     packet.print()

    ser.close()


if __name__ == "__main__":
    main(sys.argv)
