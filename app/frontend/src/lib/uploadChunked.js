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
 * Pure-JS MD5 implementation for environments where SubtleCrypto
 * is unavailable (non-HTTPS, incognito, or unsupported algorithms).
 */
function md5Fallback(data) {
  const K = []
  for (let i = 0; i < 64; i++) {
    K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296)
  }
  const S = [7,12,17,22,7,12,17,22,7,12,17,22,7,12,17,22,5,9,14,20,5,9,14,20,5,9,14,20,5,9,14,20,4,11,16,23,4,11,16,23,4,11,16,23,4,11,16,23,6,10,15,21,6,10,15,21,6,10,15,21,6,10,15,21]

  function rotateLeft(lValue, iShiftBits) {
    return (lValue << iShiftBits) | (lValue >>> (32 - iShiftBits))
  }

  function addUnsigned(lX, lY) {
    const lX8 = lX & 0x80000000, lY8 = lY & 0x80000000
    const lX4 = lX & 0x40000000, lY4 = lY & 0x40000000
    const lResult = (lX & 0x3FFFFFFF) + (lY & 0x3FFFFFFF)
    if (lX4 & lY4) return lResult ^ 0x80000000 ^ lX8 ^ lY8
    if (lX4 | lY4) {
      if (lResult & 0x40000000) return lResult ^ 0xC0000000 ^ lX8 ^ lY8
      return lResult ^ 0x40000000 ^ lX8 ^ lY8
    }
    return lResult ^ lX8 ^ lY8
  }

  function F(x, y, z) { return (x & y) | ((~x) & z) }
  function G(x, y, z) { return (x & z) | (y & (~z)) }
  function H(x, y, z) { return x ^ y ^ z }
  function I(x, y, z) { return y ^ (x | (~z)) }

  function FF(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(F(b, c, d), x), ac))
    return addUnsigned(rotateLeft(a, s), b)
  }
  function GG(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(G(b, c, d), x), ac))
    return addUnsigned(rotateLeft(a, s), b)
  }
  function HH(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(H(b, c, d), x), ac))
    return addUnsigned(rotateLeft(a, s), b)
  }
  function II(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(I(b, c, d), x), ac))
    return addUnsigned(rotateLeft(a, s), b)
  }

  function convertToWordArray(string) {
    let lWordCount, lMessageLength = string.length
    const lNumberOfWordsTemp1 = lMessageLength + 8
    const lNumberOfWordsTemp2 = (lNumberOfWordsTemp1 - (lNumberOfWordsTemp1 % 64)) / 64
    const lNumberOfWords = (lNumberOfWordsTemp2 + 1) * 16
    const lWordArray = new Array(lNumberOfWords - 1)
    let lBytePosition = 0, lByteCount = 0
    while (lByteCount < lMessageLength) {
      lWordCount = (lByteCount - (lByteCount % 4)) / 4
      lBytePosition = (lByteCount % 4) * 8
      lWordArray[lWordCount] = (lWordArray[lWordCount] || 0) | (string.charCodeAt(lByteCount) << lBytePosition)
      lByteCount++
    }
    lWordCount = (lByteCount - (lByteCount % 4)) / 4
    lBytePosition = (lByteCount % 4) * 8
    lWordArray[lWordCount] = lWordArray[lWordCount] | (0x80 << lBytePosition)
    lWordArray[lNumberOfWords - 2] = lMessageLength * 8
    return lWordArray
  }

  function wordToHex(lValue) {
    let wordToHexValue = '', wordToHexValueTemp = ''
    for (let lCount = 0; lCount <= 3; lCount++) {
      wordToHexValueTemp = (lValue >>> (lCount * 8)) & 255
      wordToHexValue += '0' + wordToHexValueTemp.toString(16)
      wordToHexValue = wordToHexValue.substr(wordToHexValue.length - 2, 2)
    }
    return wordToHexValue
  }

  let x = convertToWordArray(data)
  let a = 0x67452301, b = 0xEFCDAB89, c = 0x98BADCFE, d = 0x10325476

  for (let k = 0; k < x.length; k += 16) {
    const AA = a, BB = b, CC = c, DD = d
    a = FF(a, b, c, d, x[k + 0], S[0], K[0])
    d = FF(d, a, b, c, x[k + 1], S[1], K[1])
    c = FF(c, d, a, b, x[k + 2], S[2], K[2])
    b = FF(b, c, d, a, x[k + 3], S[3], K[3])
    a = FF(a, b, c, d, x[k + 4], S[4], K[4])
    d = FF(d, a, b, c, x[k + 5], S[5], K[5])
    c = FF(c, d, a, b, x[k + 6], S[6], K[6])
    b = FF(b, c, d, a, x[k + 7], S[7], K[7])
    a = FF(a, b, c, d, x[k + 8], S[8], K[8])
    d = FF(d, a, b, c, x[k + 9], S[9], K[9])
    c = FF(c, d, a, b, x[k + 10], S[10], K[10])
    b = FF(b, c, d, a, x[k + 11], S[11], K[11])
    a = FF(a, b, c, d, x[k + 12], S[12], K[12])
    d = FF(d, a, b, c, x[k + 13], S[13], K[13])
    c = FF(c, d, a, b, x[k + 14], S[14], K[14])
    b = FF(b, c, d, a, x[k + 15], S[15], K[15])
    a = GG(a, b, c, d, x[k + 1], S[16], K[16])
    d = GG(d, a, b, c, x[k + 6], S[17], K[17])
    c = GG(c, d, a, b, x[k + 11], S[18], K[18])
    b = GG(b, c, d, a, x[k + 0], S[19], K[19])
    a = GG(a, b, c, d, x[k + 5], S[20], K[20])
    d = GG(d, a, b, c, x[k + 10], S[21], K[21])
    c = GG(c, d, a, b, x[k + 15], S[22], K[22])
    b = GG(b, c, d, a, x[k + 4], S[23], K[23])
    a = GG(a, b, c, d, x[k + 9], S[24], K[24])
    d = GG(d, a, b, c, x[k + 14], S[25], K[25])
    c = GG(c, d, a, b, x[k + 3], S[26], K[26])
    b = GG(b, c, d, a, x[k + 8], S[27], K[27])
    a = GG(a, b, c, d, x[k + 13], S[28], K[28])
    d = GG(d, a, b, c, x[k + 2], S[29], K[29])
    c = GG(c, d, a, b, x[k + 7], S[30], K[30])
    b = GG(b, c, d, a, x[k + 12], S[31], K[31])
    a = HH(a, b, c, d, x[k + 5], S[32], K[32])
    d = HH(d, a, b, c, x[k + 8], S[33], K[33])
    c = HH(c, d, a, b, x[k + 11], S[34], K[34])
    b = HH(b, c, d, a, x[k + 14], S[35], K[35])
    a = HH(a, b, c, d, x[k + 1], S[36], K[36])
    d = HH(d, a, b, c, x[k + 4], S[37], K[37])
    c = HH(c, d, a, b, x[k + 7], S[38], K[38])
    b = HH(b, c, d, a, x[k + 10], S[39], K[39])
    a = HH(a, b, c, d, x[k + 13], S[40], K[40])
    d = HH(d, a, b, c, x[k + 0], S[41], K[41])
    c = HH(c, d, a, b, x[k + 3], S[42], K[42])
    b = HH(b, c, d, a, x[k + 6], S[43], K[43])
    a = HH(a, b, c, d, x[k + 9], S[44], K[44])
    d = HH(d, a, b, c, x[k + 12], S[45], K[45])
    c = HH(c, d, a, b, x[k + 15], S[46], K[46])
    b = HH(b, c, d, a, x[k + 2], S[47], K[47])
    a = II(a, b, c, d, x[k + 0], S[48], K[48])
    d = II(d, a, b, c, x[k + 7], S[49], K[49])
    c = II(c, d, a, b, x[k + 14], S[50], K[50])
    b = II(b, c, d, a, x[k + 5], S[51], K[51])
    a = II(a, b, c, d, x[k + 12], S[52], K[52])
    d = II(d, a, b, c, x[k + 3], S[53], K[53])
    c = II(c, d, a, b, x[k + 10], S[54], K[54])
    b = II(b, c, d, a, x[k + 1], S[55], K[55])
    a = II(a, b, c, d, x[k + 8], S[56], K[56])
    d = II(d, a, b, c, x[k + 15], S[57], K[57])
    c = II(c, d, a, b, x[k + 6], S[58], K[58])
    b = II(b, c, d, a, x[k + 13], S[59], K[59])
    a = II(a, b, c, d, x[k + 4], S[60], K[60])
    d = II(d, a, b, c, x[k + 11], S[61], K[61])
    c = II(c, d, a, b, x[k + 2], S[62], K[62])
    b = II(b, c, d, a, x[k + 9], S[63], K[63])
    a = addUnsigned(a, AA)
    b = addUnsigned(b, BB)
    c = addUnsigned(c, CC)
    d = addUnsigned(d, DD)
  }

  return wordToHex(a) + wordToHex(b) + wordToHex(c) + wordToHex(d)
}

/**
 * Calculate MD5 hash of a file for integrity verification.
 * Uses Web Crypto API when available, falls back to pure-JS MD5.
 */
async function calculateMD5(file) {
  const arrayBuffer = await file.arrayBuffer()
  // Try Web Crypto API first (fast, native)
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    try {
      const hashBuffer = await crypto.subtle.digest('MD5', arrayBuffer)
      const hashArray = Array.from(new Uint8Array(hashBuffer))
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
    } catch {
      // SubtleCrypto may not support MD5 (incognito, non-HTTPS, etc.)
    }
  }
  // Fallback: pure-JS MD5
  const bytes = new Uint8Array(arrayBuffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return md5Fallback(binary)
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
