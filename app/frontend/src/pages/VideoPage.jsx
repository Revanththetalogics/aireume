import { useState, useCallback, useRef, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Video, Upload, Loader2, AlertTriangle, CheckCircle,
  Mic, MessageSquare, Zap, AlertCircle, FileVideo,
  ChevronDown, ChevronUp, Copy, Check, X,
  Link2, ShieldAlert, ShieldCheck, ShieldQuestion,
  Clock, ThumbsUp, HelpCircle, Eye, EyeOff,
  Users, BookOpen, Brain, TrendingDown
} from 'lucide-react'
import NavBar from '../components/NavBar'
import { getCandidates, analyzeVideoFromUrl } from '../lib/api'

const ALLOWED = ['.mp4', '.webm', '.avi', '.mov', '.mkv']
const MAX_SIZE = 200 * 1024 * 1024

// ─── Platform detection ───────────────────────────────────────────────────────

function detectPlatform(url) {
  if (!url) return null
  const u = url.toLowerCase()
  if (u.includes('zoom.us') || u.includes('zoom.com')) return { name: 'Zoom', color: 'bg-blue-100 text-blue-700', icon: '🎥' }
  if (u.includes('sharepoint.com') || u.includes('teams.microsoft.com') || u.includes('1drv.ms')) return { name: 'Microsoft Teams', color: 'bg-purple-100 text-purple-700', icon: '💼' }
  if (u.includes('drive.google.com')) return { name: 'Google Drive', color: 'bg-yellow-100 text-yellow-700', icon: '📁' }
  if (u.includes('loom.com')) return { name: 'Loom', color: 'bg-pink-100 text-pink-700', icon: '🎬' }
  if (u.includes('dropbox.com')) return { name: 'Dropbox', color: 'bg-sky-100 text-sky-700', icon: '📦' }
  if (u.includes('youtube.com') || u.includes('youtu.be')) return { name: 'YouTube', color: 'bg-red-100 text-red-700', icon: '▶️' }
  const ext = url.split('?')[0].split('.').pop()?.toLowerCase()
  if (['mp4', 'webm', 'mov', 'avi', 'mkv'].includes(ext)) return { name: 'Direct URL', color: 'bg-green-100 text-green-700', icon: '🔗' }
  return { name: 'Unknown', color: 'bg-slate-100 text-slate-600', icon: '🔗' }
}

// ─── Circular gauge ───────────────────────────────────────────────────────────

function CircularGauge({ score, size = 120, strokeWidth = 8, label, colorFn }) {
  const radius = (size - strokeWidth) / 2
  const circ = radius * 2 * Math.PI
  const offset = circ - (score / 100) * circ
  const color = colorFn ? colorFn(score) : (score >= 70 ? '#22c55e' : score >= 45 ? '#eab308' : '#ef4444')
  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="transform -rotate-90" width={size} height={size}>
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#e2e8f0" strokeWidth={strokeWidth} />
          <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth}
            strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease-out' }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-slate-800">{score}</span>
          <span className="text-xs text-slate-400">/100</span>
        </div>
      </div>
      {label && <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-2">{label}</p>}
    </div>
  )
}

// ─── Score bar ────────────────────────────────────────────────────────────────

