import c4d
import os
import os.path

import sys
import threading
import random
import time
import json
import base64

from SimpleOSC import *
from OSC import *

from c4d import gui, plugins, bitmaps
from c4d.threading import C4DThread

from collections import namedtuple

VAR_Settings = 1000

VAR_NetworkSeparator = 1010
VAR_Enabled = 1011
VAR_Address = 1012
VAR_Port = 1013
VAR_UseSendThread = 1014

VAR_ObjectSeparator = 1020
VAR_SplineResolution = 1021
VAR_ReformatCoordinates = 1022

VAR_ExportSeperator = 1030
VAR_ExportEnabled = 1031
VAR_ExportFilename = 1032
VAR_ExportNote = 1033
VAR_ExportClear = 1034

activeThreads = []

SerialiseArguments = namedtuple("SerialiseArguments", "splineResolution reformatCoordinates exportEnabled exportJson")

class OSCClientThread(C4DThread):
	client = False
	lockClient = threading.Lock()

	messageQueue = []
	lockMessageQueue = threading.Lock()

	cachedAddress = ""
	cachedPort = ""

	running = True
	useSeperateThread = False

	serialiseArguments = []

	def checkInitialise(self, newAddress, newPort, useSeperateThread, serialiseArguments):
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

					self.serialiseArguments = serialiseArguments

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
			

def Send(sender, address, variable, serialiseArguments):
	if (sender is False and serialiseArguments.exportEnabled is False):
		return
	msg = OSCMessage(address)
	if type(variable) is list:
		for item in variable:
			msg.append(item)
	else:
		msg.append(variable)

	if serialiseArguments.exportEnabled:
		serialiseArguments.exportJson.append(base64.standard_b64encode(msg.getBinary()))
	else:
		sender.sendMessage(msg)

def vectorToList(vector, reformatCoordinates):
	if reformatCoordinates:
		return [vector.x / 100.0, vector.y / 100.0, vector.z / 100.0]
	else:
		return [vector.x, vector.y, vector.z]

def FormatName(name):
	return name.replace(" ", "_")

def SerialiseObject(sender, baseAddress, object, serialiseArguments):
	# send begin
	Send(sender, baseAddress + "/begin", [], serialiseArguments)

	# send object display colour
	Send(sender, baseAddress + "/displayColor", vectorToList(object[c4d.ID_BASEOBJECT_COLOR], False), serialiseArguments);

	# get our transform
	transform = object.GetMg()

	# send object position
	position = object.GetAbsPos() * object.GetUpMg();
	Send(sender, baseAddress + "/position", vectorToList(position, serialiseArguments.reformatCoordinates), serialiseArguments)

	# if the object is a spline, then send the spline
	spline = object.GetRealSpline()
	if spline is not None:
		splineCoords = []

		if spline.GetInterpolationType() == c4d.SPLINETYPE_LINEAR:
			for iPoint in range(0, spline.GetPointCount()):
				splineCoords.append(spline.GetPoint(iPoint) * transform)
			
		else:
			for iLookup in range(0, serialiseArguments.splineResolution):
				x = float(iLookup) / float(serialiseArguments.splineResolution)
				splineCoords.append(spline.GetSplinePoint(x) * transform)
			
		if spline.IsClosed():
			splineCoords.append(spline.GetSplinePoint(0) * transform)

		splineCoordsSplit = []
		for splineCoord in splineCoords:
			splineCoordsSplit += vectorToList(splineCoord, serialiseArguments.reformatCoordinates)

		Send(sender, baseAddress + "/spline", splineCoordsSplit, serialiseArguments)

	# send any user data
	userData = object.GetUserDataContainer()
	if userData is not None:
		for descID, container in userData:
			name = container.__getitem__(1)
			name = FormatName(name)
			value = object[descID]

			sendArguments = 0

			if type(value) is c4d.Vector:
				sendArguments = vectorToList(value, serialiseArguments.reformatCoordinates)
			elif value is not None:
				sendArguments = value

			Send(sender, baseAddress + "/userData/" + name, sendArguments, serialiseArguments)

	# send any children also
	children = object.GetChildren()
	for child in children:
		SerialiseObject(sender, baseAddress + "/" + FormatName(child.GetName()), child, serialiseArguments)
	if len(children) is not 0:
		Send(sender, baseAddress + "/childCount", len(children), serialiseArguments)

	# send end
	Send(sender, baseAddress + "/end", [], serialiseArguments)
	
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
		data.SetBool(VAR_ExportEnabled, False)
		return True

	def GetVirtualObjects(self, op, hierarchyhelp):
		data = op.GetDataInstance()

		useThread = data.GetBool(VAR_UseSendThread)
		newAddress = data.GetString(VAR_Address)
		newPort = data.GetLong(VAR_Port)
		splineResolution = data.GetLong(VAR_SplineResolution)
		reformatCoordinates = data.GetBool(VAR_ReformatCoordinates)
		exportEnabled = data.GetBool(VAR_ExportEnabled)
		exportFilename = data.GetFilename(VAR_ExportFilename)
		exportJson = []
		serialiseArguments = SerialiseArguments(splineResolution = splineResolution, reformatCoordinates = reformatCoordinates, exportEnabled = exportEnabled, exportJson = exportJson)

		#check if we need to open the thread
		if self.oscClient is False:
			#if so open the thread
			self.oscClient = OSCClientThread()
			self.oscClient.Start()
			self.oscClient.checkInitialise(newAddress, newPort, useThread, serialiseArguments)
			activeThreads.append(self.oscClient)

			print "OSC : Open OSCClient"
			print "OSC : Active senders ...", activeThreads
		else:
			#otherwise update any properties
			self.oscClient.checkInitialise(newAddress, newPort, useThread, serialiseArguments)

		#send the current frame number
		doc = op.GetDocument()
		frame = doc.GetTime().GetFrame(doc.GetFps())
		Send(self.oscClient, "/frame", int(frame), serialiseArguments)

		#send object tree
		SerialiseObject(self.oscClient, "", op, serialiseArguments)

		if exportEnabled:
			try:
				jsonTotal = json.loads(open(exportFilename, 'r').read())
			except:
				jsonTotal = {}
			
			jsonTotal[frame] = exportJson
			open(exportFilename, 'w').write(json.dumps(jsonTotal))
			pass

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




























