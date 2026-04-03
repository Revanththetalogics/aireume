import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, FileUp, Type } from 'lucide-react'

export default function UploadForm({
  onFileSelect,
  jobDescription,
  onJobDescriptionChange,
  onJobFileSelect,
  onSubmit,
  isLoading,
  selectedFile,
  selectedJobFile,
  error
}) {
  const [jdMode, setJdMode] = useState('text') // 'text' or 'file'
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0])
    }
  }, [onFileSelect])

  const onJdDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onJobFileSelect(acceptedFiles[0])
      setJdMode('file')
    }
  }, [onJobFileSelect])

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

  const { getRootProps: getJdRootProps, getInputProps: getJdInputProps, isDragActive: isJdDragActive } = useDropzone({
    onDrop: onJdDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt']
    },
    maxFiles: 1,
    maxSize: 5 * 1024 * 1024 // 5MB
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
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-slate-700">
              Job Description
            </label>
            <div className="flex bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setJdMode('text')}
                className={`flex items-center gap-1 px-3 py-1 rounded-md text-sm transition-all ${
                  jdMode === 'text' ? 'bg-white shadow-sm text-blue-600' : 'text-slate-600'
                }`}
              >
                <Type className="w-4 h-4" />
                Text
              </button>
              <button
                onClick={() => setJdMode('file')}
                className={`flex items-center gap-1 px-3 py-1 rounded-md text-sm transition-all ${
                  jdMode === 'file' ? 'bg-white shadow-sm text-blue-600' : 'text-slate-600'
                }`}
              >
                <FileUp className="w-4 h-4" />
                File
              </button>
            </div>
          </div>

          {jdMode === 'text' ? (
            <textarea
              value={jobDescription}
              onChange={(e) => onJobDescriptionChange(e.target.value)}
              placeholder="Paste the job description here..."
              rows={6}
              className="w-full px-4 py-3 rounded-lg border border-slate-300
                         focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                         resize-none text-slate-700 placeholder-slate-400"
            />
          ) : (
            <div
              {...getJdRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
                transition-colors duration-200
                ${isJdDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-slate-300 hover:border-slate-400'
                }
                ${selectedJobFile ? 'bg-slate-50' : ''}
              `}
            >
              <input {...getJdInputProps()} />

              {selectedJobFile ? (
                <div className="flex items-center justify-center gap-3">
                  <FileText className="w-6 h-6 text-green-500" />
                  <div className="text-left">
                    <p className="font-medium text-slate-800">{selectedJobFile.name}</p>
                    <p className="text-sm text-slate-500">
                      {(selectedJobFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <FileUp className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <p className="text-slate-600 text-sm">
                    {isJdDragActive ? 'Drop JD file here...' : 'Upload JD (PDF, DOCX, TXT)'}
                  </p>
                </>
              )}
            </div>
          )}
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
          disabled={isLoading || !selectedFile || (jdMode === 'text' ? !jobDescription.trim() : !selectedJobFile)}
          className={`
            w-full py-3 px-6 rounded-lg font-semibold text-white
            transition-all duration-200
            ${isLoading || !selectedFile || (jdMode === 'text' ? !jobDescription.trim() : !selectedJobFile)
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
