#!/usr/bin/env python3

from PIL import Image
import numpy as np
  
img= Image.open("hybo-logo-320x80.png")
image =  ( np.asarray(img) / 60 ).astype(int)
  

for irow, row in enumerate(image):
  print('  { ', end='' )
  for pix in row:
    print( pix, end=',' )
  print(' }, // row#', irow )
