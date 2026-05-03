import { useState, useRef, useEffect } from 'react';
import { Send, User, Bot } from 'lucide-react';
import { Button } from '../ui/Button';
import type { DesignChat } from '../../types/api';

interface RevisionChatProps {
  chats: DesignChat[];
  // Kept for API compatibility — no longer used (every submit triggers a revision now).
  onSendMessage: (message: string) => void;
  onRequestRevision: (notes: string) => void;
  isLoading?: boolean;
}

const QUICK_PROMPTS = [
  'Make the front logo larger',
  'Try a different color scheme',
  'Use a darker hat color',
  'Remove the back decoration',
];

export function RevisionChat({
  chats,
  onRequestRevision,
  isLoading,
}: RevisionChatProps) {
  const [message, setMessage] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chats]);

  // Every submit triggers a revision — the previous keyword-based routing dropped
  // any message that didn't contain words like "change" or "remove" into a
  // chat-only path that produced no new design, which looked broken to users.
  const submitRevision = (text: string) => {
    if (!text.trim() || isLoading) return;
    onRequestRevision(text);
    setMessage('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitRevision(message);
  };

  return (
    <div className="flex flex-col h-full">
      <h3 className="font-semibold text-white mb-3">Request a Revision</h3>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-[200px] max-h-[400px] pr-2">
        {chats.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            <p>No revisions yet.</p>
            <p className="mt-1">Each request generates a new version.</p>
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

      {/* Quick prompts */}
      {chats.length === 0 && !isLoading && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {QUICK_PROMPTS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => setMessage(q)}
              className="text-xs px-2.5 py-1 rounded-full bg-fill-tertiary text-gray-200 hover:bg-fill-secondary transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Describe what to change…"
          className="input flex-1"
          disabled={isLoading}
        />
        <Button type="submit" disabled={!message.trim() || isLoading} isLoading={isLoading}>
          <Send className="w-4 h-4" />
        </Button>
      </form>

      <p className="text-xs text-gray-400 mt-2">
        Phrase as an edit instruction, e.g. "make the logo larger" or "change the hat to navy". Each submit generates a new version.
      </p>
    </div>
  );
}
