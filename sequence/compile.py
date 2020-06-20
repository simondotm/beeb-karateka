#!/usr/bin/env python
#
# Uses the Pillow fork of Python Imaging Library (PIL) - http://python-pillow.org/ 
#
# On Windows - 
#		Install Python 2.7
# 		Download ez_setup.py from https://bootstrap.pypa.io/ez_setup.py to C:\Python27
# 		run ez_setup.py
# 		From the \Python27\Scripts folder, run easy_install.exe pillow
# 
# On Mac -
#       pip install Pillow
#
# Author: simondotm
#         https://github.com/simondotm

# options
OUTPUT_FORMAT = "png"
FORCE_UPDATE = True		# has to be True atm because configs dont get build properly otherwise (TODO!)
EXO_COMPRESS = False
BEEBASM_ROOT = "gallery/"

# bbc file format
# [version]
# [mode] 
# [pixel width]
# [height in rows where 0 = 256]
# 12 x spare bytes
# 16 x BBC palette maps (index => BBC standard palette colour)
# 32 x NULA palette entries (16 x 2 bytes for NULA registers)

# ----------------
# 64 bytes total

import gzip
import struct
import sys
import binascii
import math
import json
import os
import PIL
import time

from PIL import Image
import PIL.ImageOps  
  
from os import listdir
from os.path import isfile, join
from subprocess import call



# http://pillow.readthedocs.io/en/3.0.x/handbook/image-file-formats.html


def exportMode2(imagefilename):
	image = Image.open(imagefilename)

	if image.mode != "P":
		print "Error: Not indexed format"
		return

	width, height = image.size

	print "beebimage w=" + str(width) + " h=" + str(height)


	pixel_mask = [ 
		0b00000000, 
		0b00000001, 
		0b00000100, 
		0b00000101, 
		0b00010000, 
		0b00010001, 
		0b00010100, 
		0b00010101, 
		0b01000000, 
		0b01000001, 
		0b01000100, 
		0b01000101,
		0b01010000, 
		0b01010001, 
		0b01010100, 
		0b01010101
		]

	screen_data = bytearray()

	# output header
	screen_data.append(1)	# version
	screen_data.append(2)	# mode
	screen_data.append(width)	# width
	screen_data.append(height & 0xff)	# mode
	# padding
	for n in range(0,12):
		screen_data.append(0)

	# get the palette for this image
	palette = image.getpalette()	# returns 256 rgb entries, but we only use the first 16

	# setup the bbc micro primary colours palette array
	beeb_palette = [ (0,0,0), (255,0,0), (0,255,0), (255,255,0), (0,0,255), (255,0,255), (0,255,255), (255,255,255)]

	# bbc palette map - 16 bytes
	for n in range(0,16):
		# find best fit in the beeb palette
		r1 = palette[ n*3 + 0 ]
		g1 = palette[ n*3 + 1 ]
		b1 = palette[ n*3 + 2 ]

		closest_colour = -1
		max_dist = 256*256*3
		for i in range(0,8):

			p = beeb_palette[i]

			r2 = p[0]
			g2 = p[1]
			b2 = p[2]

			dist_r = abs(r1 - r2)
			dist_g = abs(g1 - g2)
			dist_b = abs(b1 - b2)
			dist = (dist_r * dist_r) + (dist_g * dist_g) + (dist_b * dist_b)

			if dist < max_dist:
				max_dist = dist
				closest_colour = i

		# output the colour index for the beeb palette that is closest to the image palette
		#print closest_colour	
		screen_data.append(closest_colour)

	# nula palette map - 32 bytes
	for n in range(0,16):
		i = n*16 & 0xff
		r = (palette[ n*3 + 0 ] >> 4) & 0x0f
		g = (palette[ n*3 + 1 ] & 0xf0)
		b = (palette[ n*3 + 2 ] >> 4) & 0x0f

		screen_data.append( i + r )
		screen_data.append( g + b )


	for row in xrange(height / 8):
		for col in xrange(width / 2):
			for coloffset in xrange(8):
				y = row*8 + coloffset
				x = col * 2 

				#print "x=" + str(x) + ", y=" +str(y)
				p0 = image.getpixel((x+0, y))
				p1 = image.getpixel((x+1, y))

				#print "p0=" + str(p0) + ", p1=" + str(p1)
				# mode2 format is %babababa where pixels are [ab]
				byte = pixel_mask[p1] + (pixel_mask[p0]<<1)

				screen_data.append(byte)

	output_filename = imagefilename + ".bbc"
	print "writing beeb file " + output_filename
	bin_file = open(output_filename, 'wb')
	bin_file.write(screen_data)
	bin_file.close()


	if False:
		beeb_filename = os.path.basename(output_filename)
		ext_offset = beeb_filename.find(".")
		beeb_filename = beeb_filename[:ext_offset]
		beeb_filename = "A." + beeb_filename[-7:]
		# might cock up if filenames have more than 7 chars but first 7 chars are the same
	

	#file_size = os.path.getsize(output_filename) 
	#exec_address = format(0x8000 - file_size, 'x')


	if EXO_COMPRESS:
		print "Compressing with exomizer..."
		call(["exomizer", "raw", "-q", "-m", "1024", "-c", output_filename, "-o", output_filename+".exo"])
		# replace the loaded file with exo compressed version
		#output_filename += ".exo"

	if False:
		# add this file to the beeb asm config - we just give them numbers for filenames to make things easier
		file_size = os.path.getsize(output_filename) 
		load_address = format(0x8000 - file_size, 'x')
		
		num_files = beeb_asm_config.count("PUTFILE") + 1
		beeb_filename = "A." + '{num:02d}'.format(num=num_files)

		config = 'PUTFILE "' + BEEBASM_ROOT + output_filename + '", "' + beeb_filename + '", &' + load_address + ', &' + exec_address + '\n'
		beeb_asm_config += config

	#return beeb_asm_config


