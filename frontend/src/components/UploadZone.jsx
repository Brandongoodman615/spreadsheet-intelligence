import { useState, useRef, useEffect } from 'react'
import { uploadWorkbook } from '../hooks/useApi'
import './UploadZone.css'

const UPLOAD_STEPS = [
  { label: 'Reading spreadsheet',          detail: 'Parsing sheets with pandas + openpyxl',        duration: 800  },
  { label: 'Analyzing sheet structure',    detail: 'Detecting headers, data rows, and skip rows',   duration: 3500 },
  { label: 'Profiling schema',             detail: 'Inferring column types, hints, and samples',    duration: 800  },
  { label: 'Detecting relationships',      detail: 'Finding cross-sheet joins with GPT-4o',         duration: 5000 },
  { label: 'Building search index',        detail: 'Embedding schema into pgvector',                duration: 800  },
]

export default function UploadZone({ onUploaded }) {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const stepTimer = useRef(null)

  useEffect(() => {
    if (!loading) {
      setStepIndex(0)
      return
    }
    let current = 0
    function advance() {
      current += 1
      if (current < UPLOAD_STEPS.length) {
        setStepIndex(current)
        stepTimer.current = setTimeout(advance, UPLOAD_STEPS[current].duration)
      }
    }
    stepTimer.current = setTimeout(advance, UPLOAD_STEPS[0].duration)
    return () => clearTimeout(stepTimer.current)
  }, [loading])

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
              <strong>
                {UPLOAD_STEPS[stepIndex].label}
                {stepIndex === UPLOAD_STEPS.length - 1 && <span className="upload-zone__ellipsis" aria-hidden="true" />}
              </strong>
              <span>{UPLOAD_STEPS[stepIndex].detail}</span>
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
