import c4d
import os

import sys
import random
import time

from SimpleOSC import *
from OSC import *

from c4d import gui, plugins, bitmaps

VAR_Settings = 1000
VAR_Enabled = 1001
VAR_Scale = 1102
VAR_Resolution = 1103
VAR_Address = 1002
VAR_Port = 1003

def AppendPoint(msg, spline, transform, x):
	point = spline.GetSplinePoint(x) * transform / 100.0
	msg.append(point.x)
	msg.append(point.y)
	msg.append(-point.z)

def GetFirstArg(descID):
	text = descID.__str__()
	return int(text.lstrip("(").rstrip(")").split(",")[0])

class OSCClientObject(plugins.ObjectData):
	"""OSCClientObject"""

	client = 0
	cachedAddress = ""
	cachedPort = ""

	def __init__(self):
		self.SetOptimizeCache(True)

	def Init(self, node):
		data = node.GetDataInstance()
		data.SetBool(VAR_Enabled, True)
		data.SetString(VAR_Address, "127.0.0.1")
		data.SetLong(VAR_Port, 4000)
		return True

	def GetVirtualObjects(self, op, hierarchyhelp):
		data = op.GetDataInstance()
		newAddress = data.GetString(VAR_Address)
		newPort = data.GetLong(VAR_Port)

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
				 self.client = 0

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
				resolution = 20

				msg = OSCMessage(objectBaseAddress + "/spline")

				for iLookup in range(0, resolution):
					x = float(iLookup) / float(resolution)
					AppendPoint(msg, spline, transform, x)
				
				if spline.IsClosed():
					AppendPoint(msg, spline, transform, 0)

				self.Send(msg)

			userData = child.GetUserDataContainer()
			if userData is not None:
				for descID, container in userData:
					name = container.__getitem__(1)
					name = name.replace(" ", "_")
					value = child[c4d.ID_USERDATA, GetFirstArg(descID)]
					address = objectBaseAddress + "/" + name

					if type(value) is c4d.Vector:
						self.SendVariable(address + "/x", value.x)
						self.SendVariable(address + "/y", value.y)
						self.SendVariable(address + "/z", value.z)
					elif value is not None:
						self.SendVariable(address, value)

			childIndex += 1

		self.SendVariable("/objects/end", 0)
		return None

	def Send(self, msg):
		try:
			self.client.send(msg)
		except:
			pass

	def SendVariable(self, address, variable):
		msg = OSCMessage(address);
		msg.append(variable)
		self.Send(msg)

if __name__ == "__main__":
	bmp = bitmaps.BaseBitmap()
	dir, file = os.path.split(__file__)
	bitmapFilename = os.path.join(dir, "res", "kc_letter.bmp")

	result = bmp.InitWith(bitmapFilename)
	if not result:
		print "Error loading bitmap icon"
	
	result = plugins.RegisterObjectPlugin(id=1032063, str="OSC Client", info=c4d.OBJECT_GENERATOR | c4d.OBJECT_INPUT, g=OSCClientObject, description="OSCClientObject", icon=bmp)
	
	print "OSC plugin initialised build 50: ", result




























