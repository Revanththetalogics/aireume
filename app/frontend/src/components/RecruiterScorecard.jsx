import { useState } from 'react'
import {
  Brain, Sparkles, ChevronDown, CheckCircle2, TrendingUp, ArrowRight,
  Users, MessageSquare, Heart, XCircle, AlertCircle, ShieldCheck, Zap,
} from 'lucide-react'

const RECOMMENDATION_CONFIG = {
  strong_hire:    { label: 'Strong Hire',     color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
  hire:           { label: 'Hire',            color: 'bg-green-100 text-green-700',     icon: CheckCircle2 },
  maybe:          { label: 'Maybe',           color: 'bg-amber-100 text-amber-700',     icon: AlertCircle },
  no_hire:        { label: 'No Hire',         color: 'bg-red-100 text-red-700',         icon: XCircle },
  strong_no_hire: { label: 'Strong No Hire',  color: 'bg-red-200 text-red-800',         icon: XCircle },
}

const CONFIDENCE_CONFIG = {
  high:   { label: 'High Confidence',   color: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  medium: { label: 'Medium Confidence', color: 'bg-amber-50 text-amber-700 ring-amber-200' },
  low:    { label: 'Low Confidence',    color: 'bg-red-50 text-red-700 ring-red-200' },
}

// 7-dimension model. Each entry maps a dimension key to its label, score
// field, evidence field, and a representative icon. New dimensions (motivation,
// integrity, confidence) are rendered only when the backend supplies a score.
const DIMENSIONS = [
  { key: 'technical',     label: 'Technical Proficiency',  scoreField: 'technical_score',      evidenceField: 'technical_evidence',      icon: Brain },
  { key: 'behavioral',    label: 'Behavioral Alignment',   scoreField: 'behavioral_score',     evidenceField: 'behavioral_evidence',     icon: Users },
  { key: 'communication', label: 'Communication Skills',   scoreField: 'communication_score',  evidenceField: 'communication_evidence',  icon: MessageSquare },
  { key: 'cultural_fit',  label: 'Cultural Fit',           scoreField: 'cultural_fit_score',   evidenceField: 'cultural_fit_evidence',   icon: Heart },
  { key: 'motivation',    label: 'Motivation & Growth',    scoreField: 'motivation_score',     evidenceField: 'motivation_evidence',     icon: Sparkles },
  { key: 'integrity',     label: 'Integrity',              scoreField: 'integrity_score',      evidenceField: 'integrity_evidence',      icon: ShieldCheck },
  { key: 'confidence',    label: 'Confidence',             scoreField: 'confidence_score',     evidenceField: 'confidence_evidence',     icon: Zap },
]

const DIMENSION_LABELS = DIMENSIONS.reduce((acc, d) => {
  acc[d.key] = d.label
  return acc
}, {})

/**
 * Safely coerce an evidence value into a plain object.
 * The backend stores evidence as JSON text; the API layer usually parses it
 * already, but defend against raw JSON strings or unexpected primitives.
 */
function parseEvidence(raw) {
  if (raw == null) return null
  if (typeof raw === 'string') {
    const trimmed = raw.trim()
    if (!trimmed) return null
    try {
      return JSON.parse(trimmed)
    } catch {
      return null
    }
  }
  return raw
}

/**
 * Extract a flat list of evidence bullet points from a parsed evidence value.
 * Supports multiple shapes produced by the evaluation agents:
 *   - array of strings                     → ["obs 1", "obs 2"]
 *   - { items: [...] }                     → {items: [...]}
 *   - { evidence: [...], details: {...} }  → backend evaluator shape
 *   - { strengths: [...], gaps: [...] }    → backend evaluator shape
 */
function extractEvidenceItems(parsed) {
  if (!parsed) return []
  if (Array.isArray(parsed)) return parsed.filter((x) => x != null && x !== '')
  if (typeof parsed === 'object') {
    if (Array.isArray(parsed.evidence)) return parsed.evidence.filter((x) => x != null && x !== '')
    if (Array.isArray(parsed.items)) return parsed.items.filter((x) => x != null && x !== '')
    if (Array.isArray(parsed.highlights)) return parsed.highlights.filter((x) => x != null && x !== '')
    // Fallback: gather every array-typed value
    const collected = []
    for (const v of Object.values(parsed)) {
      if (Array.isArray(v)) collected.push(...v)
    }
    return collected.filter((x) => x != null && x !== '')
  }
  return []
}

function extractLabeledItems(parsed, keys) {
  const out = {}
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return out
  for (const k of keys) {
    if (Array.isArray(parsed[k]) && parsed[k].length > 0) {
      out[k] = parsed[k].filter((x) => x != null && x !== '')
    }
  }
  return out
}

function scoreColor(pct) {
  if (pct >= 80) return 'bg-emerald-500'
  if (pct >= 60) return 'bg-green-500'
  if (pct >= 40) return 'bg-amber-500'
  return 'bg-red-500'
}

function scoreTextColor(pct) {
  if (pct >= 80) return 'text-emerald-600'
  if (pct >= 60) return 'text-green-600'
  if (pct >= 40) return 'text-amber-600'
  return 'text-red-600'
}

function ScoreGauge({ score, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100))
  const ringColor =
    pct >= 80 ? 'stroke-emerald-500' :
    pct >= 60 ? 'stroke-green-500' :
    pct >= 40 ? 'stroke-amber-500' :
    'stroke-red-500'
  const circumference = 2 * Math.PI * 44
  const offset = circumference - (pct / 100) * circumference
  return (
    <div className="relative w-28 h-28 mx-auto shrink-0">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="44" fill="none" strokeWidth="8" className="stroke-slate-100" />
        <circle
          cx="50" cy="50" r="44" fill="none" strokeWidth="8"
          className={ringColor}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${scoreTextColor(pct)}`}>{score ?? '—'}</span>
        <span className="text-xs text-slate-400">/ {max}</span>
      </div>
    </div>
  )
}

function DimensionCard({ label, score, evidence, icon: Icon }) {
  const [open, setOpen] = useState(false)
  const pct = Math.min(100, Math.max(0, (score ?? 0)))
  const parsed = parseEvidence(evidence)
  const items = extractEvidenceItems(parsed)
  const labeled = extractLabeledItems(parsed, ['strengths', 'gaps', 'patterns', 'observations', 'fit_indicators'])
  const hasDetail = items.length > 0 || Object.keys(labeled).length > 0
  const hasScore = score != null

  return (
    <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-5 transition-shadow hover:shadow-sm">
      <button
        type="button"
        onClick={() => hasDetail && setOpen((v) => !v)}
        className={`flex items-center w-full gap-3 ${hasDetail ? 'cursor-pointer' : 'cursor-default'}`}
        disabled={!hasDetail}
      >
        <div className="w-9 h-9 rounded-xl bg-brand-50 flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4 text-brand-600" />
        </div>
        <div className="flex-1 min-w-0 text-left">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-bold text-slate-800 truncate">{label}</span>
            <span className={`text-sm font-bold ${hasScore ? scoreTextColor(pct) : 'text-slate-400'}`}>
              {hasScore ? score : '—'}
            </span>
          </div>
          <div className="mt-2 h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${hasScore ? scoreColor(pct) : 'bg-slate-200'}`}
              style={{ width: `${hasScore ? pct : 0}%` }}
            />
          </div>
        </div>
        {hasDetail && (
          <ChevronDown
            className={`w-4 h-4 text-slate-400 transition-transform shrink-0 ${open ? 'rotate-180' : ''}`}
          />
        )}
      </button>

      {open && hasDetail && (
        <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
          {items.length > 0 && (
            <ul className="space-y-1.5">
              {items.map((item, i) => (
                <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                  <span className="mt-1.5 w-1 h-1 rounded-full bg-brand-400 shrink-0" />
                  <span>{typeof item === 'string' ? item : JSON.stringify(item)}</span>
                </li>
              ))}
            </ul>
          )}
          {labeled.strengths && (
            <EvidenceSubList title="Strengths" items={labeled.strengths} tone="emerald" />
          )}
          {labeled.gaps && (
            <EvidenceSubList title="Gaps" items={labeled.gaps} tone="amber" />
          )}
          {labeled.patterns && (
            <EvidenceSubList title="Patterns" items={labeled.patterns} tone="brand" />
          )}
          {labeled.observations && (
            <EvidenceSubList title="Observations" items={labeled.observations} tone="brand" />
          )}
          {labeled.fit_indicators && (
            <EvidenceSubList title="Fit Indicators" items={labeled.fit_indicators} tone="brand" />
          )}
        </div>
      )}
    </div>
  )
}

