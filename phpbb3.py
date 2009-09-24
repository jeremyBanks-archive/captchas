#!/usr/bin/env python2.6
from __future__ import unicode_literals, print_function, absolute_import, division
import Image
import ImageChops
import ImageEnhance
import ImageStat
import functools
import os.path
import sys
import tempfile
import webbrowser

def image_show(image):
    """Saves an image to a temporary file and opens it in a web browser."""
    
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(f)
    webbrowser.open("file://" + os.path.abspath(f.name))


def read_captcha(filename):
    original = Image.open(filename)
    background = tuple(ImageStat.Stat(original).median)

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
    """Makes an image object slightly nicer to work with.

    - Loads the image and put the access object in .data.
    - Sets .width and .height from .size.
    - Adds a .show() that should work anywhere."""
    
    image.data = image.load()
    image.width, image.height = image.size
    image.show = functools.partial(image_show, image)
    
    return(image)

class Captcha(object):
    """Throw this an image file containing a CATCHPA and it'll put it's best guess in .value."""
    
    def __init__(self, file_):
        self.image = prep(Image.open(file_).convert("RGB"))
        self.mask = prep(Image.new("1", self.dimensions, 0))

        self.mask_background()
        self.mask_horzontal_lines()
        self.mask_small_chunks()
        
        self.characters = self.chunk_images()
        self.align_characters()

        self.value = self.interpret_characters()

    def mask_background(self):
        """Masks all pixels with the median pixel value in the image."""

    MIN_LINE_LENGTH = 3
    
    def mask_horizontal_lines(self):
        """Masks monocolored horizontal lines at least MIN_LINE_LENGTH in length in the image.

        Lines to be masked must have masked pixels or edges above and below them."""

    MIN_CHUNK_AREA = 128
    
    def mask_small_chunks(self):
        """Masks all monocolored chunks of the image with an area less than MIN_CHUNK_AREA."""

    def chunk_images(self):
        """Return an iterable of images of each unmasked chunk in the image.

        Rembember that this ignores color information and acts only based on masks."""

    MAX__ROTATION = .25
    
    def align_characters(self):
        """Rotates character images to the correct alignment.

        This is determined by finding the orientation within MAX_ROTATION
        rotations with the minimum area that produces an image taller than
        it is wide."""

    def interpret_characters(self):
        """Attempts to return the string of characters represented by the character images."""

        return("NO IDEA") # good fucking luck.
    
    def __getitem__(self, x_y):
        """Returns the value (or None if masked or out of bounds) of a pixel in the image."""
        
        x, y = x_y
        
        if 0 <= x < self.width and 0 <= y < self.height and self.mask[x, y] == 0:
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

def main(filenames):
    if not filenames:
        sys.stderr.write("Usage: {0} image1 [image2...]\n".format(sys.argv[0]))
        return(1)

    for filename in filenames:
        captcha = Captcha(filename)        
        sys.stdout.write("{0: >8s} <- {1}\n".format(captcha.value, filename))
    
    return(0)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
