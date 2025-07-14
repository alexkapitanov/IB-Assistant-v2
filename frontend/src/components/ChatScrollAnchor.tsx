import React, { useEffect, useRef } from 'react';

interface ChatScrollAnchorProps {
  trackVisibility?: boolean;
}

const ChatScrollAnchor: React.FC<ChatScrollAnchorProps> = ({ trackVisibility }) => {
  const anchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (anchorRef.current && trackVisibility) {
      anchorRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [trackVisibility]);

  return <div ref={anchorRef} className="h-px w-full" />;
};

export default ChatScrollAnchor;
