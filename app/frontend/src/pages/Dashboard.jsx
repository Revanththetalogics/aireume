import { useState } from 'react'
import { Sparkles, History } from 'lucide-react'
import UploadForm from '../components/UploadForm'
import ScoreGauge from '../components/ScoreGauge'
import ResultCard from '../components/ResultCard'
import Timeline from '../components/Timeline'
import { analyzeResume } from '../lib/api'

export default function Dashboard() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [selectedJobFile, setSelectedJobFile] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    const hasJd = jobDescription.trim() || selectedJobFile
    if (!selectedFile || !hasJd) {
      setError('Please upload a resume and provide a job description (text or file)')
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await analyzeResume(selectedFile, jobDescription, selectedJobFile)
      setResult(data)
    } catch (err) {
      console.error('Analysis error:', err)
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to analyze resume. Please try again.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-blue-600" />
            <h1 className="text-xl font-bold text-slate-800">
              AI Resume Screener
            </h1>
            <span className="text-sm text-slate-500 ml-2">by ThetaLogics</span>
          </div>

          <a
            href="/api/history"
            className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-800"
          >
            <History className="w-4 h-4" />
            <span className="hidden sm:inline">History</span>
          </a>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Form */}
        <UploadForm
          onFileSelect={setSelectedFile}
          jobDescription={jobDescription}
          onJobDescriptionChange={setJobDescription}
          onJobFileSelect={setSelectedJobFile}
          onSubmit={handleSubmit}
          isLoading={isLoading}
          selectedFile={selectedFile}
          selectedJobFile={selectedJobFile}
          error={error}
        />

        {/* Results Section */}
        {result && (
          <div className="mt-8 space-y-6">
            {/* Score Section */}
            <div className="grid md:grid-cols-3 gap-6">
              <div className="md:col-span-1">
                <ScoreGauge score={result.fit_score} />
              </div>
              <div className="md:col-span-2">
                <ResultCard result={result} />
              </div>
            </div>

            {/* Timeline Section */}
            <Timeline
              workExperience={result.work_experience || []}
              gaps={result.employment_gaps || []}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-sm text-slate-500">
        <p>Powered by Ollama (llama3) • Local-first AI • No data leaves your VPS</p>
      </footer>
    </div>
  )
}
