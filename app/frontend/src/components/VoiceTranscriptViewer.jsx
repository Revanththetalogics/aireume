import { MessageSquare, User, Bot, Clock } from 'lucide-react'

export default function VoiceTranscriptViewer({ entries }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No transcript available</p>
      </div>
    )
  }

  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-4">
        <MessageSquare className="w-4 h-4" />
        Transcript
        <span className="text-xs font-normal text-slate-400">({entries.length} turns)</span>
      </h3>
      <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
        {entries.map((entry, idx) => {
          const isBot = entry.speaker === 'bot'
          return (
            <div
              key={entry.id || idx}
              className={`flex gap-3 ${isBot ? 'flex-row' : 'flex-row-reverse'}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                isBot
                  ? 'bg-brand-100 text-brand-600'
                  : 'bg-slate-100 text-slate-600'
              }`}>
                {isBot ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
              </div>
              <div className={`flex-1 max-w-[80%] ${isBot ? '' : 'text-right'}`}>
                <div className={`inline-block px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                  isBot
                    ? 'bg-brand-50 text-slate-700 rounded-tl-md'
                    : 'bg-slate-100 text-slate-700 rounded-tr-md'
                }`}>
                  {entry.text}
                </div>
                {entry.timestamp && (
                  <p className={`flex items-center gap-1 text-[10px] text-slate-400 mt-1 ${isBot ? '' : 'justify-end'}`}>
                    <Clock className="w-3 h-3" />
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
