#!/usr/bin/env python2.6
from __future__ import unicode_literals, print_function, absolute_import, division
import sys
import Image
import ImageChops
import ImageEnhance
from ImageStat import Stat as ImageStat
import webbrowser
import os.path
import tempfile
import functools

BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)

def image_show(image):
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(f)
    webbrowser.open("file://" + os.path.abspath(f.name))

def image_sub(image, original, replacement):
    for x in range(image.width):
        for y in range(image.height):
            if image.data[x, y] == original:
                image.data[x, y] = replacement

def image_flood(image, x, y, color, dry=False):
    "Floods an image and returns affected pixels. Doesn't affect original if dry is set."

    if dry:
        image = prep(ImageChops.duplicate(image))

    original_color = image.data[x, y]
    width, height = image.size
        
    def flood(x, y):
        affected = 1
        
        image.data[x, y] = color

        if 1 <= x and image.data[x - 1, y] == original_color:
            affected += flood(x - 1, y)
            
        if x + 1 < width and image.data[x + 1, y] == original_color:
            affected += flood(x + 1, y)
            
        if 1 <= y and image.data[x, y - 1] == original_color:
            affected += flood(x, y - 1)
            
        if y + 1 < height and image.data[x, y + 1] == original_color:
            affected += flood(x, y + 1)

        # Diagonals too!

        if 1 <= x and 1 <= y and image.data[x - 1, y - 1] == original_color:
            affected += flood(x - 1, y - 1)
            
        if x + 1 < width and 1 <= y and image.data[x + 1, y - 1] == original_color:
            affected += flood(x + 1, y - 1)

        if 1 <= x and y + 1 < height and image.data[x - 1, y + 1] == original_color:
            affected += flood(x - 1, y + 1)
            
        if x + 1 < width and y + 1 < height and image.data[x + 1, y + 1] == original_color:
            affected += flood(x + 1, y + 1)

        return(affected)

    affected = flood(x, y)
    
    return(affected)

def prep(image):
    image.data = image.load()
    image.width, image.height = image.size
    image.show = functools.partial(image_show, image)
    image.sub = functools.partial(image_sub, image) # TODO: NUKE
    image.flood = functools.partial(image_flood, image) # TODO: NUKE
    
    return(image)

# TODO: Use a mask on the original image instead of modifying all
# of these coppies, and modularize this shit.
# Also, throw __iter__, __getitem__ and __setitem__ on preppeds.

class Captcha(object):
    def __init__(self, file_):
        self.image = prep(Image.open(file_))
        self.mask = prep(Image.new("1", self.dimensions, 0))

        self.mask_background()
        self.mask_horzontal_lines()
        self.mask_small_chunks()
        
        self.character_images = self.chunk_images()

    def mask_background(self):
        pass

    def mask_horizontal_lines(self):
        pass

    def mask_small_chunks(self):
        pass

    def chunk_images(self):
        pass
    
    def __getitem__(self, x_y):
        """Returns the value (or None if masked) of a pixel in the image."""
        
        x, y = x_y
        
        if self.mask[x, y] == 0:
            return(self.original[x, y])
        else:
            return(None)

    def __setitem__(self, x_y, value):
        """Sets the value (or mask if None) of a pixel in the image."""
        
        x, y = x_y

        if value is None:
            self.mask.data[x, y] = 1
        else:
            self.mask.data[x, y] = 0
            self.image.data[x, y] = value

    def __iter__(self):
        """Iterates the coords of each pixels in the image."""
        
        for y in range(self.height):
            for x in range(self.width):
                yield(x, y)

    @property
    def masked(self):
        """Returns an RGBA image based on original with masked areas transparent.

        They keep their original color values, their alpha is just zeroed."""

        image = prep(self.image.convert("RGBA"))

        for index in self:
            if self[index] is None:
                r, g, b, a = image[index]
                image[index] = r, g, b, 0

        return(image)
    
    @property
    def dimensions(self):
        return(self.image.dimensions)

    @property
    def width(self):
        return(self.dimensions[0])

    @property
    def height(self):
        return(self.dimensions[1])

def read_captcha(filename):
    original = Image.open(filename)
    background = tuple(ImageStat(original).median)

    # Remove the horizontal lines in the background.
    
    lines_gone = prep(ImageChops.duplicate(original))

    MIN_LINE_SIZE = 3
    
    # We look for any instances of MIN_LINE_SIZE or more
    # pixels of a non-background color in a row but with
    # constant background on either side.

    horizontal_lines = list()
    
    for y in range(lines_gone.height):
        start = None
        end = None
        color = None

        for x in range(lines_gone.width): # Why aren't ints iterable?
            if (lines_gone.data[x, y] != background and
                (y == 0 or lines_gone.data[x, y - 1] == background) and
                (y == lines_gone.height - 1 or lines_gone.data[x, y + 1] == background)):
                
                if start is None:
                    start = end = x
                    color = lines_gone.data[x, y]
                else:
                    if end == x - 1 and color == lines_gone.data[x, y]:
                        end = x
                    else:
                        if end - start >= MIN_LINE_SIZE - 1:
                            horizontal_lines.append((y, start, end))
                        start = None
                        end = None

            if start and end - start >= MIN_LINE_SIZE - 1:
                horizontal_lines.append((y, start, end))

    for y_start_end in horizontal_lines:
        y, start, end = y_start_end

        for x in range(start, end + 1):
            lines_gone.data[x, y] = background

    MAX_FILL_AREA = 128
    
    # Next we'll eliminate anything too small to be a letter.
    # We do this my looking for any "fill" areas of a given
    # color with an area less than MAX_FILL_AREA.
    smalls_gone = prep(ImageChops.duplicate(lines_gone))

    for x in range(smalls_gone.width):
        for y in range(smalls_gone.height):
            if smalls_gone.data[x, y] != background:
                if smalls_gone.flood(x, y, background, dry=True) <= MAX_FILL_AREA:
                    smalls_gone.flood(x, y, background)

    # Now that we've got nothing except the characters we
    # want, change it to white on black.
    discolored = prep(Image.new("1", smalls_gone.size, 0))

    for x in range(smalls_gone.width):
        for y in range(smalls_gone.height):
            if smalls_gone.data[x, y] == background:
                discolored.data[x, y] = 1
    
    discolored.show()

def main(filenames):
    if not filenames:
        sys.stderr.write("Usage: {0} image1 [image2...]\n".format(sys.argv[0]))
        return(1)

    for filename in filenames:
        result = read_captcha(filename)
        sys.stdout.write("{0: >8s} <- {1}\n".format(result, filename))
    
    return(0)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
