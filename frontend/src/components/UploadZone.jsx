import { useState, useRef } from 'react'
import { uploadWorkbook } from '../hooks/useApi'
import './UploadZone.css'

export default function UploadZone({ onUploaded }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  async function handleFile(file) {
    if (!file) return
    if (!file.name.endsWith('.xlsx')) {
      setError('Only .xlsx files are supported.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const result = await uploadWorkbook(file)
      onUploaded(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  return (
    <div className="upload-zone-wrapper">
      <div
        className={`upload-zone card ${dragging ? 'upload-zone--dragging' : ''} ${loading ? 'upload-zone--loading' : ''}`}
        role="button"
        tabIndex={0}
        aria-label="Upload Excel file. Click or drag and drop an .xlsx file here."
        onClick={() => !loading && inputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && !loading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx"
          aria-hidden="true"
          tabIndex={-1}
          style={{ display: 'none' }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
        <div className="upload-zone__icon" aria-hidden="true">
          {loading ? '⏳' : '📊'}
        </div>
        <div className="upload-zone__text">
          {loading ? (
            <>
              <strong>Parsing workbook...</strong>
              <span>Extracting schema and generating embeddings</span>
            </>
          ) : (
            <>
              <strong>Upload an Excel workbook</strong>
              <span>Drag & drop or click to select an .xlsx file</span>
            </>
          )}
        </div>
      </div>
      {error && <p className="error-message" role="alert">{error}</p>}
    </div>
  )
}
