/**
 * Chunked file upload utility for handling large files that exceed CDN/proxy limits.
 * 
 * This module provides a robust chunked upload system that:
 * - Splits large files into 10MB chunks
 * - Uploads chunks with retry logic and progress tracking
 * - Assembles chunks on the server
 * - Provides real-time progress updates per file
 * - Handles network failures gracefully
 * 
 * Usage:
 *   const uploader = new ChunkedUploader(file, {
 *     onProgress: (progress) => console.log(`${progress.percent}% uploaded`),
 *     onComplete: (result) => console.log('Upload complete:', result),
 *     onError: (error) => console.error('Upload failed:', error)
 *   });
 *   await uploader.start();
 */

import { nanoid } from 'nanoid'
import api from './api'

const CHUNK_SIZE = 10 * 1024 * 1024 // 10MB chunks (stays under Cloudflare 100MB limit)
const MAX_RETRIES = 3
const RETRY_DELAY_MS = 1000

/**
 * Calculate MD5 hash of a file for integrity verification.
 * Uses Web Crypto API for efficient hashing.
 */
async function calculateMD5(file) {
  const arrayBuffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('MD5', arrayBuffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

/**
 * Sleep utility for retry delays.
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * ChunkedUploader class - handles uploading a single file in chunks.
 */
export class ChunkedUploader {
  constructor(file, options = {}) {
    this.file = file
    this.uploadId = nanoid()
    this.totalChunks = Math.ceil(file.size / CHUNK_SIZE)
    this.uploadedChunks = new Set()
    this.aborted = false
    
    // Callbacks
    this.onProgress = options.onProgress || (() => {})
    this.onComplete = options.onComplete || (() => {})
    this.onError = options.onError || (() => {})
    
    // Progress tracking
    this.bytesUploaded = 0
    this.startTime = null
  }

  /**
   * Start the chunked upload process.
   */
  async start() {
    this.startTime = Date.now()
    this.aborted = false
    
    try {
      // Upload all chunks
      await this.uploadChunks()
      
      // Finalize upload on server
      const result = await this.finalizeUpload()
      
      this.onComplete({
        uploadId: this.uploadId,
        filename: this.file.name,
        fileSize: this.file.size,
        ...result
      })
      
      return result
    } catch (error) {
      this.onError(error)
      throw error
    }
  }

  /**
   * Upload all chunks with parallel processing and retry logic.
   */
  async uploadChunks() {
    const chunks = []
    
    // Split file into chunks
    for (let i = 0; i < this.totalChunks; i++) {
      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, this.file.size)
      const chunk = this.file.slice(start, end)
      chunks.push({ index: i, blob: chunk })
    }
    
    // Upload chunks with concurrency limit (3 parallel uploads)
    const concurrency = 3
    const results = []
    
    for (let i = 0; i < chunks.length; i += concurrency) {
      if (this.aborted) {
        throw new Error('Upload aborted by user')
      }
      
      const batch = chunks.slice(i, i + concurrency)
      const batchPromises = batch.map(chunk => this.uploadChunk(chunk.index, chunk.blob))
      
      const batchResults = await Promise.all(batchPromises)
      results.push(...batchResults)
    }
    
    return results
  }

  /**
   * Upload a single chunk with retry logic.
   */
  async uploadChunk(chunkIndex, chunkBlob, retryCount = 0) {
    if (this.aborted) {
      throw new Error('Upload aborted by user')
    }
    
    try {
      const formData = new FormData()
      formData.append('upload_id', this.uploadId)
      formData.append('chunk_index', chunkIndex)
      formData.append('total_chunks', this.totalChunks)
      formData.append('filename', this.file.name)
      formData.append('chunk', chunkBlob)
      
      const response = await api.post('/upload/chunk', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000, // 60 second timeout per chunk
      })
      
      // Mark chunk as uploaded
      this.uploadedChunks.add(chunkIndex)
      this.bytesUploaded += chunkBlob.size
      
      // Update progress
      this.updateProgress()
      
      return response.data
    } catch (error) {
      // Retry logic
      if (retryCount < MAX_RETRIES) {
        await sleep(RETRY_DELAY_MS * (retryCount + 1))
        return this.uploadChunk(chunkIndex, chunkBlob, retryCount + 1)
      }
      
      throw new Error(`Failed to upload chunk ${chunkIndex} after ${MAX_RETRIES} retries: ${error.message}`)
    }
  }

  /**
   * Finalize the upload by assembling chunks on the server.
   */
  async finalizeUpload() {
    try {
      // Calculate file hash for integrity check (optional but recommended)
      let fileHash = null
      try {
        fileHash = await calculateMD5(this.file)
      } catch (e) {
        console.warn('MD5 calculation failed, skipping integrity check:', e)
      }
      
      const response = await api.post('/upload/finalize', {
        upload_id: this.uploadId,
        filename: this.file.name,
        total_chunks: this.totalChunks,
        file_hash: fileHash,
      })
      
      return response.data
    } catch (error) {
      throw new Error(`Failed to finalize upload: ${error.message}`)
    }
  }

  /**
   * Update progress and notify callback.
   */
  updateProgress() {
    const percent = Math.round((this.bytesUploaded / this.file.size) * 100)
    const elapsed = Date.now() - this.startTime
    const speed = this.bytesUploaded / (elapsed / 1000) // bytes per second
    const remaining = (this.file.size - this.bytesUploaded) / speed // seconds
    
    this.onProgress({
      uploadId: this.uploadId,
      filename: this.file.name,
      bytesUploaded: this.bytesUploaded,
      totalBytes: this.file.size,
      percent,
      speed,
      remainingSeconds: remaining,
      chunksUploaded: this.uploadedChunks.size,
      totalChunks: this.totalChunks,
    })
  }

  /**
   * Abort the upload.
   */
  abort() {
    this.aborted = true
    
    // Cancel upload on server
    api.delete(`/upload/cancel/${this.uploadId}`).catch(err => {
      console.warn('Failed to cancel upload on server:', err)
    })
  }
}

