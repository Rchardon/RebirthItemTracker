# This script takes png files from a directory and makes a copy that is twice the size.
# The workflow is:
# 1) Put new file images in the incoming_files_directory
# 2) Run this script
# 3) Put the files in the outgoing_files_directory in the appropriate place in collectibles/
# 4) Run add_missing_glow_images.py

# This script uses the "magick" command, which is part of ImageMagick:
# https://www.imagemagick.org/script/download.php
# You must use the version 7 or above of ImageMagick for the magick command to work properly.

import os
import sys

os.chdir("scripts")
incoming_files_directory = 'renamed_images'
outgoing_files_directory = 'resized_images'

if not os.path.isdir(incoming_files_directory):
    print(('The incoming files directory of "' + incoming_files_directory + '" does not exist.'))
    sys.exit(1)

if not os.path.isdir(outgoing_files_directory):
    os.makedirs(outgoing_files_directory)

for file in os.listdir(incoming_files_directory):
    if file.endswith('.png'):
        in_file = os.path.join(incoming_files_directory, file)
        out_file = os.path.join(outgoing_files_directory, file)
        cmd = 'magick "' + in_file + '" ' +\
              '-scale 200% png32:"' + out_file + '"' # png32 is to set the sprite to 32-bit depth
        print(cmd)
        os.system(cmd)
