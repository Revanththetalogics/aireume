import {
  AlertTriangle, CheckCircle, CheckCircle2, Compass, Flame, Shield, Star, TrendingUp, XCircle,
} from 'lucide-react'
import SkillsRadar from './SkillsRadar'
import { safeStr } from '../lib/utils'

export default function ResultCardSkillsIntel({
  skill_analysis,
  score_breakdown,
  result,
  matched_skills,
  missing_skills,
  skill_depth,
  adjacent_skills,
  risk_summary,
}) {
  const onet_hot_skills = result?.onet_hot_skills || []
  return (
    <>
        {/* Skills Intel — Tiered display when enhanced skill_analysis is available */}
        {skill_analysis?.matched_required != null ? (
          /* ── Tiered Skill Display (new backend data) ── */
          <div className="space-y-4">
            {/* Tiered score breakdown */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2 bg-brand-50/80 ring-1 ring-brand-200 rounded-xl px-3 py-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-brand-600" />
                <span className="text-xs font-bold text-brand-800">
                  Core Skills: {typeof score_breakdown?.skill_match === 'object' ? (score_breakdown?.skill_match?.score ?? skill_analysis.required_match_pct ?? 0) : (score_breakdown?.skill_match ?? skill_analysis.required_match_pct ?? 0)}%
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="font-semibold text-green-700">Must-have: {skill_analysis.required_match_pct ?? 0}%</span>
                <span className="text-slate-300">|</span>
                <span className="font-semibold text-amber-700">Good-to-have: {skill_analysis.nice_to_have_match_pct ?? 0}%</span>
                {skill_analysis.proficiency_analysis && Object.keys(skill_analysis.proficiency_analysis).length > 0 && (() => {
                  const profEntries = Object.values(skill_analysis.proficiency_analysis)
                  const avgMatch = profEntries.length > 0
                    ? Math.round((profEntries.reduce((sum, e) => sum + (e.match_factor ?? 0), 0) / profEntries.length) * 100)
                    : 0
                  return (
                    <>
                      <span className="text-slate-300">|</span>
                      <span className="font-semibold text-indigo-700">Proficiency match: {avgMatch}%</span>
                    </>
                  )
                })()}
              </div>
            </div>

            {/* Must-Have Skills */}
            {(() => {
              let matched = skill_analysis.matched_required || []
              let missing = skill_analysis.missing_required || []
              let total = matched.length + missing.length
              if (total === 0) {
                const reqSkills = result?.jd_analysis?.required_skills || skill_analysis.required_skills || []
                const flatMatched = skill_analysis.matched_skills || matched_skills || []
                if (Array.isArray(reqSkills) && reqSkills.length > 0) {
                  const matchedLower = new Set(flatMatched.map((s) => String(s).toLowerCase()))
                  matched = reqSkills.filter((s) => matchedLower.has(String(s).toLowerCase()))
                  missing = reqSkills.filter((s) => !matchedLower.has(String(s).toLowerCase()))
                  total = reqSkills.length
                }
              }
              const profAnalysis = skill_analysis.proficiency_analysis || {}
              const hotSet = new Set((onet_hot_skills || []).map(s => typeof s === 'string' ? s.toLowerCase() : String(s).toLowerCase()))
              if (total === 0) return null
              return (
                <div className="bg-slate-50 rounded-2xl p-4 ring-1 ring-slate-200">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-5 h-5 rounded-md bg-red-100 flex items-center justify-center">
                      <Shield className="w-3 h-3 text-red-600" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                      Must-Have Skills
                    </span>
                    <span className="text-xs font-semibold text-slate-500">
                      ({matched.length}/{total} matched)
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {matched.map((s, i) => {
                      const skillName = safeStr(s)
                      const prof = profAnalysis[skillName] || profAnalysis[skillName.toLowerCase()]
                      const isHot = hotSet.has(skillName.toLowerCase())
                      let profPill = null
                      if (prof) {
                        const mf = prof.match_factor ?? 0
                        if (mf >= 1.0) {
                          profPill = (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-green-700 bg-green-200/60 rounded px-1 py-px">
                              <CheckCircle2 className="w-2.5 h-2.5" />
                              {safeStr(prof.estimated_candidate)}
                            </span>
                          )
                        } else if (mf >= 0.5) {
                          profPill = (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-amber-700 bg-amber-200/60 rounded px-1 py-px">
                              {safeStr(prof.estimated_candidate)} ({safeStr(prof.required)} expected)
                            </span>
                          )
                        } else {
                          profPill = (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-orange-700 bg-orange-200/60 rounded px-1 py-px">
                              {safeStr(prof.estimated_candidate)} ({safeStr(prof.required)} expected)
                            </span>
                          )
                        }
                      }
                      return (
                        <span
                          key={`mr-${i}`}
                          className="px-2.5 py-1 bg-green-100 border-2 border-green-400 text-green-800 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <CheckCircle className="w-3 h-3 text-green-600" />
                          {skillName}
                          {profPill}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                          {skill_depth && skill_depth[skillName] && (
                            <span className="text-[10px] text-green-600 font-medium">({safeStr(skill_depth[skillName])}x)</span>
                          )}
                        </span>
                      )
                    })}
                    {missing.map((s, i) => {
                      const skillName = safeStr(s)
                      const isHot = hotSet.has(skillName.toLowerCase())
                      return (
                        <span
                          key={`mm-${i}`}
                          className="px-2.5 py-1 bg-red-100 border-2 border-red-400 text-red-800 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <XCircle className="w-3 h-3 text-red-500" />
                          {skillName}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )
            })()}

            {/* Good-to-Have Skills */}
            {(() => {
              const matched = skill_analysis.matched_nice_to_have || []
              const missing = skill_analysis.missing_nice_to_have || []
              const total = matched.length + missing.length
              const hotSet = new Set((onet_hot_skills || []).map(s => typeof s === 'string' ? s.toLowerCase() : String(s).toLowerCase()))
              if (total === 0) return null
              return (
                <div className="bg-amber-50/50 rounded-2xl p-4 ring-1 ring-amber-100">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-5 h-5 rounded-md bg-amber-100 flex items-center justify-center">
                      <Star className="w-3 h-3 text-amber-600" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                      Good-to-Have Skills
                    </span>
                    <span className="text-xs font-semibold text-slate-500">
                      ({matched.length}/{total} matched)
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {matched.map((s, i) => {
                      const skillName = safeStr(s)
                      const isHot = hotSet.has(skillName.toLowerCase())
                      return (
                        <span
                          key={`gr-${i}`}
                          className="px-2.5 py-1 bg-green-50 border border-green-200 text-green-700 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <CheckCircle className="w-3 h-3 text-green-500" />
                          {skillName}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                          {skill_depth && skill_depth[skillName] && (
                            <span className="text-[10px] text-green-500 font-medium">({safeStr(skill_depth[skillName])}x)</span>
                          )}
                        </span>
                      )
                    })}
                    {missing.map((s, i) => {
                      const skillName = safeStr(s)
                      const isHot = hotSet.has(skillName.toLowerCase())
                      return (
                        <span
                          key={`gm-${i}`}
                          className="px-2.5 py-1 bg-amber-50 border border-amber-200 text-amber-700 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          {skillName}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )
            })()}
          </div>
        ) : (
          /* ── Legacy flat skill display (backward compat) ── */
          ((matched_skills?.length > 0) || (missing_skills?.length > 0)) && (
            <div className="grid grid-cols-2 gap-4">
              {matched_skills?.length > 0 && (
                <div className="bg-green-50 rounded-2xl p-4 ring-1 ring-green-100 border-l-4 border-green-500">
                  <div className="flex items-center gap-1.5 mb-2.5">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-xs font-bold text-green-700 uppercase tracking-wide">Matched</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {matched_skills.slice(0, 12).map((s, i) => (
                      <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-lg font-semibold inline-flex items-center gap-1">
                        {safeStr(s)}
                        {skill_depth && skill_depth[safeStr(s)] && (
                          <span className="text-[10px] text-green-600 font-medium">({safeStr(skill_depth[safeStr(s)])}x)</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {missing_skills?.length > 0 && (
                <div className="bg-red-50 rounded-2xl p-4 ring-1 ring-red-100 border-l-4 border-red-400">
                  <div className="flex items-center gap-1.5 mb-2.5">
                    <XCircle className="w-4 h-4 text-red-600" />
                    <span className="text-xs font-bold text-red-700 uppercase tracking-wide">Missing</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {missing_skills.slice(0, 10).map((s, i) => (
                      <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-lg font-semibold">{safeStr(s)}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        )}

        {/* Adjacent skills */}
        {adjacent_skills?.length > 0 && (
          <div className="bg-blue-50 rounded-2xl p-4 ring-1 ring-blue-100">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Compass className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-blue-700 uppercase tracking-wide">Adjacent Skills (bonus context)</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {adjacent_skills.slice(0, 10).map((s, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-lg font-semibold">{safeStr(s)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Skills Gap Visualization */}
        <SkillsRadar matchedSkills={matched_skills || []} missingSkills={missing_skills || []} />

        {/* Risk Flags Section */}
        {risk_summary?.risk_flags && risk_summary.risk_flags.length > 0 && (
          <div className="bg-slate-50 rounded-2xl p-5 ring-1 ring-slate-200">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Risk Flags</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {risk_summary.risk_flags.map((flag, i) => {
                const severityColors = {
                  high: 'bg-red-100 text-red-800 ring-red-200',
                  medium: 'bg-orange-100 text-orange-800 ring-orange-200',
                  low: 'bg-yellow-100 text-yellow-800 ring-yellow-200',
                }
                const colorClass = severityColors[flag.severity] || severityColors.low
                return (
                  <div
                    key={i}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold ring-1 ${colorClass} cursor-help`}
                    title={safeStr(flag.detail) || ''}
                  >
                    {safeStr(flag.flag)}
                    {flag.severity && (
                      <span className="ml-1.5 text-[10px] uppercase opacity-75">({safeStr(flag.severity)})</span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

    </>
  )
}
