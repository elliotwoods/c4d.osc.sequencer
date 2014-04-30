import c4d
import os

import sys
import random
import time

import SimpleOSC

from c4d import gui, plugins, bitmaps

VAR_Settings = 1000
VAR_Enabled = 1001
VAR_Scale = 1102
VAR_Resolution = 1103
VAR_Address = 1002
VAR_Port = 1003

class OSCClientObject(c4d.plugins.ObjectData):
	"""OSCClientObject"""

	client = 0
	cachedAddress = ""
	cachedPort = ""

	def Init(self, node):
		data = node.GetDataInstance()
		data.SetBool(VAR_Enabled, True)
		data.SetString(VAR_Address, "127.0.0.1")
		data.SetLong(VAR_Port, 4000)
		return True

	def AddToExecution(self, op, list):
		print "add to exec queue"
		list.Add(op, c4d.EXECUTIONPRIORITY_INITIAL, 0)
		list.Add(op, c4d.EXECUTIONPRIORITY_ANIMATION, 0)
		list.Add(op, c4d.EXECUTIONPRIORITY_EXPRESSION, 0)
		list.Add(op, c4d.EXECUTIONPRIORITY_GENERATOR, 0)
		return True

	def Execute(self, op, doc, bt, priority, flags):
		print "exec client object"
		data = node.GetDataInstance()
		newAddress = data.GetString(VAR_Address)
		newPort = data.GetLong(VAR_Port)

		if newAddress != self.cachedAddress or newPort != self.cachedPort:
			self.cachedAddress = newAddress
			self.newPort = newPort
			client = OSCClient()
			client.connect(newAddress, newPort)

			msg = OSCMessage("/init")
			client.send(msg)
			print msg

		frame = doc.GetTime().GetFrame(doc.GetFps())
		print frame
		return c4d.EXECUTIONRESULT_OK

class OSCSplineTag(c4d.plugins.TagData):
	"""OSCSplineTag"""

	def Init(self, node):
		tag = node
		data = tag.GetDataInstance()

		data.SetBool(VAR_Enabled, False)
		data.SetLong(VAR_Scale, 7)
		data.SetLong(VAR_Resolution, 4)
		return True

	def Execute(self, tag, doc, op, bt, priority, flags):
		print "exec spline tag"
		data = tag.GetDataInstance()
		ourTransform = op.GetMg()
		spline = op.GetRealSpline()
		client = op.GetUp()
		fail = False
		if client is None:
			fail = True

		if spline is None:
			fail = True

		if fail:
			print "Please use OSC Spline Tag on spline objects "
			return EXECUTIONRESULT_OK
		
		resolution = data.GetLong(VAR_Resolution)

		for iLookup in range(0, resolution):
			x = float(iLookup) / float(resolution)
			point = spline.GetSplinePoint(x) * ourTransform / 100.0
			# print point

		return c4d.EXECUTIONRESULT_OK

if __name__ == "__main__":
	bmp = bitmaps.BaseBitmap()
	dir, file = os.path.split(__file__)
	bitmapFilename = os.path.join(dir, "res", "kc_letter.bmp")

	result = bmp.InitWith(bitmapFilename)
	if not result:
		print "Error loading bitmap icon"

	result = plugins.RegisterTagPlugin(id=1032062, str="OSC Spline Tag", info=c4d.TAG_VISIBLE|c4d.TAG_EXPRESSION, g=OSCSplineTag, description="OSCSplineTag", icon=bmp)
	if result:
		result = plugins.RegisterObjectPlugin(id=1032063, str="OSC Client", info=c4d.OBJECT_CALL_ADDEXECUTION, g=OSCClientObject, description="OSCClientObject", icon=bmp)
	
	print "OSC plugin initialised build 34: ", result




























