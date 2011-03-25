import psyco
psyco.full()

# Please see included README for license details.
# In short, it's BSD licensed. Enjoy!

from Mightex import *
from Tkinter import *
from PIL import Image, ImageTk, ImageOps, ImageStat

# Based on prasannagautam's StreamViewer.py in mjpeg-stream-client
class Viewer(Frame):
	def __init__(self,root,camera):
		self.camera = camera
		self.root = root
		self.root.title("Mightex Viewer")
		self.addFrame(self.root)
		
		self.streaming = True
		self.thresholding = True
		
		
	def addFrame(self,root):
		frame = Frame(root,  background="#FFFFFF")
		self.addCanvas(frame)
		self.b1 = Button(frame,text="Stream",command=self.toggleStream)
		self.b1.pack(fill=X,side=BOTTOM)
		self.b2 = Button(frame,text="Threshold",command=self.toggleThreshold)
		self.b2.pack(fill=X,side=BOTTOM)
		frame.pack(fill=BOTH, expand=YES)
        
	def addCanvas(self, frame):
		self.canvas = Canvas(frame, background='#000000')
		self.canvas.pack(fill=BOTH, expand=YES)
		self.canvas.pack()

	def addImage(self, photoimage):
		self.canvas.create_image(640,480, image=photoimage,anchor=SE)

	def toggleStream(self):
		self.streaming = not self.streaming
		
	def toggleThreshold(self):
		self.thresholding = not self.thresholding


if __name__ == '__main__':
	img = None
	def update_viewer(viewer,root,camera):
		global img
		if viewer.streaming:
			img = camera.get_frame()
		if viewer.thresholding:
			#imgt = ImageOps.autocontrast(img,40)
			imgstat = ImageStat.Stat(img)
			#thresh = imgstat.mean[0] + 3*imgstat.stddev[0]
			thresh = 200
			imgt = img.point(lambda i: 0 if i<thresh else 255, "L")
			imgtk = ImageTk.PhotoImage(imgt)
		else:
			imgtk = ImageTk.PhotoImage(img)
		viewer.addImage(imgtk)
		root.update()
		return img

	root = Tk()
	root.geometry("%dx%d+0+0" % (640,525))
	root.resizable(False,False)
	c = Camera()
	c.set_exposure_time(50.0)
	v = Viewer(root,c)

	while(True):
		update_viewer(v,root,c)
