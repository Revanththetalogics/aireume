import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle } from 'lucide-react'

export default function UploadForm({
  onFileSelect,
  jobDescription,
  onJobDescriptionChange,
  onSubmit,
  isLoading,
  selectedFile,
  error
}) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024 // 10MB
  })

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8">
        <h2 className="text-2xl font-semibold text-slate-800 mb-6">
          Upload Resume & Job Description
        </h2>

        {/* Resume Upload */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Resume (PDF or DOCX)
          </label>

          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
              transition-colors duration-200
              ${isDragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-300 hover:border-slate-400'
              }
              ${selectedFile ? 'bg-slate-50' : ''}
            `}
          >
            <input {...getInputProps()} />

            {selectedFile ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="w-8 h-8 text-blue-500" />
                <div className="text-left">
                  <p className="font-medium text-slate-800">{selectedFile.name}</p>
                  <p className="text-sm text-slate-500">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
            ) : (
              <>
                <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                <p className="text-slate-600 mb-1">
                  {isDragActive ? 'Drop the file here...' : 'Drag & drop your resume here'}
                </p>
                <p className="text-sm text-slate-400">
                  or click to browse (PDF, DOCX up to 10MB)
                </p>
              </>
            )}
          </div>
        </div>

        {/* Job Description */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Job Description
          </label>
          <textarea
            value={jobDescription}
            onChange={(e) => onJobDescriptionChange(e.target.value)}
            placeholder="Paste the job description here..."
            rows={6}
            className="w-full px-4 py-3 rounded-lg border border-slate-300
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                       resize-none text-slate-700 placeholder-slate-400"
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={onSubmit}
          disabled={isLoading || !selectedFile || !jobDescription.trim()}
          className={`
            w-full py-3 px-6 rounded-lg font-semibold text-white
            transition-all duration-200
            ${isLoading || !selectedFile || !jobDescription.trim()
              ? 'bg-slate-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'
            }
          `}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            'Analyze Resume'
          )}
        </button>
      </div>
    </div>
  )
}