const SUB_TONE = {
  emerald: { dot: 'bg-emerald-400', label: 'text-emerald-700' },
  amber:   { dot: 'bg-amber-400',   label: 'text-amber-700' },
  brand:   { dot: 'bg-brand-400',   label: 'text-brand-700' },
}

function EvidenceSubList({ title, items, tone = 'brand' }) {
  const t = SUB_TONE[tone] || SUB_TONE.brand
  return (
    <div>
      <p className={`text-[11px] font-semibold uppercase tracking-wide mb-1.5 ${t.label}`}>{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
            <span className={`mt-1.5 w-1 h-1 rounded-full shrink-0 ${t.dot}`} />
            <span>{typeof item === 'string' ? item : JSON.stringify(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function FitScoreAdjustment({ original, adjusted, reasoning }) {
  const hasData = original != null || adjusted != null
  if (!hasData) return null

  const diff = (adjusted ?? 0) - (original ?? 0)
  const isUp = diff > 0
  const isFlat = diff === 0
  const valueColor = isUp ? 'text-emerald-600' : isFlat ? 'text-slate-600' : 'text-amber-600'

  return (
    <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
      <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-brand-600" />
        Fit Score Adjustment
      </h3>
      <div className="flex items-center justify-center gap-4 sm:gap-6">
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-1">Original</p>
          <p className="text-2xl font-bold text-slate-600">{original ?? '—'}</p>
        </div>
        <ArrowRight className="w-5 h-5 text-slate-300" />
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-1">Adjusted</p>
          <p className={`text-2xl font-bold ${valueColor}`}>{adjusted ?? '—'}</p>
        </div>
        {!isFlat && (
          <div className="text-center">
            <p className="text-xs text-slate-400 mb-1">Change</p>
            <p className={`text-lg font-bold ${valueColor}`}>
              {isUp ? '+' : ''}{diff}
            </p>
          </div>
        )}
      </div>
      {reasoning && (
        <p className="text-xs text-slate-500 mt-4 text-center italic leading-relaxed">{reasoning}</p>
      )}
    </div>
  )
}

export default function RecruiterScorecard({ scorecard }) {
  if (!scorecard) return null

  const recommendation = scorecard.recommendation || null
  const recConfig = RECOMMENDATION_CONFIG[recommendation] || null
  const RecIcon = recConfig?.icon || null
  const confidence = scorecard.confidence_level || null
  const confConfig = confidence ? CONFIDENCE_CONFIG[confidence] : null

  const activeDimensions = DIMENSIONS.filter(
    (d) => scorecard[d.scoreField] != null || scorecard[d.evidenceField] != null,
  )

  return (
    <div className="space-y-6">
      {/* Overall Score + Recommendation + Confidence */}
      <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
        <div className="flex flex-col md:flex-row items-center gap-6">
          <ScoreGauge score={scorecard.overall_score ?? 0} />
          <div className="flex-1 text-center md:text-left">
            <h3 className="text-lg font-bold text-slate-900">Overall Score</h3>
            <div className="flex flex-wrap items-center gap-2 mt-2 justify-center md:justify-start">
              {recConfig && (
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${recConfig.color}`}>
                  {RecIcon && <RecIcon className="w-4 h-4" />}
                  {recConfig.label}
                </span>
              )}
              {confConfig && (
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ring-1 ${confConfig.color}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
                  {confConfig.label}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Dimension Cards */}
      {activeDimensions.length > 0 && (
        <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
          <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Brain className="w-4 h-4 text-brand-600" />
            Dimension Scores
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeDimensions.map((d) => (
              <DimensionCard
                key={d.key}
                label={d.label}
                score={scorecard[d.scoreField]}
                evidence={scorecard[d.evidenceField]}
                icon={d.icon}
              />
            ))}
          </div>
        </div>
      )}

      {/* Fit Score Adjustment */}
      <FitScoreAdjustment
        original={scorecard.original_fit_score}
        adjusted={scorecard.adjusted_fit_score}
        reasoning={scorecard.adjustment_reasoning}
      />
    </div>
  )
}

export { DIMENSION_LABELS, RECOMMENDATION_CONFIG, CONFIDENCE_CONFIG }