def updateConfig(imagefilename, beeb_asm_config):
	output_filename = imagefilename + ".bbc"
	file_size = os.path.getsize(output_filename) 
	exec_address = format(0x8000 - file_size, 'x')
	if EXO_COMPRESS:
		# replace the loaded file with exo compressed version
		output_filename += ".exo"

	# add this file to the beeb asm config - we just give them numbers for filenames to make things easier
	file_size = os.path.getsize(output_filename) 
	load_address = format(0x8000 - file_size, 'x')
	
	num_files = beeb_asm_config.count("PUTFILE") + 1
	beeb_filename = "A." + '{num:02d}'.format(num=num_files)

	config = 'PUTFILE "'  + BEEBASM_ROOT + output_filename + '", "' + beeb_filename + '", &' + load_address + ', &' + exec_address + '\n'
	beeb_asm_config += config

	return beeb_asm_config	

class AssetManager:

	_database = { "source" : "", "target" : "", "root" : {} }
	_database_filename = None

	_meta = {}
	_meta_filename = None
	
	_db_folderlist = []
	_db_source_dir = None
	_db_target_dir = None
	_db_root = None

	# constructor - pass in the filename of the VGM
	def __init__(self, database_filename):
		self._database_filename = database_filename
		if not os.path.isfile(database_filename):
			print "No database exists - creating one"
			self.saveDatabase()
		
		# load the database
		self.loadDatabase()
		self.loadMeta()

		

	
	def saveDatabase(self):
		with open(self._database_filename, 'w') as outfile:
			json.dump(self._database, outfile, sort_keys = True, indent = 4, separators = (',', ': ') )	
	
	def saveMeta(self):
		with open(self._meta_filename, 'w') as outfile:
			json.dump(self._meta, outfile, sort_keys = True, indent = 4, separators = (',', ': ') )		
	
	def loadMeta(self):
		self._meta_filename = self._db_target_dir + "/meta.json"
		if not os.path.isfile(self._meta_filename):
			print "No meta file exists - creating one"
			self.saveMeta()	
		else:
			fh = open(self._meta_filename)
			self._meta = json.loads(fh.read())			
		
	def loadDatabase(self):

		fh = open(self._database_filename)
		self._database = json.loads(fh.read())
		#print self._database

		self._db_root = self._database['root']
		self._db_source_dir = self._database['source']
		self._db_target_dir = self._database['target']

		# load folder list
		for folderkey in self._db_root:
			if not folderkey in self._db_folderlist:
				self._db_folderlist.append(folderkey)

		#print "folder list"
		#print self._db_folderlist
		
		# sync database	
		print "scanning folders"
		update_db = False
		new_folders = []
		for folder, subs, files in os.walk(self._db_source_dir):
			path = folder.replace('\\', '/')
			if path.startswith(self._db_source_dir):
				sz = len(self._db_source_dir)
				path = path[sz:]
				if len(path) > 0:
					if not path in self._db_folderlist:
						self._db_folderlist.append(path)
						new_folders.append(path)
						self._db_root[path] = {}
						update_db = True

		#print "done"

		if update_db:
			self.saveDatabase()
			print str(len(new_folders)) + " new folders detected and added to database."
			print "Apply settings if desired, then re-run script to compile."
			exit()
		
	# scan source folder looking for files that are not in the database and add them
	def scanDir(self, dir):
		print ""
	
	
	def syncDatabase(self):
		files = [f for f in listdir(sourcepath) if isfile(join(sourcepath, f))]	
	
	
	
	def compile(self):
		print "Compiling assets..."
		update_count = 0
		
		config_db = {}
		byte_stream = bytearray()

		for assetkey in self._db_root:

			asset = self._db_root[assetkey]	

			#print "'" + folder + "'"
			source_path = self._db_source_dir + assetkey + "/"
			target_path = self._db_target_dir + assetkey + "/"

			asset_is_dir = False
			if os.path.isdir(source_path):
				files = [f for f in listdir(source_path) if isfile(join(source_path, f))]
				asset_is_dir = True
				output_dir = target_path
			else:
				files = [ assetkey ]
				source_path = self._db_source_dir
				target_path = self._db_target_dir				
				output_dir = os.path.dirname(target_path + assetkey) + "/"
				#print output_dir
				#print files
			
			if output_dir not in config_db:
				config_db[output_dir] = ""

			# make the target directory if it doesn't exist
			if not os.path.exists(output_dir):
				os.makedirs(output_dir)

			# for each folder we create a beeb asm config file containing the data for each generated file
			beeb_asm_config = config_db[output_dir]

			frameId = 0
			lastImageBuffers = [ None, None ]
							
			for file in files:
			

				print "'" + file + "'"
				#print beeb_asm_config
				
				# if we're processing a directory, skip any files we come across that have been added individually to the database
				asset_file = assetkey + "/" + file
				if asset_is_dir and asset_file in self._db_root:
					#print "Skipping overridden asset"
					continue				
				
				source_file = source_path + file
				target_file = target_path + file



				# determine if we need to synchronise the asset based on :
				#     target is missing
				#     target is older than source
				#     asset meta data is absent
				#     asset settings have changed since last compile
				#
				
				update_asset = FORCE_UPDATE
				update_meta = FORCE_UPDATE
				
				# TODO: missing source file should trigger some cleanup of meta data & output files
				if isfile(source_file):
				
				
						
					# compile the image
					img = Image.open(source_file)					
					iw = img.size[0]
					ih = img.size[1]		

					if img.mode != 'RGBA' and img.mode != 'RGB':
						img = img.convert('RGB')
			
					imode = img.mode
					if imode != 'RGBA':
						imode = 'RGB'
					
					# create a new blank canvas at the target size and copy the original image to its centre
					#c = img.getpixel((0,0))	# use the top left colour of the image as the bg color
					c = (0,0,0,0) # use transparent colour as the pad bg color

					# source image is 328 x 272
					# we'll crop it to 320 x 256
					# its then resized to 80 x 64
					newimg = Image.new(imode, (320, 256), c) 
					newimg.paste(img, (-4, -8, -4+iw, -8+ih) )
					img = newimg
					
					iw = img.size[0]
					ih = img.size[1]		

					# resample the image to target size
					filter = PIL.Image.NEAREST

					ow = iw / 4
					oh = ih / 4
					img = img.resize((ow, oh), filter)


					# do a diff on the last frame



					print "diffing image"
					# take a copy of the image for differencing before we modify it
					#img_copy = Image.new(imode, (ow, oh), c) 
					#img_copy.paste(img, (0, 0, 0+ow, 0+oh) )
					img_copy = img.copy()

					# diff the image, replace same pixels with green
					# at the same time map the image to a beeb palette
					# and also dump the pixels to a binary stream


					# setup the bbc micro primary colours palette array
					beeb_palette = [ (0,0,0), (255,0,0), (0,255,0), (255,255,0), (0,0,255), (255,0,255), (0,255,255), (255,255,255)]

					def get_beeb_rgb(rgb):
						# find best fit in the beeb palette
						r1 = rgb[ 0 ]
						g1 = rgb[ 1 ]
						b1 = rgb[ 2 ]

						closest_colour = -1
						max_dist = 256*256*3
						for i in range(0,8):

							p = beeb_palette[i]

							r2 = p[0]
							g2 = p[1]
							b2 = p[2]

							dist_r = abs(r1 - r2)
							dist_g = abs(g1 - g2)
							dist_b = abs(b1 - b2)
							dist = (dist_r * dist_r) + (dist_g * dist_g) + (dist_b * dist_b)

							if dist < max_dist:
								max_dist = dist
								closest_colour = i

						# output the colour index for the beeb palette that is closest to the image palette
						#print closest_colour	
						if closest_colour < 0 or closest_colour > 15:
							print("ERROR closest colour=" + str(closest_colour))
						byte_stream.append(closest_colour & 15)
						return beeb_palette[closest_colour]


										
					#for y in xrange(oh):
					#	for x in xrange(ow):

					lastImage = lastImageBuffers[frameId]
					DIFF_FRAMES = True

					SCALE_Y = 4 # number of times we duplicate rows
					for row in xrange((oh * SCALE_Y) / 8):
						for col in xrange(ow / 1):
							for coloffset in xrange(8):
								y = (row*8 + coloffset) / SCALE_Y
								x = col * 1 


								p_new = img.getpixel((x, y))


								if DIFF_FRAMES and lastImage != None:

									p_old = lastImage.getpixel((x, y))

									# mark same pixels as green

									#print "p_new=" + str(p_new) + ", p_old=" + str(p_old)
									if p_new == p_old:
										#print "are same, now green"
										p_new = (0,255,0)

								# get_beeb_rgb also spits out the new pixel to the byte stream
								p_new = get_beeb_rgb(p_new)
								img.putpixel((x,y), p_new)

					# last image is now latest image
					lastImageBuffers[frameId] = img_copy

					frameId = (frameId + 1) & 1

					# convert to indexed palette format if required
					# TODO: should use convert - http://pillow.readthedocs.io/en/3.0.x/reference/Image.html?highlight=quantize#PIL.Image.Image.convert
					#if option_palette != 0:
					img = img.quantize(16, method=2)	
					#img = img.convert("P", colors=16, dither=0)#, colors=option_palette, dither=Image.FLOYDSTEINBERG)		
					#	#img = myquantize(img, option_palette)		
					#	#img = img




					#for y in xrange(oh):
					#	for x in xrange(ow):
					#		p = img.getpixel((x, y))
					#		byte_stream.append(p)





					# save the processed image
					ext_offset = target_file.rfind('.')
					output_filename = target_file[:ext_offset] + "." + OUTPUT_FORMAT
					img.save(output_filename, OUTPUT_FORMAT)
					#img.save("temp.png", OUTPUT_FORMAT)
					#time.sleep(0.1)	# some dodgy file access going on

					if False: #option_palette != 0:
						# -f --speed 1 --nofs --posterize 4 --output "quant\%%x" 16 "%%x"
						command_line = ["pngquant"]
						#command_line.extend(["--verbose"])
						if option_dither == 0:
							command_line.extend(["--nofs"])
						command_line.extend(["-f", "--speed", "1", "--posterize", "4"])
						#command_line.extend(["--output", output_filename, "16", output_filename])
						command_line.extend(["--output", output_filename, "16", "temp.png"])
						#print command_line
						call(command_line)
						#img = img.quantize(option_palette, method=2)	
						#img = img.convert("P", colors=2, dither=1)#, colors=option_palette, dither=Image.FLOYDSTEINBERG)		
						#img = myquantize(img, option_palette)		
						#img = img						

					if False:
						exportMode2(output_filename)
						#print beeb_asm_config
						config_db[output_dir] = beeb_asm_config

						# update asm config
						ext_offset = target_file.rfind('.')
						output_filename = target_file[:ext_offset] + "." + OUTPUT_FORMAT
						beeb_asm_config = updateConfig(output_filename, beeb_asm_config)
						#print beeb_asm_config
						config_db[output_dir] = beeb_asm_config
					
			print "Processed asset '" + assetkey + "'"


		print "Complete - updated " + str(update_count) + " files"


		# write bytestream
		bytestream_filename = "bytestream.bin"
		bin_file = open(bytestream_filename, 'wb')
		bin_file.write(byte_stream)
		bin_file.close()	

		#print "Compressing with exomizer..."
		#call(["exomizer", "raw", "-q", "-m", "1024", "-c", bytestream_filename, "-o", bytestream_filename+".exo"])		

		#print config_db
		for config in config_db:
			#print config + "config.asm"
			#print config_db[config]		
			#print	

			if True:
				#print "beebasm config " + beeb_asm_config
				config_filename = config + "config.asm"
				print "writing beebasm config file " + config_filename
				bin_file = open(config_filename, 'w')
				bin_file.write(config_db[config])
				bin_file.close()	
		

	
	
	
	

		
	
