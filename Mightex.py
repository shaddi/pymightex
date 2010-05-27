#import psyco
#psyco.full()

import usb.core
import sys
import array
import numpy
from scipy import *
from PIL import Image
import time



# API for accessing a BTN-B013U camera, implemented from "Mightex Buffer USB 
# Camera USB Protocol", v1.0.5.
# By: Shaddi Hasan
# March 2010
class Camera:
	def __init__(self,res=(1280,1024),exposure_time=750,gain=4,fps=1000):

		self.dev = usb.core.find(idVendor=0x04b4,idProduct=0x0428)

		if self.dev is None:
			raise ValueError("Mightex camera not found")
		else:
			pass

		self.dev.set_configuration()
		
		# make sure we can read and write
		# not sure why this is necessary, but without this commands timeout
		r = self.dev.write(0x01,[0x21])
		r = self.dev.write(0x01,[0x21])
		r = self.dev.write(0x01,[0x21])
		r = self.dev.read(0x81,0x2e)
		
		# apply specified configuration
		self.set_mode(0x00,0x0a) # normal mode, 10-bit
		self.res = res
		self.exposure_time = exposure_time
		self.gain = gain
		self.fps = fps
		self.set_gain(self.gain)
		self.set_resolution(self.res)
		self.set_exposure_time(self.exposure_time)
		self.set_fps(self.fps)

		# wait a bit to initialize camera
		time.sleep(2)
		
		
	r"""Get the firmware version for the device. Specify
		a chip to get the firmware for: the USB controller
		("usb") or the DSP ("dsp").
	"""
	def get_firmware_version(self,chip="usb"):
		if chip=="usb":
			res = self.dev.write(0x01,[0x01])
		else: # chip=="dsp":
			res = self.dev.write(0x01,[0x02])
		res = self.dev.read(0x81,0x05)
		return res.tolist()
		
	# need to change this so you don't need to know command codes
	def set_mode(self,mode=0x00,bits=10):
		self.dev.write(0x01,[0x30,0x02,mode,bits])
		#print "Mightex set into mode " + str(mode) + ", " + str(bits) + " bits"
	
	# set the camera resolution to res[0]*res[1]
	# note: undefined, potentially hazardous, behavior if you set to an unsupported resolution
	def set_resolution(self,res):
		xres = self.int2hexlist(res[0])
		yres = self.int2hexlist(res[1])
		result = self.dev.write(0x01,[0x60,0x07,xres[0],xres[1],yres[0],yres[1],0x00,0x04,0x00])
		self.res = res # apply after setting succesfully applied
		return result
		
	# set ROI start points (xstart,ystart)
	# these need to be within the range of your resolution
	# not currently implemented; not sure how ROI is defined for this camera
	#def set_roi(self,roi):
		
	
	# set the gain for the camera.
	# range: 1-64. Input translated into actual gain, which is gain/8 (0.25x - 8x)
	# pass a 3 item list/tuple to set RGB gain, or a single value to set the 
	# gain across all three channels. 
	# TODO: multiply user input by 8 (gain of 8 is really gain of 1x (aka no gain))
	def set_gain(self,gain):
		if  getattr(gain,'__iter__',False):
			# gain is iterable, so treat as a list/tuple
			if not len(gain) == 3:
				raise ValueError("Gain tuple must consist of exactly three values")
			res = self.dev.write(0x01,[0x62,0x03,gain[0],gain[1],gain[2]])
		else:
			# single value passed in
			res = self.dev.write(0x01,[0x62,0x03,gain,gain,gain])
		self.gain = gain # apply after setting succesfully applied
		
	# set the exposure time for the camera in ms
	# range: 0.05ms - 750ms
	def set_exposure_time(self,time):
		time_mult = int(time/0.05) # base time is 0.05, camera expects a multiplier
		time_mult = self.int2hexlist(time_mult)
		self.dev.write(0x01,[0x63,0x02,time_mult[0],time_mult[1]])
		self.exposure_time = float(time)
		self.set_fps(float(1.0/(self.exposure_time/1000)))
		
	# set frames per second. camera will update its frame buffer this often on 
	# its own.
	def set_fps(self,frame_rate):
		time_mult = int(1./float(frame_rate) * float(1000)/0.05)
		time_mult = self.int2hexlist(time_mult)
		self.dev.write(0x01,[0x64,0x02,time_mult[0],time_mult[1]])
		self.fps = frame_rate
	
	# gets an image frame from the camera. returns a PIL image.
	def get_frame(self):
		frame_count = 1 # maybe make this a parameter later, if necessary
		img_len = self.res[0]*self.res[1]*2 # number of bytes in a 10-bit image
		# step 1: issue command 0x33 to check buffered images
		self.dev.write(0x01,[0x33,0x01,0x00])
		result = self.dev.read(0x81,0x08)
		
		# step 2: ensure that buffered frames match last set configurations.
		# if there is a mismatch, we need to ignore the frames.
		avail_frames = result[2]
		if self.res[0] != self.hexlist2int((result[3],result[4])) or self.res[1] != self.hexlist2int((result[5],result[6])):
			raise ValueError("Buffered frame resolution does not match expected")
		if avail_frames < frame_count:
			raise ValueError("Not enough frames in buffer, try again later.")

		# step 3: issue command 0x34 to request camera set bufferred images for retreival
		self.dev.write(0x01,[0x34,0x01,0x01])
		
		# step 4: start retreiving bufferred frames.
		# todo: support multiple frames
		raw_img = self.dev.read(0x82,img_len)
		header = self.dev.read(0x82,512)

		# step 5: translate into 1d array of pixels
		pixels = []
		for i in range(0,len(raw_img)/2):
			val = (raw_img[i+i]<<2)+(raw_img[i+i+1])
		#	val = (raw_img[2*i]<<2)+(raw_img[2*i+1])
			pixels.append(val)
		
		pixels = numpy.reshape(pixels,(self.res[1],self.res[0]),'C') # row-major order
		pil_image = misc.pilutil.toimage(pixels)
		
		return pil_image
		
		
	# execute a raw usb command
	def write(self,command,parameters):
		command_list = [command,len(parameters)]
		for i in parameters:
			command_list.append(i)
		return self.dev.write(0x01,command_list)
		
	# read raw usb data
	def read(self,length,endpoint=0x81):
		return self.dev.read(endpoint,length)
		
	# convert int to hex representation: (2 MSB, 2LSB)
	def int2hexlist(self,num):
		lsb = num & 0xff
		msb = (num & 0xff00) >> 0x8
		return [msb,lsb]
		
	def hexlist2int(self,hexlist):
		return (hexlist[0] << 0x8 + hexlist[1])

if __name__ == "__main__":
	camera = Camera()
	show = False
	# testing code
	if show:
		print camera.get_firmware_version()
		img = camera.get_frame()
		misc.pilutil.imshow(img)
		img.save("out.png","PNG")
	else:
		import timeit
		t = timeit.Timer("camera.get_frame()","from __main__ import *")
		print t.repeat(3,5)
			
