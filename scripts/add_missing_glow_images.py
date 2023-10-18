# This script add glow versions of any item images that don't currently have glow versions.

# This script uses the "magick" command, which is part of ImageMagick:
# https://www.imagemagick.org/script/download.php
# You must use the version 7 or above of ImageMagick for the magick command to work properly.

import os

def add_glow_to_dir(dirname):
    glows = {}
    for file in os.listdir(os.path.join(dirname, 'glow')):
        if file.endswith('.png'):
            glows[file] = True

    for file in os.listdir(dirname):
        if file.endswith('grey.png') or file.endswith('without_glow.png') or file.endswith('Head.png') or file.startswith('soul'):
            continue
        elif file not in glows:
            if file.endswith('.png'):
                file_path = os.path.join(dirname, file)
                file_glow_path = os.path.join(dirname, 'glow', file)
                cmd = 'magick "' + file_path + '" ' +\
                      '( +clone -channel A -blur 0x2.5 -level "0,80%" +channel -fill White -colorize 100 ) -compose DstOver -composite ' +\
                      'png32:"' + file_glow_path + '"' # png32 is to set the sprite to 32-bit depth
                print(cmd)
                os.system(cmd)

paths_to_add = [
  os.path.join('.', 'collectibles'),
  os.path.join('.', 'collectibles', 'antibirth'),
  os.path.join('.', 'collectibles', 'afterbirth+'),
  os.path.join('.', 'collectibles', 'glitch'),
  os.path.join('.', 'collectibles', 'custom'),
]
for path in paths_to_add:
    print(('Scanning directory: ' + path))
    add_glow_to_dir(path)
