import InterviewInitiateModal from './InterviewInitiateModal'

/**
 * @deprecated Use InterviewInitiateModal directly — kept for backward compatibility.
 */
export default function VoiceScheduleModal({
  onClose,
  onScheduled,
  preselectedCandidate = null,
  preselectedJdId = null,
  editSession = null,
}) {
  return (
    <InterviewInitiateModal
      onClose={onClose}
      onSuccess={onScheduled}
      editSession={editSession}
      preselectedCandidate={preselectedCandidate}
      initialJdId={preselectedJdId || ''}
      initialDepth="quick"
      lockDepth={Boolean(preselectedCandidate && !editSession)}
    />
  )
}
