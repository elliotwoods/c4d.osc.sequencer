#pragma once

#include "ofxOSC.h"
#include "ofNode.h"
#include <memory>

namespace ofxC4DOSC {
	template<typename T> Node : ofNode {
		vector<shared_ptr<T> > children;
	};
	
	class Receiver {
	public:
		void setup(int port);
		void update();
	protected:
		ofxOSCReceiver rx;
	};
}