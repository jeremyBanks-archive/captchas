#!/usr/bin/env python2.6
from __future__ import unicode_literals, print_function, absolute_import, division

from copy import *
import Image # We'll add .prep and .show to this.
import ImageChops
import ImageFilter
import ImageStat
import collections
import functools
import os.path
import random
import subprocess
import sys
import tempfile
import webbrowser
import codecs

sys.stdout = codecs.getwriter("utf-8")(sys.stdout)

def ocr(image):
    with tempfile.NamedTemporaryFile(suffix=".bmp") as f:
        image.save(f.name)
        subprocess.Popen(["tesseract", f.name, "/tmp/locr"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE).communicate()
        return(codecs.open("/tmp/locr.txt", "rt", "utf-8").read()
               .replace("0", "O")
               .strip()
               .upper())

# TODO: Make code better. Break stuff up some more.

class Captcha(object):
    """Throw this an image file containing a CATCHPA and it'll put it's best guess in .value."""
    
    def __init__(self, file_):
        self.image = Image.prep(Image.open(file_).convert("RGB"))
        self.mask = Image.prep(Image.new("1", self.dimensions, False))
        self.characters = [] # filled in mask_crap_and_find_characters
        
        self.mask_background()
        self.mask_horizontal_lines()        
        self.mask_crap_and_find_characters()
        
        self.align_characters()
        self.scale_characters()
        self.interpret_characters() # Return and into self.value

    def mask_background(self):
        """Masks all pixels with the median pixel value in the image."""

        background = tuple(ImageStat.Stat(self.image).median)
        
        for index in self:
            
            if self[index] == background:
                self[index] = None

    MIN_LINE_LENGTH = 8
    
    def mask_horizontal_lines(self):
        """Masks monocolored horizontal lines at least MIN_LINE_LENGTH in length in the image.

        Lines to be masked must have masked pixels or edges above and below them."""

        horizontal_lines = list()

        for y in range(self.height):
            start = None

            for x in range(self.width):
                if (self[x, y] is not None and
                    self[x, y - 1] is None and
                    self[x, y + 1] is None):

                    if start is None:
                        start = end = x
                        color = self[x, y]
                    else:
                        if end == x - 1 and color == self[x, y]:
                            end = x
                        else:
                            if end - start + 1 >= self.MIN_LINE_LENGTH:
                                horizontal_lines.append((y, start, end))
                            start = None

                if start and end - start + 1 >= self.MIN_LINE_LENGTH:
                    horizontal_lines.append((y, start, end))

        for y_start_end in horizontal_lines:
            y, start, end = y_start_end

            for x in range(start, end + 1):
                self[x, y] = None

    def chunk(self, start, ignore_color=False):
        """Returns a set of indicies of an unmasked chunk."""

        original = self[start]
        
        if original is None:
            return(set())
        
        indicies = set( (start,) ) # our result
        unchecked = set( (start,) ) # indicies we haven't scanned around

        while unchecked:
            index = unchecked.pop()
            
            for d_x in (-1, 0, +1):
                for d_y in (-1, 0, +1):
                    if d_x or d_y:
                        next = (index[0] + d_x, index[1] + d_y)
                        
                        if (next not in indicies and
                            ((ignore_color and self[next] is not None) or
                             self[next] == original)):
                            indicies.add(next)
                            unchecked.add(next)
        
        return(indicies)

    def all_chunks(self, ignore_color=False):
        """Returns an iterable of the index sets of all chunks in the image."""
        
        exclusion = set() # previously-chunked cells
        
        for index in self:
            if self[index] is not None and index not in exclusion:
                chunk = self.chunk(index, ignore_color)
                
                exclusion.update(chunk)

                yield(chunk)
    
    MIN_CHUNK_AREA = 128

    def mask_crap_and_find_characters(self):
        """Masks all monocolored chunks in the image with an area less than MIN_CHUNK_AREA."""

        character_chunks = []
        
        for chunk in self.all_chunks():
            if len(chunk) < self.MIN_CHUNK_AREA:
                for index in chunk:
                    self[index] = None
            else:
                character_chunks.append(chunk)

        self.characters = map(self.chunk_image_mask,
                              sorted(character_chunks,
                                     key=lambda indicies: min(x for x, y in indicies)))

    def chunk_image_mask(self, chunk, ignore_color=False):
        """Returns a B&W image of the pixels in a chunk, cropped to fit.

        The pixels that fit into the crop but are not in the chunk are
        masked, but their colour values are preserved."""

        min_x = None
        max_x = None
        min_y = None
        max_y = None

        for index in chunk:
            x, y = index

            if min_x is None or x < min_x:
                min_x = x
            if max_x is None or x > max_x:
                max_x = x
            if min_y is None or y < min_y:
                min_y = y
            if max_y is None or y > max_y:
                max_y = y

        image = Image.prep(Image.new("1", (max_x - min_x + 1,
                                           max_y - min_y + 1)))
        
        for x in range(image.width):
            for y in range(image.height):
                image.data[x, y] = (min_x + x, min_y + y) in chunk
        
        return(image)

    MIN_ROTATION = -120
    MAX_ROTATION = +120
    
    def align_characters(self):
        """Rotates character images to the correct alignment.

        This is determined by finding the orientation within MAX_ROTATION
        rotations with the minimum area that produces an image taller than
        it is wide."""

        new_characters = []
        
        for character in self.characters:
            best_width = None
            best_area = None
            
            for angle in range(self.MIN_ROTATION, self.MAX_ROTATION + 1):
                rotated = Image.prep(character.rotate(angle, Image.NEAREST,
                                                      expand=True))

                min_x = 0
                max_x = rotated.width - 1
                min_y = 0
                max_y = rotated.height - 1
                
                for x in range(rotated.width):
                    if any(rotated.data[x, y] for y in range(rotated.height)):
                        break
                    else:
                        min_x = x

                for _x in range(rotated.width):
                    x = rotated.width - 1 - _x
                    
                    if any(rotated.data[x, y] for y in range(rotated.height)):
                        break
                    else:
                        max_x = x

                for y in range(rotated.height):
                    if any(rotated.data[x, y] for x in range(rotated.width)):
                        break
                    else:
                        min_y = y

                for _y in range(rotated.height):
                    y = rotated.height - 1 - _y
                    
                    if any(rotated.data[x, y] for x in range(rotated.width)):
                        break
                    else:
                        max_y = y

                width = max_x - min_x + 1
                height = max_y - min_y + 1

                area = (width ** 1.2) * height
                
                if best_area is None or (area < best_area and width < height):
                    best_area = area
                    best_image = rotated
                    best_box = (min_x, min_y, max_x, max_y)

            new_characters.append(Image.prep(best_image.crop(best_box)))

        self.characters = new_characters

    def scale_characters(self):
        max_height = max(i.height for i in self.characters) # TODO: Should this be a constant?
        max_width = max(i.width for i in self.characters) # :-/
        
        scaled_characters = []

        for character in self.characters:
            width = character.width * (max_height / character.height)
            
            if width > max_width:
                width = max_width
                height = int(character.height * (width / character.width))
            else:
                width = int(width)
                height = max_height
            
            scaled_characters.append(Image.prep
                                     (character
                                      .convert("L")
                                      .resize((width, height),
                                              Image.BICUBIC).convert("1")))

        self.characters = scaled_characters

    CHARACTER_PADDING = 16
    
    def interpret_characters(self):
        """Attempts to return the string of characters represented by the character images."""

        max_height = max(i.height for i in self.characters) # TODO: Should this be a constant?
        
        # We put the characters in an image, each CHARACTER_PADDING from the bottom.
        
        width = (sum(i.width for i in self.characters) +
                 self.CHARACTER_PADDING * (len(self.characters) + 1))
        height = max_height + self.CHARACTER_PADDING * 2

        image = Image.prep(Image.new("L", (width, height), 0))

        x_offset = self.CHARACTER_PADDING
        
        for character in self.characters:
            y_offset = height - self.CHARACTER_PADDING - character.height
            
            image.paste(character, (x_offset, y_offset,
                                    x_offset + character.width,
                                    y_offset + character.height))
            
            x_offset += character.width + self.CHARACTER_PADDING

        image = Image.prep(image
                           .filter(ImageFilter.MaxFilter(3))
                           .filter(ImageFilter.ModeFilter(3))
                           )

        self.value = ocr(image)
        return(self.value)

    @property
    def masked(self):
        """Returns an RGBA image based on original with masked areas transparent.

        They keep their original color values, their alpha is just zeroed."""

        image = Image.prep(self.image.convert("RGBA"))

        for index in self:
            if self[index] is None:
                r, g, b, a = image.data[index]
                image.data[index] = r, g, b, False

        return(image)
    
    def __getitem__(self, x_y):
        """Returns the value (or None if masked or out of bounds) of a pixel in the image."""
        
        x, y = x_y
        
        if 0 <= x < self.width and 0 <= y < self.height and self.mask.data[x, y] == False:
            return(self.image.data[x, y])
        else:
            return(None)

    def __setitem__(self, x_y, value):
        """Sets the value (or mask if None) of a pixel in the image."""
        
        x, y = x_y

        if value is None:
            self.mask.data[x, y] = True
        else:
            self.mask.data[x, y] = False
            self.image.data[x, y] = value

    def __iter__(self):
        """Iterates the coords of each pixels in the image."""
        
        for y in range(self.height):
            for x in range(self.width):
                yield(x, y)

    @property
    def dimensions(self):
        return(self.image.size)

    @property
    def width(self):
        return(self.dimensions[0])

    @property
    def height(self):
        return(self.dimensions[1])

def __Image_show(image):
    """Saves an image to a temporary file and opens it in a web browser."""
    
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(f)
    webbrowser.open("file://" + os.path.abspath(f.name))

Image.show = __Image_show

def __Image_prep(image):
    """Makes an image object slightly nicer to work with.

    - Loads the image and put the access object in .data.
    - Sets .width and .height from .size.
    - Adds a .show() that should work anywhere."""
    
    image.data = image.load()
    image.width, image.height = image.size
    image.show = functools.partial(Image.show, image)
    
    return(image)

Image.prep = __Image_prep

def main(filenames):
    if not filenames:
        sys.stderr.write("Usage: {0} image1 [image2...]\n".format(sys.argv[0]))
        return(1)

    hits = 0
    total = 0
    
    for filename in filenames:
        correct = filename.rpartition("/")[2].partition(".")[0]
        captcha = Captcha(filename)

        hit = correct == captcha.value

        if hit:
            hits += 1
        total += 1
        
        sys.stdout.write("{2} {0: >8s} <- {1}\n".format(captcha.value, filename, "+" if hit else "-"))

    print("\n{0} hits out of {1} attempts ({2:.1f}%)"
          .format(hits, total, hits / total * 100))
    
    return(0)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
