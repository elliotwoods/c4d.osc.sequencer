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
VAR_Address = 1002
VAR_Port = 1003
VAR_SplineResolution = 1004
VAR_ReformatCoordinates = 1005

activeThreads = []

class ClientThread(C4DThread):
	client = False
	lockClient = threading.Lock()

	messageQueue = []
	lockMessageQueue = threading.Lock()

	cachedAddress = ""
	cachedPort = ""

	running = True

	def checkInitialise(self, newAddress, newPort):
		with self.lockClient:
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

	def sendMessage(self, message):
		with self.lockMessageQueue:
			self.messageQueue.append(message)

	def Main(self):
		while not self.TestBreak() and self.running:
			if self.client is not False:
				messagesToSend = []
				with self.lockMessageQueue:
					messagesToSend = list(self.messageQueue)
					self.messageQueue = []
				for message in messagesToSend:
					try:
						self.client.send(message)
					except:
						pass
			
			time.sleep(0.005)

def Send(sender, address, variable):
	if (sender is False):
		return
	msg = OSCMessage(address)
	if type(variable) is list:
		for item in variable:
			msg.append(item)
	else:
		msg.append(variable)
	sender.sendMessage(msg)

def vectorToList(vector, reformatCoordinates):
	if reformatCoordinates:
		return [vector.x / 100.0, vector.y / 100.0, - vector.z / 100.0]
	else:
		return [vector.x, vector.y, vector.z]

def FormatName(name):
	return name.replace(" ", "_")

def SerialiseObject(sender, baseAddress, object, splineResolution, reformatCoordinates):
	# send begin
	Send(sender, baseAddress + "/begin", [])

	# get our transform
	transform = object.GetMg()

	# send object position
	position = object.GetAbsPos() * object.GetUpMg();
	Send(sender, baseAddress + "/position", vectorToList(position, reformatCoordinates))

	# if the object is a spline, then send the spline
	spline = object.GetRealSpline()
	if spline is not None:
		splineCoords = []

		for iLookup in range(0, splineResolution):
			x = float(iLookup) / float(splineResolution)
			splineCoords.append(spline.GetSplinePoint(x) * transform)
		
		if spline.IsClosed():
			splineCoords.append(spline.GetSplinePoint(0) * transform)

		splineCoordsSplit = []
		for splineCoord in splineCoords:
			splineCoordsSplit += vectorToList(splineCoord, reformatCoordinates)

		Send(sender, baseAddress + "/spline", splineCoordsSplit)

	# send any user data
	userData = object.GetUserDataContainer()
	if userData is not None:
		for descID, container in userData:
			name = container.__getitem__(1)
			name = FormatName(name)
			value = object[descID]

			sendArguments = 0

			if type(value) is c4d.Vector:
				sendArguments = vectorToList(value, reformatCoordinates)
			elif value is not None:
				sendArguments = value

			Send(sender, baseAddress + "/" + name, sendArguments)

	# send any children also
	children = object.GetChildren()
	for child in children:
		SerialiseObject(sender, baseAddress + "/" + FormatName(child.GetName()), child, splineResolution, reformatCoordinates)
	if len(children) is not 0:
		Send(sender, baseAddress + "/childCount", len(children))

	# send end
	Send(sender, baseAddress + "/end", [])
	
class OSCClientObject(plugins.ObjectData):
	"""OSCClientObject"""

	sendThread = False

	def __init__(self):
		self.SetOptimizeCache(True)

	def Free(self, node):
		if self.sendThread:
			self.sendThread.End()
			while self.sendThread in activeThreads: activeThreads.remove(self.sendThread)
			print "OSC : Close send thread"
			print "OSC : Active threads ...", activeThreads

	def Init(self, node):
		data = node.GetDataInstance()
		data.SetBool(VAR_Enabled, True)
		data.SetString(VAR_Address, "127.0.0.1")
		data.SetLong(VAR_Port, 4000)
		data.SetLong(VAR_SplineResolution, 200)
		data.SetBool(VAR_ReformatCoordinates, True)
		return True

	def GetVirtualObjects(self, op, hierarchyhelp):
		data = op.GetDataInstance()

		#check if we need to open the thread
		if self.sendThread is False:
			#if so open the thread
			self.sendThread = ClientThread()
			self.sendThread.Start()
			activeThreads.append(self.sendThread)

			print "OSC : Open send thread"
			print "OSC : Active threads ...", activeThreads
		else:
			#otherwise check if we need to set properties
			newAddress = data.GetString(VAR_Address)
			newPort = data.GetLong(VAR_Port)
			self.sendThread.checkInitialise(newAddress, newPort)

		#send the current frame number
		doc = op.GetDocument()
		frame = doc.GetTime().GetFrame(doc.GetFps())
		Send(self.sendThread, "/frame", int(frame))

		#send object tree
		SerialiseObject(self.sendThread, "", op, data.GetLong(VAR_SplineResolution), data.GetBool(VAR_ReformatCoordinates))

		return None

if __name__ == "__main__":
	bmp = bitmaps.BaseBitmap()
	dir, file = os.path.split(__file__)
	bitmapFilename = os.path.join(dir, "res", "kc_letter.png")

	result = bmp.InitWith(bitmapFilename)
	if not result:
		print "Error loading bitmap icon"
	
	result = plugins.RegisterObjectPlugin(id=1032063, str="OSC Client", info=c4d.OBJECT_GENERATOR | c4d.OBJECT_INPUT, g=OSCClientObject, description="OSCClientObject", icon=bmp)
	
	gitCommitFilename = os.path.join(dir, "res", "git_commit.txt")
	gitCommitFile = open(gitCommitFilename, 'r')

	print "OSC plugin initialised build: ", gitCommitFile.read()




























