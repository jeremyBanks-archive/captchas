#!/usr/bin/env python3.1
import sys
import struct

def bitmask(low, high=None):
    """Zero-indexed, eh?"""
    
    if high is None:
        high = low
        
    result = 0

    for n in range(low, high + 1):
        result += 1 << n
        
    return(result)

BM = bitmask

class gif87a(object):
    def __init__(self, filename):
        """Load an image from that damn file.

        This may print error messages, but never throws exceptions."""
        
        with open(filename, "rb") as f:
            def read(format):
                result = struct.unpack(format, f.read(struct.calcsize(format)))

                if len(result) == 1:
                    return(result[0])
                else:
                    return(result)

            
            signature = read("6s") # Ignored
            width, height = read("2h")            
            temp = read("B") # Ignored

            has_color_table = bool(temp & BM(7)) # Ignored, True assumed
            color_resolution = ((temp & BM(4, 6)) >> 4) + 1 # ?
            bitrate = (temp & BM(0, 3)) + 1 # Somewhat ignored?
            
            bgindex = read("b")
            zero = read("b") # Ignored

            colors = list()

            for n in range(2 ** bitrate):
                colors.append(read("BBB"))

            background = colors[bgindex]

            # We're also only reading the first frame/image.

            seperator = read("c") # Ignored, assumed b","

            self.width, self.height = width, height
            self.data = [ background ] * (width * height)
            
            x_offset = read("h")
            y_offset = read("h")
            my_width = read("h")
            my_height = read("h")

            temp = read("B")

            has_color_map = bool(temp & BM(7)) # Ignored, assumed False
            interlaced = bool(temp & BM(6)) # Ignored, assumed False
            image_bitrate = temp & BM(0, 2) + 1 # Ignored

            # Decompress now

            decompressed = bytearray()

            code_size = read("B")

            clear_code = 2 ** code_size
            e_o_i_code = clear_code + 1
            
            block_size = read("B")

            while block_size:
                block = f.read(block_size)

                for b in block:
                    print("Fuck my life and go die in a fire.")                    
                break
                
                block_size = read("B")                
            

            i = 0

            for y in range(y_offset, y_offset + my_height):
                for x in range(x_offset, x_offset + my_width):
                    self[x, y] = colors[struct.unpack("B", decompressed[i])]
                    
                    i += 1
                    


    def __getitem__(self, key):
        x, y = key
        return(self.data[y * self.width + x])

    def __setitem__(self, key, value):
        x, y = key
        self.data[y * self.width + x] = value
                
            
            
            

def main():
    import gif
    
    print(gif.gif87a(("image.gif")))

def __main__(function, path, user_args):
    """Wraps a main function to display a usage message when necessary."""
    
    co = function.__code__
    
    num_args = co.co_argcount

    if function.__defaults__ is not None:
        min_args = num_args - len(function.__defaults__)
    else:
        min_args = num_args
    
    if co.co_flags & 0x04: # function captures extra arguments with *
        max_args = None
    else:
        max_args = num_args
    
    if min_args <= len(user_args) and (max_args is None or
                                       max_args >= len(user_args)):
        return(function(*user_args))

    if max_args == 0:
        sys.stderr.write("Usage: {path}\n".format(path=path))
    else:
        arg_list = list()
        optionals = 0
        
        for index in range(num_args):
            if index < min_args:
                arg_list.append(co.co_varnames[index])
            else:
                arg_list.append("[" + co.co_varnames[index])
                optionals += 1
                
        if max_args is None:
            arg_list.append("[" + co.co_varnames[num_args] + "...")
            optionals += 1
            
        sys.stderr.write("Usage: {path} {args}{optional_closes}\n".format
                         (path=path,
                          args=" ".join(arg_list),
                          optional_closes="]" * optionals))
    if function.__doc__:
        sys.stderr.write("\n")
        sys.stderr.write(function.__doc__)
        sys.stderr.write("\n")
    
    return(1)

if __name__ == "__main__":
    sys.exit(__main__(main, sys.argv[0], sys.argv[1:]))
