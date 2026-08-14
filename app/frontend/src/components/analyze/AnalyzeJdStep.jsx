import {
  AlertCircle, FileText, FileUp, Link2, Loader2, RefreshCw, ShieldCheck, Type, X,
} from 'lucide-react'
import { parseJdPreview, parseJdPreviewFromFile, updateRequisition } from '../../lib/api'
import { extractRoleTitle } from '../../lib/analyzeBatchUtils'
import { ANALYZE } from '../../lib/uxLabels'
import SkillClassificationEditor from '../SkillClassificationEditor'
import {
  AdHocModeToggle,
  RequisitionContextBar,
  RequisitionPickerPanel,
} from './AnalyzeRequisitionStep'

export default function AnalyzeJdStep(props) {
  const {
    hasRequisitions,
    screeningMode,
    showRequisitionFirst,
    adHocMode,
    enableAdHocMode,
    clearRequisitionSelection,
    requisitions,
    requisitionsLoading,
    requisitionSearch,
    setRequisitionSearch,
    handleLoadRequisition,
    navigate,
    requisitionRequired,
    showLoadedRequisition,
    loadedRequisition,
    intakeGateStatus,
    remainingAnalyses,
    setShowJdModal,
    showAdHocInput,
    jdMode,
    setJdMode,
    hasLoadedRequisition,
    jdText,
    setJdText,
    skillsConfirmed,
    setSkillsConfirmed,
    setSkillOverrides,
    jdParseResult,
    setJdParseResult,
    showAiSuggestion,
    setShowAiSuggestion,
    roleName,
    setRoleName,
    roleNameTouchedRef,
    roleCategory,
    parsingJd,
    setParsingJd,
    parseError,
    setParseError,
    jdFile,
    setJdFile,
    getJdRootProps,
    getJdInputProps,
    isJdDragActive,
    urlInput,
    setUrlInput,
    handleExtractUrl,
    urlLoading,
    urlError,
    loadedRequisitionId,
    skillOverrides,
  } = props

  return (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8 card-animate">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <h2 className="text-xl font-bold text-brand-900">
              {hasRequisitions ? ANALYZE.step1TitleRequisition : ANALYZE.step1Title}
            </h2>
            {hasRequisitions && screeningMode === 'allow_ad_hoc' && !showRequisitionFirst && (
              <AdHocModeToggle
                active={adHocMode}
                onEnable={enableAdHocMode}
                onDisable={clearRequisitionSelection}
              />
            )}
          </div>

          {showRequisitionFirst && (
            <>
              <RequisitionPickerPanel
                requisitions={requisitions}
                loading={requisitionsLoading}
                search={requisitionSearch}
                onSearchChange={setRequisitionSearch}
                onSelect={handleLoadRequisition}
                onCreateNew={() => navigate('/requisitions')}
              />
              {screeningMode === 'allow_ad_hoc' && (
                <div className="mt-4 text-center">
                  <AdHocModeToggle active={false} onEnable={enableAdHocMode} onDisable={clearRequisitionSelection} />
                </div>
              )}
              {requisitionRequired && (
                <p className="mt-4 text-xs text-slate-500 text-center">{ANALYZE.adHocDisabledHint}</p>
              )}
            </>
          )}

          {showLoadedRequisition && loadedRequisition && (
            <RequisitionContextBar
              requisition={loadedRequisition}
              intakeGate={intakeGateStatus}
              remainingAnalyses={remainingAnalyses}
              onChangeRole={clearRequisitionSelection}
              onViewFullJd={() => setShowJdModal(true)}
            />
          )}

          {showAdHocInput && (
            <>
          {/* JD Mode Tabs */}
          <div className="flex gap-2 mb-4">
            {[
              { mode: 'text', icon: Type, label: 'Paste Text' },
              { mode: 'file', icon: FileUp, label: 'Upload File' },
              { mode: 'url', icon: Link2, label: 'Extract from URL' }
            ].map(({ mode, icon: Icon, label }) => (
              <button
                key={mode}
                type="button"
                onClick={() => setJdMode(mode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  jdMode === mode
                    ? 'bg-brand-600 text-white shadow-brand-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* Role title — saved as requisition on Growth+ ad-hoc path */}
          {hasRequisitions && !hasLoadedRequisition && (jdMode === 'text' ? jdText.trim().length > 50 : jdFile) && (
            <div className="mb-4">
              <label htmlFor="role-name" className="block text-sm font-semibold text-brand-900 mb-1.5">
                Role name
              </label>
              <input
                id="role-name"
                type="text"
                value={roleName}
                onChange={(e) => {
                  roleNameTouchedRef.current = true
                  setRoleName(e.target.value)
                }}
                placeholder={extractRoleTitle(jdParseResult, roleCategory, '') || 'e.g. Talent Acquisition Specialist'}
                className="w-full px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
              />
              <p className="text-xs text-slate-500 mt-1.5">
                {parsingJd
                  ? 'Detecting role title from job description…'
                  : 'Saved as a requisition when you analyze. Edit if the detected title is wrong.'}
              </p>
            </div>
          )}

          {/* JD Input */}
          {jdMode === 'text' && (
            <div>
              <textarea
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value)
                  // Reset skill confirmation when JD text changes
                  if (skillsConfirmed) {
                    setSkillsConfirmed(false)
                    setSkillOverrides(null)
                    setJdParseResult(null)
                  }
                  if (e.target.value.length > 100 && !showAiSuggestion) {
                    setShowAiSuggestion(true)
                  }
                }}
                placeholder="Paste the job description here... (minimum 50 characters)"
                className="w-full h-64 px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none text-sm"
              />
              <p className="text-xs text-slate-500 mt-2">
                {jdText.length} characters • {jdText.split(/\s+/).filter(Boolean).length} words
              </p>

              {/* Short JD hint */}
              {jdText.trim() && jdText.split(/\s+/).filter(Boolean).length < 80 && (
                <div className="mt-3 flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                  <p className="text-xs text-amber-700">
                    Add more detail to the job description for better skill extraction ({jdText.split(/\s+/).filter(Boolean).length}/80 words minimum)
                  </p>
                </div>
              )}

              {/* Parsing indicator */}
              {parsingJd && jdMode === 'text' && (
                <div className="mt-3 flex items-center gap-2 p-3 bg-brand-50 border border-brand-200 rounded-xl">
                  <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                  <p className="text-xs text-brand-700 font-medium">Parsing job description…</p>
                </div>
              )}

              {/* Parse error with retry */}
              {parseError && !parsingJd && jdMode === 'text' && (
                <div className="mt-3 flex items-center justify-between gap-2 p-3 bg-red-50 border border-red-200 rounded-xl">
                  <p className="text-xs text-red-700">{parseError}</p>
                  <button
                    type="button"
                    onClick={async () => {
                      setParseError(null)
                      setParsingJd(true)
                      try {
                        if (jdMode === 'file' && jdFile) {
                          const data = await parseJdPreviewFromFile(jdFile)
                          setJdParseResult(data)
                        } else {
                          const data = await parseJdPreview(jdText)
                          setJdParseResult(data)
                        }
                      } catch (err) {
                        setParseError(err.message || 'Failed to parse job description')
                      } finally {
                        setParsingJd(false)
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50 transition-all shrink-0"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                </div>
              )}
            </div>
          )}

          {jdMode === 'file' && (
            <div>
              <div
                {...getJdRootProps()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                  isJdDragActive
                    ? 'border-brand-500 bg-brand-50'
                    : jdFile
                    ? 'border-brand-200 bg-brand-50/40'
                    : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
                }`}
              >
                <input {...getJdInputProps()} />
                {jdFile ? (
                  <div className="flex items-center justify-center gap-3">
                    <FileText className="w-8 h-8 text-brand-600" />
                    <div>
                      <p className="font-semibold text-brand-900">{jdFile.name}</p>
                      <p className="text-xs text-slate-500">{(jdFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setJdFile(null)
                        setSkillsConfirmed(false)
                        setSkillOverrides(null)
                        setJdParseResult(null)
                      }}
                      aria-label="Remove job description file"
                      className="ml-4 p-2 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ) : (
                  <div>
                    <FileUp className="w-12 h-12 text-brand-400 mx-auto mb-3" />
                    <p className="text-sm font-medium text-slate-700">Drop JD file here or click to browse</p>
                    <p className="text-xs text-slate-500 mt-1">PDF, DOCX, or TXT (max 5MB)</p>
                  </div>
                )}
              </div>
              {/* File mode parsing indicator */}
              {parsingJd && jdMode === 'file' && (
                <div className="mt-3 flex items-center gap-2 p-3 bg-brand-50 border border-brand-200 rounded-xl">
                  <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                  <p className="text-xs text-brand-700 font-medium">Parsing job description file…</p>
                </div>
              )}
              {/* File mode parse error */}
              {parseError && !parsingJd && jdMode === 'file' && (
                <div className="mt-3 flex items-center justify-between gap-2 p-3 bg-red-50 border border-red-200 rounded-xl">
                  <p className="text-xs text-red-700">{parseError}</p>
                  <button
                    type="button"
                    onClick={async () => {
                      setParseError(null)
                      setParsingJd(true)
                      try {
                        const data = await parseJdPreviewFromFile(jdFile)
                        setJdParseResult(data)
                      } catch (err) {
                        setParseError(err.message || 'Failed to parse job description file')
                      } finally {
                        setParsingJd(false)
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50 transition-all shrink-0"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                </div>
              )}
            </div>
          )}

          {jdMode === 'url' && (
            <div>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example.com/job-posting"
                  className="flex-1 px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
                />
                <button
                  onClick={handleExtractUrl}
                  disabled={urlLoading || !urlInput.trim()}
                  className="px-6 py-3 bg-brand-600 text-white rounded-2xl font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  {urlLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Extracting...
                    </>
                  ) : (
                    'Extract'
                  )}
                </button>
              </div>
              {urlError && (
                <p className="text-sm text-red-600 mt-2">{urlError}</p>
              )}
            </div>
          )}
            </>
          )}

          {showLoadedRequisition && !skillsConfirmed && parsingJd && (
            <div className="mt-3 flex items-center gap-2 p-3 bg-brand-50 border border-brand-200 rounded-xl">
              <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
              <p className="text-xs text-brand-700 font-medium">Parsing job description from requisition…</p>
            </div>
          )}

          {/* ── Inline Skill Classification Editor (shown after JD is parsed, before confirmation) ── */}
          {(showAdHocInput || showLoadedRequisition) && jdParseResult && !skillsConfirmed && (
            <div className="mt-6">
              <SkillClassificationEditor
                data={jdParseResult}
                onConfirm={async (overrides) => {
                  setSkillOverrides(overrides)
                  setSkillsConfirmed(true)
                  // Persist overrides to requisition so they are restored on next load
                  if (loadedRequisitionId) {
                    try {
                      await updateRequisition(loadedRequisitionId, {
                        required_skills_override: overrides.required_skills,
                        nice_to_have_skills_override: overrides.nice_to_have_skills,
                      })
                    } catch (err) {
                      console.warn('Failed to persist skill overrides to requisition:', err)
                    }
                  }
                }}
                onSkip={() => {
                  setSkillOverrides(null)
                  setSkillsConfirmed(true)
                }}
                loading={false}
              />
            </div>
          )}

          {/* ── Skills Confirmed Badge ── */}
          {(showAdHocInput || showLoadedRequisition) && skillsConfirmed && (
            <div className="mt-6 flex items-center gap-3 flex-wrap p-3 bg-green-50 border border-green-200 rounded-2xl">
              <ShieldCheck className="w-4 h-4 text-green-600 shrink-0" />
              <span className="text-sm font-medium text-green-700">
                {jdParseResult?.restored_from_requisition
                  ? (jdParseResult?.skill_source === 'calibrated'
                    ? ANALYZE.skillsFromCalibrated
                    : ANALYZE.skillsFromRequisition)
                  : jdParseResult?.restored_from_template
                  ? 'Skills restored from saved template'
                  : 'Skills confirmed'}
                {skillOverrides && !jdParseResult?.restored_from_template
                  ? ` — ${Array.isArray(skillOverrides.required_skills) ? skillOverrides.required_skills.length : 0} must-have, ${Array.isArray(skillOverrides.nice_to_have_skills) ? skillOverrides.nice_to_have_skills.length : 0} good-to-have`
                  : skillOverrides && jdParseResult?.restored_from_template
                  ? ` — ${Array.isArray(skillOverrides.required_skills) ? skillOverrides.required_skills.length : 0} must-have, ${Array.isArray(skillOverrides.nice_to_have_skills) ? skillOverrides.nice_to_have_skills.length : 0} good-to-have`
                  : ' — using AI defaults'}
              </span>
              {jdParseResult?.jd_quality && (
                <span className="text-sm font-medium text-emerald-700">
                  JD Quality: {jdParseResult.jd_quality.grade} ({jdParseResult.jd_quality.overall_score}/100)
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  setSkillsConfirmed(false)
                  // Clear restored flag so user can re-edit from fresh parse
                  if (jdParseResult?.restored_from_template) {
                    setJdParseResult(null)
                    setSkillOverrides(null)
                  }
                }}
                className="ml-auto text-xs text-green-500 hover:text-green-700 underline"
              >
                Re-edit
              </button>
            </div>
          )}
        </div>

  )
}