function ScoreBar({ label, value, color = 'blue' }) {
  const colors = { blue: 'bg-blue-500', green: 'bg-green-500', purple: 'bg-purple-500', amber: 'bg-amber-500', red: 'bg-red-500' }
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs font-medium text-slate-600">{label}</span>
        <span className="text-xs font-bold text-slate-700">{value}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div className={`h-2 rounded-full transition-all duration-700 ${colors[color]}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

// ─── Malpractice flag type meta ───────────────────────────────────────────────

const FLAG_META = {
  scripted_reading:    { label: 'Scripted Reading',       icon: BookOpen,      bg: 'bg-orange-50 border-orange-200', text: 'text-orange-800', badge: 'bg-orange-100 text-orange-700' },
  background_coaching: { label: 'Background Coaching',    icon: Users,         bg: 'bg-red-50 border-red-200',       text: 'text-red-800',    badge: 'bg-red-100 text-red-700' },
  inconsistent_fluency:{ label: 'Inconsistent Fluency',   icon: TrendingDown,  bg: 'bg-amber-50 border-amber-200',   text: 'text-amber-800',  badge: 'bg-amber-100 text-amber-700' },
  suspicious_pause:    { label: 'Suspicious Pause',       icon: Clock,         bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-800', badge: 'bg-yellow-100 text-yellow-700' },
  evasive_pattern:     { label: 'Evasive Pattern',        icon: Eye,           bg: 'bg-purple-50 border-purple-200', text: 'text-purple-800', badge: 'bg-purple-100 text-purple-700' },
  third_party_answering:{ label: 'Third-Party Answering', icon: Brain,         bg: 'bg-red-50 border-red-200',       text: 'text-red-800',    badge: 'bg-red-100 text-red-700' },
}

const SEVERITY_BADGE = {
  high:   'bg-red-100 text-red-700 border border-red-200',
  medium: 'bg-amber-100 text-amber-700 border border-amber-200',
  low:    'bg-slate-100 text-slate-600 border border-slate-200',
}

// ─── Malpractice Panel ────────────────────────────────────────────────────────

function MalpracticePanel({ m }) {
  const [expanded, setExpanded] = useState(true)
  const [showFlags, setShowFlags] = useState(true)

  const riskConfig = {
    low:    { bg: 'bg-green-50 border-green-200',   badge: 'bg-green-100 text-green-700 border border-green-300',   icon: ShieldCheck,    heading: 'text-green-800', label: 'LOW RISK' },
    medium: { bg: 'bg-amber-50 border-amber-200',   badge: 'bg-amber-100 text-amber-700 border border-amber-300',   icon: ShieldQuestion, heading: 'text-amber-800', label: 'MEDIUM RISK' },
    high:   { bg: 'bg-red-50 border-red-200',       badge: 'bg-red-100 text-red-700 border border-red-300',         icon: ShieldAlert,    heading: 'text-red-800',   label: 'HIGH RISK' },
  }
  const reliabilityConfig = {
    trustworthy:  { text: 'text-green-700', bg: 'bg-green-100', label: 'Trustworthy' },
    questionable: { text: 'text-amber-700', bg: 'bg-amber-100', label: 'Questionable' },
    unreliable:   { text: 'text-red-700',   bg: 'bg-red-100',   label: 'Unreliable' },
  }

  const risk    = m.malpractice_risk || 'low'
  const cfg     = riskConfig[risk] || riskConfig.low
  const relCfg  = reliabilityConfig[m.reliability_rating || 'trustworthy'] || reliabilityConfig.trustworthy
  const RiskIcon = cfg.icon
  const malpracticeColorFn = (s) => s >= 60 ? '#ef4444' : s >= 35 ? '#eab308' : '#22c55e'

  return (
    <div className={`rounded-xl border-2 ${cfg.bg} overflow-hidden`}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-5 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${cfg.badge}`}>
            <RiskIcon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className={`font-bold text-base ${cfg.heading}`}>Malpractice Assessment</h3>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wider ${cfg.badge}`}>
                {cfg.label}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {m.flags?.length || 0} flag{(m.flags?.length || 0) !== 1 ? 's' : ''} detected
              {m.pause_count > 0 && ` · ${m.pause_count} suspicious pause${m.pause_count !== 1 ? 's' : ''}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <CircularGauge score={m.malpractice_score || 0} size={72} strokeWidth={6} colorFn={malpracticeColorFn} />
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-opacity-30" style={{ borderColor: 'inherit' }}>

          {/* Reliability + Assessment row */}
          <div className="grid sm:grid-cols-2 gap-3 pt-3">
            <div className="bg-white rounded-lg p-3 border border-slate-200">
              <p className="text-xs text-slate-500 font-medium mb-1">Reliability Rating</p>
              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-1 rounded-full text-sm font-semibold ${relCfg.bg} ${relCfg.text}`}>
                  {relCfg.label}
                </span>
              </div>
            </div>
            {m.overall_assessment && (
              <div className="bg-white rounded-lg p-3 border border-slate-200">
                <p className="text-xs text-slate-500 font-medium mb-1">Overall Assessment</p>
                <p className="text-sm text-slate-700 leading-relaxed">{m.overall_assessment}</p>
              </div>
            )}
          </div>

          {/* Flags */}
          {m.flags?.length > 0 && (
            <div>
              <button
                onClick={() => setShowFlags(!showFlags)}
                className="flex items-center gap-2 text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2"
              >
                <AlertCircle className="w-3.5 h-3.5" />
                Detected Flags ({m.flags.length})
                {showFlags ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
              {showFlags && (
                <div className="space-y-2">
                  {m.flags.map((flag, i) => {
                    const meta = FLAG_META[flag.type] || { label: flag.type, icon: AlertCircle, bg: 'bg-slate-50 border-slate-200', text: 'text-slate-800', badge: 'bg-slate-100 text-slate-700' }
                    const FlagIcon = meta.icon
                    return (
                      <div key={i} className={`rounded-lg border p-3 ${meta.bg}`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <FlagIcon className={`w-4 h-4 ${meta.text} shrink-0`} />
                            <span className={`text-xs font-semibold ${meta.text}`}>{meta.label}</span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${SEVERITY_BADGE[flag.severity] || SEVERITY_BADGE.low}`}>
                              {flag.severity}
                            </span>
                          </div>
                        </div>
                        {flag.evidence && (
                          <p className={`text-xs mt-2 italic ${meta.text} opacity-80`}>
                            "{flag.evidence}"
                          </p>
                        )}
                        {flag.recommendation && (
                          <div className="mt-2 flex items-start gap-1.5">
                            <HelpCircle className="w-3 h-3 text-slate-400 shrink-0 mt-0.5" />
                            <p className="text-xs text-slate-600">{flag.recommendation}</p>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Pause timeline */}
          {m.pauses?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Suspicious Pause Timeline
              </p>
              <div className="space-y-2">
                {m.pauses.map((p, i) => (
                  <div key={i} className="bg-white rounded-lg border border-yellow-200 p-3 flex items-start gap-3">
                    <div className="bg-yellow-100 text-yellow-700 rounded-full px-2 py-0.5 text-xs font-mono font-bold shrink-0">
                      {p.formatted_at}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-semibold ${p.severity === 'high' ? 'text-red-600' : 'text-amber-600'}`}>
                          {p.duration_s}s silence
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-xs ${SEVERITY_BADGE[p.severity]}`}>{p.severity}</span>
                      </div>
                      <p className="text-xs text-slate-500 truncate">
                        After: <span className="italic">"{p.before_text}"</span>
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Positive signals */}
          {m.positive_signals?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <ThumbsUp className="w-3.5 h-3.5 text-green-500" /> Authenticity Signals
              </p>
              <div className="flex flex-wrap gap-2">
                {m.positive_signals.map((sig, i) => (
                  <span key={i} className="px-2.5 py-1 bg-green-50 text-green-700 border border-green-200 text-xs rounded-full">
                    {sig}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Follow-up questions */}
          {m.follow_up_questions?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-blue-500" /> Recommended Follow-Up Questions
              </p>
              <div className="space-y-1.5">
                {m.follow_up_questions.map((q, i) => (
                  <div key={i} className="flex items-start gap-2 bg-blue-50 rounded-lg px-3 py-2 border border-blue-100">
                    <span className="text-blue-400 text-xs font-bold shrink-0 mt-0.5">Q{i + 1}</span>
                    <p className="text-xs text-blue-800">{q}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Transcript panel ─────────────────────────────────────────────────────────

function TranscriptPanel({ transcript }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied]     = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(transcript)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="bg-slate-50 rounded-lg border border-slate-200">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-slate-500" />
          <span className="text-sm font-semibold text-slate-700">Full Transcript</span>
          <span className="text-xs text-slate-400">({transcript?.split(' ').length || 0} words)</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleCopy} className="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-700 transition-colors" title="Copy transcript">
            {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button onClick={() => setExpanded(!expanded)} className="p-1 hover:bg-slate-200 rounded text-slate-400 transition-colors">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>
      <div className={`px-4 py-3 text-sm text-slate-600 leading-relaxed ${expanded ? '' : 'max-h-28 overflow-hidden relative'}`}>
        {transcript || 'No transcript available.'}
        {!expanded && transcript && transcript.length > 300 && (
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-slate-50 to-transparent" />
        )}
      </div>
      {!expanded && transcript && transcript.length > 300 && (
        <button onClick={() => setExpanded(true)} className="w-full py-2 text-xs text-blue-600 hover:bg-slate-100 transition-colors rounded-b-lg">
          Show full transcript
        </button>
      )}
    </div>
  )
}

// ─── Analysis results ─────────────────────────────────────────────────────────

function VideoResults({ result, onReset }) {
  const confidenceColor = {
    high:   'bg-green-100 text-green-700',
    medium: 'bg-amber-100 text-amber-700',
    low:    'bg-red-100 text-red-700',
  }
  const commLabel = result.communication_score >= 70 ? 'Strong Communicator'
    : result.communication_score >= 45 ? 'Moderate Communication'
    : 'Needs Improvement'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-extrabold text-brand-900 tracking-tight">Video Analysis Results</h3>
          <p className="text-sm text-slate-500 mt-0.5 flex items-center gap-2 flex-wrap font-medium">
            <FileVideo className="w-4 h-4 text-brand-400" />
            <span>{result.source || result.filename || 'Recording'}</span>
            {result.platform && <span className="px-2 py-0.5 bg-brand-50 ring-1 ring-brand-200 rounded-lg text-xs text-brand-700 font-semibold">{result.platform}</span>}
            {result.duration_s > 0 && <span>· {Math.floor(result.duration_s / 60)}m {Math.round(result.duration_s % 60)}s</span>}
            {result.language && <span>· {result.language.toUpperCase()}</span>}
          </p>
        </div>
        <button
          onClick={onReset}
          className="flex items-center gap-2 px-3 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
        >
          <X className="w-4 h-4" /> New Video
        </button>
      </div>

      {/* 1. Malpractice Panel (top, most important for recruiter) */}
      {result.malpractice && <MalpracticePanel m={result.malpractice} />}

      {/* 2. Communication scores */}
      <div>
        <p className="text-xs font-bold text-brand-700 uppercase tracking-wide mb-3">Communication Analysis</p>
        <div className="grid sm:grid-cols-3 gap-4">
          {/* Communication score gauge */}
          <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5 flex flex-col items-center">
            <p className="text-xs font-bold text-brand-700 uppercase tracking-wide mb-3">Communication Score</p>
            <CircularGauge score={result.communication_score} label={commLabel} />
          </div>

          {/* Score breakdown */}
          <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5 space-y-3">
            <p className="text-xs font-bold text-brand-700 uppercase tracking-wide mb-3">Breakdown</p>
            <ScoreBar label="Clarity" value={result.clarity_score} color="blue" />
            {result.articulation_score != null && (
              <ScoreBar label="Articulation" value={result.articulation_score} color="purple" />
            )}
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs font-semibold text-slate-600">Confidence</span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold capitalize ${confidenceColor[result.confidence_level] || confidenceColor.medium}`}>
                {result.confidence_level}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">Words/min</span>
              <span className="text-xs font-extrabold text-brand-900">{result.words_per_minute}</span>
            </div>
          </div>

          {/* AI Summary */}
          <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5">
            <p className="text-xs font-bold text-brand-700 uppercase tracking-wide mb-3">AI Summary</p>
            <p className="text-sm text-slate-700 leading-relaxed">{result.summary || 'No summary available.'}</p>
          </div>
        </div>
      </div>

      {/* Strengths + Key phrases + Red flags */}
      <div className="grid sm:grid-cols-2 gap-4">
        {result.strengths?.length > 0 && (
          <div className="bg-green-50 rounded-2xl ring-1 ring-green-100 p-4 border-l-4 border-green-500">
            <div className="flex items-center gap-2 mb-2">
              <ThumbsUp className="w-4 h-4 text-green-600" />
              <h4 className="font-bold text-green-800 text-sm">Communication Strengths</h4>
            </div>
            <ul className="space-y-1">
              {result.strengths.map((s, i) => (
                <li key={i} className="text-xs text-green-700 flex items-start gap-1.5">
                  <CheckCircle className="w-3 h-3 text-green-500 mt-0.5 shrink-0" />{s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {result.key_phrases?.length > 0 && (
          <div className="bg-brand-50 rounded-2xl ring-1 ring-brand-100 p-4 border-l-4 border-brand-500">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-brand-600" />
              <h4 className="font-bold text-brand-800 text-sm">Notable Phrases</h4>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {result.key_phrases.map((p, i) => (
                <span key={i} className="px-2 py-0.5 bg-brand-100 text-brand-800 text-xs rounded-lg font-semibold">"{p}"</span>
              ))}
            </div>
          </div>
        )}

        {result.red_flags?.length > 0 ? (
          <div className="bg-red-50 rounded-2xl ring-1 ring-red-100 p-4 border-l-4 border-red-400">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <h4 className="font-bold text-red-800 text-sm">Communication Red Flags</h4>
            </div>
            <ul className="space-y-1">
              {result.red_flags.map((f, i) => (
                <li key={i} className="text-xs text-red-700 flex items-start gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-red-500 mt-0.5 shrink-0" />{f}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="bg-green-50 rounded-2xl ring-1 ring-green-100 p-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
            <p className="text-sm text-green-700 font-bold">No communication red flags.</p>
          </div>
        )}
      </div>

      {/* Transcript */}
      <TranscriptPanel transcript={result.transcript} />
    </div>
  )
}

// ─── Processing steps ─────────────────────────────────────────────────────────

const STEPS_UPLOAD = [
  { id: 'upload',     label: 'Uploading video file...' },
  { id: 'transcribe', label: 'Transcribing audio with Whisper AI...' },
  { id: 'analyze',    label: 'Analyzing communication & detecting malpractice...' },
]
const STEPS_URL = [
  { id: 'download',   label: 'Downloading recording from URL...' },
  { id: 'transcribe', label: 'Transcribing audio with Whisper AI...' },
  { id: 'analyze',    label: 'Analyzing communication & detecting malpractice...' },
]

function ProcessingSteps({ steps, activeStep, uploadProgress }) {
  return (
    <div className="space-y-2 p-4 bg-brand-50/60 rounded-2xl ring-1 ring-brand-100">
      {steps.map((step) => {
        const idx     = steps.findIndex(s => s.id === step.id)
        const actIdx  = steps.findIndex(s => s.id === activeStep)
        const isDone  = idx < actIdx
        const isActive = step.id === activeStep
        return (
          <div key={step.id} className={`flex items-center gap-3 p-2.5 rounded-xl transition-all ${
            isActive ? 'bg-brand-50 ring-1 ring-brand-200' :
            isDone   ? 'bg-green-50 ring-1 ring-green-100' :
                       'bg-white ring-1 ring-slate-100'
          }`}>
            {isDone ? <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
              : isActive ? <Loader2 className="w-4 h-4 text-brand-500 shrink-0 animate-spin" />
              : <div className="w-4 h-4 rounded-full ring-2 ring-slate-200 shrink-0" />}
            <span className={`text-sm flex-1 ${isActive ? 'text-brand-700 font-semibold' : isDone ? 'text-green-700' : 'text-slate-400'}`}>
              {step.label}
            </span>
            {step.id === 'upload' && isActive && uploadProgress > 0 && (
              <>
                <div className="w-24 bg-brand-100 rounded-full h-1.5">
                  <div className="h-1.5 bg-brand-500 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                </div>
                <span className="text-xs text-brand-600 font-mono shrink-0">{uploadProgress}%</span>
              </>
            )}
          </div>
        )
      })}
      <p className="text-xs text-slate-400 text-center pt-1">Malpractice detection runs in parallel. Total time: 1–4 min.</p>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function VideoPage() {
  const [inputMode, setInputMode]       = useState('upload')   // 'upload' | 'url'
  const [file, setFile]                 = useState(null)
  const [url, setUrl]                   = useState('')
  const [candidates, setCandidates]     = useState([])
  const [candidateId, setCandidateId]   = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [activeStep, setActiveStep]     = useState(null)
  const [result, setResult]             = useState(null)
  const [error, setError]               = useState('')
  const [isLoading, setIsLoading]       = useState(false)
  const xhrRef = useRef(null)

  const platform = detectPlatform(url)

  useEffect(() => {
    getCandidates({ page_size: 100 })
      .then(d => setCandidates(d.candidates || []))
      .catch(() => {})
  }, [])

  const onDrop = useCallback((accepted, rejected) => {
    if (accepted.length > 0) { setFile(accepted[0]); setError(''); setResult(null) }
    if (rejected.length > 0) setError(`File rejected: ${rejected[0].errors.map(e => e.message).join(', ')}`)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/mp4': ['.mp4'], 'video/webm': ['.webm'], 'video/avi': ['.avi'], 'video/quicktime': ['.mov'], 'video/x-matroska': ['.mkv'] },
    maxFiles: 1, maxSize: MAX_SIZE,
  })

  const formatSize = (b) => b >= 1024*1024 ? `${(b/(1024*1024)).toFixed(1)} MB` : `${(b/1024).toFixed(0)} KB`

  const handleUploadAnalyze = async () => {
    if (!file) return
    setError(''); setResult(null); setIsLoading(true); setUploadProgress(0); setActiveStep('upload')
    const formData = new FormData()
    formData.append('video', file)
    if (candidateId) formData.append('candidate_id', candidateId)
    const token   = localStorage.getItem('access_token')
    const API_URL = import.meta.env.VITE_API_URL || '/api'

    try {
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        xhrRef.current = xhr
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100)
            setUploadProgress(pct)
            if (pct === 100) setActiveStep('transcribe')
          }
        }
        xhr.onload = () => {
          setActiveStep('analyze')
          if (xhr.status >= 200 && xhr.status < 300) {
            try { resolve(JSON.parse(xhr.responseText)) }
            catch { reject(new Error('Invalid response')) }
          } else {
            try { reject(new Error(JSON.parse(xhr.responseText).detail || `Error ${xhr.status}`)) }
            catch { reject(new Error(`Server error ${xhr.status}`)) }
          }
        }
        xhr.onerror = () => reject(new Error('Network error'))
        xhr.open('POST', `${API_URL}/analyze/video`)
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
        xhr.send(formData)
      })
      setActiveStep('done')
      setResult(data)
    } catch (err) {
      setError(err.message || 'Video analysis failed.')
      setActiveStep(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleUrlAnalyze = async () => {
    if (!url.trim()) return
    setError(''); setResult(null); setIsLoading(true); setActiveStep('download')
    try {
      setActiveStep('transcribe')
      const data = await analyzeVideoFromUrl(url.trim(), candidateId || null)
      setActiveStep('analyze')
      await new Promise(r => setTimeout(r, 300))
      setActiveStep('done')
      setResult(data)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Video analysis failed.'
      setError(msg)
      setActiveStep(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setFile(null); setUrl(''); setResult(null); setError('')
    setActiveStep(null); setUploadProgress(0); setIsLoading(false)
    if (xhrRef.current) { xhrRef.current.abort(); xhrRef.current = null }
  }

  const activeSteps = inputMode === 'upload' ? STEPS_UPLOAD : STEPS_URL

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Page header */}
        <div className="card-animate">
          <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Video Interview Analysis</h2>
          <p className="text-slate-500 text-sm mt-1 font-medium">
            Upload or paste a recording URL — ARIA transcribes speech, scores communication, and detects malpractice signals.
          </p>
        </div>

        {/* How it works */}
        <div className="grid sm:grid-cols-4 gap-3 card-animate">
          {[
            { icon: Video,         title: 'Upload or URL',       desc: 'File upload or Zoom / Teams / Drive / Loom link' },
            { icon: Mic,           title: 'Auto Transcription',  desc: 'Whisper AI converts speech to text' },
            { icon: MessageSquare, title: 'Communication Score', desc: 'LLM rates clarity, confidence & fluency' },
            { icon: ShieldAlert,   title: 'Malpractice Check',   desc: 'Detects coaching, scripted answers & pauses' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 flex gap-3">
              <div className="w-9 h-9 rounded-xl bg-brand-50 flex items-center justify-center shrink-0">
                <Icon className="w-5 h-5 text-brand-600" />
              </div>
              <div>
                <p className="text-sm font-bold text-brand-900">{title}</p>
                <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Upload + results */}
        {!result ? (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 space-y-5 card-animate">

            {/* Input mode toggle */}
            <div className="flex gap-1 p-1 bg-brand-50 ring-1 ring-brand-100 rounded-xl w-fit">
              {[
                { id: 'upload', label: 'Upload File', icon: Upload },
                { id: 'url',    label: 'From URL',    icon: Link2 },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => { setInputMode(id); setError('') }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                    inputMode === id
                      ? 'bg-brand-600 text-white shadow-brand-sm'
                      : 'text-slate-500 hover:text-brand-700'
                  }`}
                >
                  <Icon className="w-4 h-4" />{label}
                </button>
              ))}
            </div>

            {/* File upload tab */}
            {inputMode === 'upload' && (
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Interview Recording</label>
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
                    isDragActive ? 'border-brand-500 bg-brand-50' :
                    file ? 'border-green-300 bg-green-50' :
                    'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
                  }`}
                >
                  <input {...getInputProps()} />
                  {file ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-14 h-14 bg-green-100 rounded-2xl flex items-center justify-center">
                        <FileVideo className="w-7 h-7 text-green-600" />
                      </div>
                      <div>
                        <p className="font-bold text-brand-900">{file.name}</p>
                        <p className="text-sm text-slate-500 mt-0.5">{formatSize(file.size)}</p>
                      </div>
                      <button type="button" onClick={e => { e.stopPropagation(); handleReset() }} className="text-xs text-red-500 hover:underline font-medium">
                        Remove
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-14 h-14 bg-brand-50 ring-1 ring-brand-100 rounded-2xl flex items-center justify-center">
                        <Upload className="w-7 h-7 text-brand-400" />
                      </div>
                      <div>
                        <p className="text-slate-700 font-semibold">
                          {isDragActive ? 'Drop the video here...' : 'Drag & drop your interview recording'}
                        </p>
                        <p className="text-sm text-slate-400 mt-1">MP4, WebM, MOV, AVI, MKV · Up to 200 MB</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* URL tab */}
            {inputMode === 'url' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-2">Recording URL</label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-400" />
                      <input
                        type="url"
                        value={url}
                        onChange={e => setUrl(e.target.value)}
                        placeholder="https://zoom.us/rec/share/... or Teams / Drive / Loom link"
                        className="w-full pl-9 pr-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm text-slate-700 placeholder-slate-400 bg-white"
                        onKeyDown={e => e.key === 'Enter' && !isLoading && url.trim() && handleUrlAnalyze()}
                      />
                    </div>
                    {platform && url.trim() && (
                      <span className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold shrink-0 ${platform.color}`}>
                        <span>{platform.icon}</span>{platform.name}
                      </span>
                    )}
                  </div>
                </div>
                <div className="bg-brand-50 rounded-2xl ring-1 ring-brand-100 p-3">
                  <p className="text-xs font-bold text-brand-700 mb-1.5">Supported platforms</p>
                  <div className="flex flex-wrap gap-1.5">
                    {['Zoom', 'Microsoft Teams', 'Google Drive', 'Loom', 'Dropbox', 'Direct MP4 URL'].map(p => (
                      <span key={p} className="px-2 py-0.5 bg-white ring-1 ring-brand-200 text-brand-700 text-xs rounded-full font-semibold">{p}</span>
                    ))}
                  </div>
                  <p className="text-xs text-brand-600 mt-2">
                    Ensure the recording link is set to <strong>"Anyone with the link can view"</strong> (no login required).
                  </p>
                </div>
              </div>
            )}

            {/* Link to candidate (optional) */}
            {candidates.length > 0 && (
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">
                  Link to Candidate <span className="text-slate-400 font-normal">(optional)</span>
                </label>
                <select
                  value={candidateId}
                  onChange={e => setCandidateId(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm text-slate-700 bg-white"
                >
                  <option value="">— Select a candidate —</option>
                  {candidates.map(c => (
                    <option key={c.id} value={c.id}>{c.name || c.email || `Candidate #${c.id}`}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="p-3.5 bg-red-50 ring-1 ring-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Processing steps */}
            {isLoading && (
              <ProcessingSteps
                steps={activeSteps}
                activeStep={activeStep}
                uploadProgress={uploadProgress}
              />
            )}

            {/* Analyze button */}
            <button
              onClick={inputMode === 'upload' ? handleUploadAnalyze : handleUrlAnalyze}
              disabled={isLoading || (inputMode === 'upload' ? !file : !url.trim())}
              className="w-full py-3.5 btn-brand text-white font-bold rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed shadow-brand flex items-center justify-center gap-2 text-sm"
            >
              {isLoading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing Interview...</>
              ) : (
                <><Video className="w-5 h-5" /> Analyze Interview</>
              )}
            </button>
          </div>
        ) : (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
            <VideoResults result={result} onReset={handleReset} />
          </div>
        )}
      </main>
    </div>
  )
}