#----------------------------------------------------------------------------------------------------------------------------
# main
#----------------------------------------------------------------------------------------------------------------------------
	
	
asset_manager = AssetManager("assets.json")
asset_manager.compile()


# hacky script to auto-update the readme with thumbnails of the converted images
if False:

	rootdir = "output/"
	my_file = "../readme.md"

	gallery_md = '\n'

	for root, directories, filenames in os.walk(rootdir):
		#for directory in directories:
		#    print os.path.join(root, directory) 
		volume = root[root.rfind('/')+1:]
		if len(volume) > 0:
			gallery_md += '\n### ' + volume + '\n\n<p float="left">'

		for filename in filenames: 
			if filename[-4:] == '.png':
				f = os.path.join(root,filename) 
				f = f.replace('\\', '/')
				f = f.replace(rootdir, '')
				s = '<img src="https://github.com/simondotm/bbc-nula/raw/master/gallery/output/' + f + '" width="160" height="128" /> '
				gallery_md += s 

		if len(volume) > 0:
			gallery_md += "\n</p>\n\n"

	file = open(my_file, "r")
	readme = file.read()
	offset = readme.find("<meta>")
	readme = readme[:offset+6]
	readme += gallery_md
	file = open(my_file, "w")
	file.write(readme)

	print "readme.md updated."