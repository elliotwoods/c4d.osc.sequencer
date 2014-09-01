CONTAINER OSCClientObject {
	
	NAME OSCClientObject;

	GROUP OSCClientObjectSettings
	{
		SEPARATOR NetworkSeparator {}
		BOOL Enabled {}
		STRING Address {}
		LONG Port { MINEX; MIN 1; }
		BOOL UseSendThread {}

		SEPARATOR ObjectSeparator {}
		LONG SplineResolution {
			MINEX;
			MIN 1;
		}
		BOOL ReformatCoordinates {}
		
		
		SEPARATOR ExportSeparator {}
		BOOL ExportEnabled {}
		FILENAME ExportFilename {
			SAVE;
		}
		STATICTEXT ExportNote {}
	}
}