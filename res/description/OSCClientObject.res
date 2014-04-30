CONTAINER OSCClientObject {
	
	NAME OSCClientObject;

	GROUP OSCClientObjectSettings
	{
		STRING Address {}
		LONG Port {MINEX; MIN 1; }
		BOOL Enabled {}
	}
}