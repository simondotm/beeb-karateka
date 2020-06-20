

import sys
import os
from subprocess import call

bytestream_filename = "bytestream.bin"
bytestream_filename_rle = "bytestream.bin.rle"
bytestream_filename_exo = "bytestream.bin.rle.exo"


SCALE_Y = 4

# given a block of bytes of 4-bit values, compress two bytes to 1
def pack4(block):
    packed_block = bytearray()

    for x in range(0, len(block), 2):
        a = block[x+0] & 15
        if x+1 >= len(block):
            b = 0
        else:
            b = block[x+1] & 15
        c = (a << 4) + b
        packed_block.append(c)
    return packed_block



# run length encoded into top 4-bits. 0=no repeat, 15=15 repeats.
def rle4(block):

    rle_block = bytearray()
    n = 0
    while (n < len(block)):
        #print('offset ' + str(n))
        offset = n
        count = 0
        while ((offset < len(block)-1) and (count < 15)):
            #print('diff[' + str(offset+1) + ']='+str(block[offset+1]))
            if block[offset+1] == block[n]:
                count += 1 
                offset += 1
            else:
                #print('ack')
                break

        out = ((count&15)<<4) | (block[n] & 15)
        rle_block.append( out )
        n += count + 1
        #if count > 0:
        #		print('run length ' + str(count) + " of " + format(out, 'x'))

    print('   RLE Pack size in=' + str(len(block)) + ', out=' + str(len(rle_block)) + ", saving=" + str(len(block)-len(rle_block)) )
    return rle_block

# run length encoded into 8-bits. 0 = no repeat
def rle8(block):

    rle_block = bytearray()
    n = 0
    while (n < len(block)):
        offset = n
        count = 0
        match = block[n]
        while ((offset < len(block)-1) and (count < 255)):
            if block[offset+1] == match:
                count += 1 
                offset += 1
            else:
                break

        if match > 7:
            print(' ERROR MATCH')

        rle_block.append( count & 255 )
        rle_block.append( match & 255 )

        #print('run length ' + format(count, 'x') + " of " + format(match, 'x') + ", length " + str(len(rle_block)) )

        n += count + 1

    print('   RLE Pack size in=' + str(len(block)) + ', out=' + str(len(rle_block)) + ", saving=" + str(len(block)-len(rle_block)) )

    return rle_block




# run length encoded into top 4-bits. 0=no repeat (+4 writes), 1=+4 repeats, 15=+15*4 repeats.
def rle44(block):

    rle_block = bytearray()
    n = 0
    while (n < len(block)):
        #print('offset ' + str(n))
        offset = n
        count = 0
        match = block[n]

        while ((offset < len(block)-1) and (count < 63)):
            #print('diff[' + str(offset+1) + ']='+str(block[offset+1]))
            if block[offset+1] == match:
                count += 1 
                offset += 1
            else:
                #print('ack')
                break

        shifted_count = count>>2
        out = ((shifted_count&15)<<4) | (match & 15)
        rle_block.append( out )
        n += count + 1

        #print('run length ' + str(count) + " of " + format(match, 'x') + ", offset=" + str(n))

        #if count > 0:
        #		print('run length ' + str(count) + " of " + format(out, 'x'))

    print('   RLE Pack size in=' + str(len(block)) + ', out=' + str(len(rle_block)) + ", saving=" + str(len(block)-len(rle_block)) )
    return rle_block




# run length encoded into top 5-bits. 0=no repeat (+4 writes), 1=+4 repeats, 31=+31*4 repeats.
# bottom 3 bits are the data 
def rle54(block):

    rle_block = bytearray()
    n = 0
    while (n < len(block)):
        #print('offset ' + str(n))
        offset = n
        count = 0
        match = block[n]

        while ((offset < len(block)-1) and (count < 127)):
            #print('diff[' + str(offset+1) + ']='+str(block[offset+1]))
            if block[offset+1] == match:
                count += 1 
                offset += 1
            else:
                #print('ack')
                break

        shifted_count = count>>2
        out = ((shifted_count&31)<<3) | (match & 7)
        rle_block.append( out )
        n += count + 1

        #print('run length ' + str(count) + " of " + format(match, 'x') + ", offset=" + str(n))

        #if count > 0:
        #		print('run length ' + str(count) + " of " + format(out, 'x'))

    print('   RLE Pack size in=' + str(len(block)) + ', out=' + str(len(rle_block)) + ", saving=" + str(len(block)-len(rle_block)) )
    return rle_block


# read the bytestream & rle pack it
bin_file = open(bytestream_filename, 'rb')
raw_byte_stream = bytearray(bin_file.read())
bin_file.close()	


# we have to pack in frame chunks otherwise RLE coding will overrun frames
frame_size = 80*256

frame_count = len(raw_byte_stream)/frame_size
byte_stream = bytearray()

print("RLE Packing " + str(frame_count) + " frames, frame size " + str(frame_size))

for f in range(frame_count):

    print(" - Packing frame " + str(f))

    offset_begin = f*frame_size
    offset_end = offset_begin + frame_size - 1
    frame_data = raw_byte_stream[offset_begin:offset_end]


    #rle_byte_stream = rle4(frame_data)
    #rle_byte_stream = rle44(frame_data)
    # 5 bits run + 3 bits data gives best perf/comp tradeoff
    rle_byte_stream = rle54(frame_data)

    byte_stream.extend(rle_byte_stream)



bin_file = open(bytestream_filename_rle, 'wb')
bin_file.write(byte_stream)
bin_file.close()	

# exo compress the rle file
print "Compressing with exomizer..."
call(["exomizer", "raw", "-q", "-m", "1024", "-c", bytestream_filename_rle, "-o", bytestream_filename_exo])		

# split exo data into 16Kb bank files
bin_file = open(bytestream_filename_exo, 'rb')
exo_stream = bin_file.read()
bin_file.close()	

bin_file1 = open(bytestream_filename_exo + ".1", 'wb')
bin_file1.write(exo_stream[0:16384])
bin_file1.close()	

bin_file2 = open(bytestream_filename_exo + ".2", 'wb')
bin_file2.write(exo_stream[16384:32768])
bin_file2.close()	

bin_file3 = open(bytestream_filename_exo + ".3", 'wb')
bin_file3.write(exo_stream[32768:])
bin_file3.close()	