/**
 * Upload multiple files in chunks with progress tracking.
 * 
 * @param {File[]} files - Array of File objects to upload
 * @param {Object} options - Upload options
 * @param {Function} options.onFileProgress - Callback for individual file progress
 * @param {Function} options.onOverallProgress - Callback for overall progress
 * @param {Function} options.onFileComplete - Callback when a file completes
 * @param {Function} options.onFileError - Callback when a file fails
 * @param {Function} options.onAllComplete - Callback when all files complete
 * 
 * @returns {Promise<Object>} Results object with successful and failed uploads
 */
export async function uploadMultipleFiles(files, options = {}) {
  const {
    onFileProgress = () => {},
    onOverallProgress = () => {},
    onFileComplete = () => {},
    onFileError = () => {},
    onAllComplete = () => {},
  } = options
  
  const totalFiles = files.length
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0)
  let completedFiles = 0
  let uploadedBytes = 0
  
  const results = {
    successful: [],
    failed: [],
  }
  
  // Track progress for each file
  const fileProgress = new Map()
  
  const updateOverallProgress = () => {
    const overallPercent = Math.round((uploadedBytes / totalBytes) * 100)
    onOverallProgress({
      completedFiles,
      totalFiles,
      uploadedBytes,
      totalBytes,
      percent: overallPercent,
    })
  }
  
  // Upload files sequentially to avoid overwhelming the server
  for (const file of files) {
    try {
      const uploader = new ChunkedUploader(file, {
        onProgress: (progress) => {
          // Update file-specific progress
          fileProgress.set(file.name, progress)
          onFileProgress(file.name, progress)
          
          // Update overall progress
          uploadedBytes = Array.from(fileProgress.values())
            .reduce((sum, p) => sum + p.bytesUploaded, 0)
          updateOverallProgress()
        },
        onComplete: (result) => {
          completedFiles++
          results.successful.push({ file: file.name, result })
          onFileComplete(file.name, result)
          updateOverallProgress()
        },
        onError: (error) => {
          completedFiles++
          results.failed.push({ file: file.name, error: error.message })
          onFileError(file.name, error)
          updateOverallProgress()
        },
      })
      
      await uploader.start()
    } catch (error) {
      // Error already handled in onError callback
      console.error(`Upload failed for ${file.name}:`, error)
    }
  }
  
  onAllComplete(results)
  return results
}

/**
 * Get the assembled file path for use in batch analysis.
 * This is called after chunked upload completes.
 */
export function getAssembledFilePath(uploadId, filename) {
  return `/tmp/aria_chunks/assembled/${uploadId}_${filename}`
}

export default {
  ChunkedUploader,
  uploadMultipleFiles,
  getAssembledFilePath,
}
