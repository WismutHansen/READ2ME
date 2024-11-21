'use client';

import React from 'react';
import { ArrowDown } from 'lucide-react';

const WelcomeMessage = () => {
  return (
    <div className="flex flex-col items-center justify-center space-y-8 py-12 relative">
      {/* Main welcome text */}
      <div className="text-center">
        <div className="text-xl font-medium mb-4">
          Welcome to READ2ME
        </div>
        <div className="text-lg text-gray-600">
          There is currently no content in your audio library,<br />
          try adding something via Add Content or from the article feed.
        </div>
      </div>

      {/* Down Arrow for Feed - centered above the feed list */}
      <div className="flex flex-col items-center">
        <span className="text-sm text-gray-500 mb-2">Article Feed</span>
        <ArrowDown 
          className="text-gray-400 animate-bounce" 
          size={32}
        />
      </div>
    </div>
  );
};

export default WelcomeMessage;
