import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot } from 'lucide-react';
import { Button } from '../ui/Button';
import type { DesignChat } from '../../types/api';

interface RevisionChatProps {
  chats: DesignChat[];
  onSendMessage: (message: string) => void;
  onRequestRevision: (notes: string) => void;
  isLoading?: boolean;
}

export function RevisionChat({
  chats,
  onSendMessage,
  onRequestRevision,
  isLoading,
}: RevisionChatProps) {
  const [message, setMessage] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chats]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    // Check if message looks like a revision request
    const revisionKeywords = ['change', 'make', 'update', 'modify', 'add', 'remove', 'revise', 'different', 'instead', 'try'];
    const isRevisionRequest = revisionKeywords.some((keyword) =>
      message.toLowerCase().includes(keyword)
    );

    if (isRevisionRequest) {
      onRequestRevision(message);
    } else {
      onSendMessage(message);
    }

    setMessage('');
  };

  return (
    <div className="flex flex-col h-full">
      <h3 className="font-semibold text-white mb-3">Revisions & Chat</h3>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-[200px] max-h-[400px] pr-2">
        {chats.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            <p>No messages yet.</p>
            <p className="mt-1">Request changes to generate new versions.</p>
          </div>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              className={`flex gap-2 ${chat.is_user ? 'justify-end' : 'justify-start'}`}
            >
              {!chat.is_user && (
                <div className="w-8 h-8 rounded-full bg-primary-900/50 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-400" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  chat.is_user
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-700 text-gray-100'
                }`}
              >
                <p className="text-sm">{chat.message}</p>
                <p
                  className={`text-xs mt-1 ${
                    chat.is_user ? 'text-primary-200' : 'text-gray-400'
                  }`}
                >
                  {new Date(chat.created_at).toLocaleTimeString()}
                </p>
              </div>
              {chat.is_user && (
                <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-gray-300" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Request changes or ask questions..."
          className="input flex-1"
          disabled={isLoading}
        />
        <Button type="submit" disabled={!message.trim() || isLoading} isLoading={isLoading}>
          <Send className="w-4 h-4" />
        </Button>
      </form>

      <p className="text-xs text-gray-400 mt-2">
        Tip: Describe changes like "Make the logo larger" or "Use a different color scheme" to generate a new version.
      </p>
    </div>
  );
}
