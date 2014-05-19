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
VAR_UseSendThread = 1006

activeThreads = []

class OSCClientThread(C4DThread):
	client = False
	lockClient = threading.Lock()

	messageQueue = []
	lockMessageQueue = threading.Lock()

	cachedAddress = ""
	cachedPort = ""

	running = True
	useSeperateThread = False

	def checkInitialise(self, newAddress, newPort, useSeperateThread):
		self.useSeperateThread = useSeperateThread
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
					print "OSC : Failed to open thread"
					self.client = False

	def sendMessage(self, message):
		if self.useSeperateThread:
			with self.lockMessageQueue:
				self.messageQueue.append(message)
		else:
			with self.lockClient:
				if self.client is not False:
					try:
						self.client.send(message)
					except:
						pass
				else:
					print "OSC : Cannot send message, OSCCLient.client is not set"

	def Main(self):
		while not self.TestBreak() and self.running:
			if self.useSeperateThread:
				hasClient = False
				with self.lockClient:
					hasClient = self.client is not False
				if hasClient:
					messagesToSend = []
					with self.lockMessageQueue:
						messagesToSend = list(self.messageQueue)
						self.messageQueue = []
					for message in messagesToSend:
						try:
							self.client.send(message)
						except:
							pass
				else:
					time.sleep(0.005)
			else:
				time.sleep(0.010)
			

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
				sendArguments = vectorToList(value, False)
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

	oscClient = False

	def __init__(self):
		self.SetOptimizeCache(True)

	def Free(self, node):
		if self.oscClient:
			self.oscClient.End()
			while self.oscClient in activeThreads:
				activeThreads.remove(self.oscClient)
			print "OSC : Close send thread"
			print "OSC : Active threads ...", activeThreads

	def Init(self, node):
		data = node.GetDataInstance()
		data.SetBool(VAR_Enabled, True)
		data.SetString(VAR_Address, "127.0.0.1")
		data.SetLong(VAR_Port, 4000)
		data.SetLong(VAR_SplineResolution, 200)
		data.SetBool(VAR_ReformatCoordinates, True)
		data.SetBool(VAR_UseSendThread, False)
		return True

	def GetVirtualObjects(self, op, hierarchyhelp):
		data = op.GetDataInstance()

		useThread = data.GetBool(VAR_UseSendThread)
		newAddress = data.GetString(VAR_Address)
		newPort = data.GetLong(VAR_Port)

		#check if we need to open the thread
		if self.oscClient is False:
			#if so open the thread
			self.oscClient = OSCClientThread()
			self.oscClient.Start()
			self.oscClient.checkInitialise(newAddress, newPort, useThread)
			activeThreads.append(self.oscClient)

			print "OSC : Open OSCClient"
			print "OSC : Active senders ...", activeThreads
		else:
			#otherwise update any properties
			self.oscClient.checkInitialise(newAddress, newPort, useThread)

		#send the current frame number
		doc = op.GetDocument()
		frame = doc.GetTime().GetFrame(doc.GetFps())
		Send(self.oscClient, "/frame", int(frame))

		#send object tree
		SerialiseObject(self.oscClient, "", op, data.GetLong(VAR_SplineResolution), data.GetBool(VAR_ReformatCoordinates))

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




























