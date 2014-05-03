import c4d
import os

import sys
import threading
import random
import time

from SimpleOSC import *
from OSC import *

from c4d import gui, plugins, bitmaps
from c4d.threading import C4DThread

VAR_Settings = 1000
VAR_Enabled = 1001
VAR_Scale = 1102
VAR_Resolution = 1103
VAR_Address = 1002
VAR_Port = 1003

def AppendPoint(msg, point):
	msg.append(point.x / 100.0)
	msg.append(point.y / 100.0)
	msg.append(-point.z / 100.0)

def GetFirstArg(descID):
	text = descID.__str__()
	return int(text.lstrip("(").rstrip(")").split(",")[0])

class ClientThread(C4DThread):
	client = False
	lockClient = threading.Lock()

	messageQueue = []
	lockMessageQueue = threading.Lock()

	cachedAddress = ""
	cachedPort = ""

	running = True

	def checkInitialise(self, newAddress, newPort):
		with lockClient:
			if newAddress != self.cachedAddress or newPort != self.cachedPort:
				print "OSC : Re-initialise client : ", newAddress, newPort
				try:
					self.client = OSCClient()
					self.client.connect( (newAddress, newPort ) )
					self.client.send(OSCMessage("/init"))

					self.cachedAddress = newAddress
					self.cachedPort = newPort

					print "OSC : Connected"
				except:
					 self.client = False

	def queueMessage(self, message):
		with lockMessageQueue:
			self.messageQueue.append(message)
		pass

	def Main(self):
		print "startThread"
		while not self.TestBreak() and self.running:
			empty = False
			messagesToSend = []
			with self.lockMessageQueue:
				messagesToSend = self.messageQueue
				self.messageQueue = []
			for message in messageQueue:
				self.client.send(message)
			
			time.sleep(0.005)

class OSCClientObject(plugins.ObjectData):
	"""OSCClientObject"""

	sendThread = False

	def __init__(self):
		self.SetOptimizeCache(True)
		print "init"

	def Free(self, node):
		sendThread.End()
		print "quit"

	def Init(self, node):
		data = node.GetDataInstance()
		data.SetBool(VAR_Enabled, True)
		data.SetString(VAR_Address, "127.0.0.1")
		data.SetLong(VAR_Port, 4000)

		self.sendThread = ClientThread()
		self.sendThread.Start()

		return True

	def GetVirtualObjects(self, op, hierarchyhelp):
		data = op.GetDataInstance()
		newAddress = data.GetString(VAR_Address)
		newPort = data.GetLong(VAR_Port)



		doc = op.GetDocument()
		frame = doc.GetTime().GetFrame(doc.GetFps())

		self.SendVariable("/frame", int(frame))

		children = op.GetChildren()
		childIndex = 0
		self.SendVariable("/objects/clear", 0)
		self.SendVariable("/objects/count", len(children))
		for child in children:
			spline = child.GetRealSpline()
			objectBaseAddress = "/objects/" + str(childIndex)

			if spline is not None:
				transform = child.GetMg()
				resolution = 200

				msg = OSCMessage(objectBaseAddress + "/spline")

				for iLookup in range(0, resolution):
					x = float(iLookup) / float(resolution)
					AppendPoint(msg, spline.GetSplinePoint(x) * transform)
				
				if spline.IsClosed():
					AppendPoint(msg, spline.GetSplinePoint(0) * transform)

				self.Send(msg)

			userData = child.GetUserDataContainer()
			if userData is not None:
				for descID, container in userData:
					name = container.__getitem__(1)
					name = name.replace(" ", "_")
					value = child[c4d.ID_USERDATA, GetFirstArg(descID)]
					address = objectBaseAddress + "/" + name

					if type(value) is c4d.Vector:
						msg = OSCMessage()
						AppendPoint()
						self.SendVariable(address + "/x", value.x)
						self.SendVariable(address + "/y", value.y)
						self.SendVariable(address + "/z", value.z)
					elif value is not None:
						self.SendVariable(address, value)

			childIndex += 1

		self.SendVariable("/objects/end", 0)
		self.hasDataWaiting = True
		return None

	def Send(self, msg):
		try:
			self.client.send(msg)
		except:
			pass

	def SendVariable(self, address, variable):
		msg = OSCMessage(address);
		msg.append(variable)
		if self.sendThread is not False:
			self.sendThread

if __name__ == "__main__":
	bmp = bitmaps.BaseBitmap()
	dir, file = os.path.split(__file__)
	bitmapFilename = os.path.join(dir, "res", "kc_letter.bmp")

	result = bmp.InitWith(bitmapFilename)
	if not result:
		print "Error loading bitmap icon"
	
	result = plugins.RegisterObjectPlugin(id=1032063, str="OSC Client", info=c4d.OBJECT_GENERATOR | c4d.OBJECT_INPUT, g=OSCClientObject, description="OSCClientObject", icon=bmp)
	
	gitCommitFilename = os.path.join(dir, "res", "git_commit.txt")
	gitCommitFile = open(gitCommitFilename, 'r')

	print "OSC plugin initialised build: ", gitCommitFile.read()




























