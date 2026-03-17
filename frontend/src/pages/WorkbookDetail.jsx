import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getWorkbook } from '../hooks/useApi'
import SchemaPanel from '../components/SchemaPanel'
import QueryChat from '../components/QueryChat'
import './WorkbookDetail.css'

export default function WorkbookDetail() {
  const { id } = useParams()
  const [workbook, setWorkbook] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getWorkbook(id)
      .then(setWorkbook)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="detail-loading" role="status" aria-label="Loading workbook">
        <span className="detail-spinner" aria-hidden="true" />
        <span>Loading workbook…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="detail-error">
        <p className="error-message" role="alert">{error}</p>
        <Link to="/" className="btn btn-ghost" style={{ marginTop: 12 }}>
          ← Back to home
        </Link>
      </div>
    )
  }

  const schema = workbook?.schema

  return (
    <div className="detail">
      <div className="detail__header">
        <Link to="/" className="btn btn-ghost detail__back" aria-label="Back to home">
          ← Back
        </Link>
        <div className="detail__title-group">
          <h1 className="detail__title">{workbook.original_name}</h1>
          <div className="detail__meta">
            <span className="badge badge-blue">{schema.sheet_count} sheet{schema.sheet_count !== 1 ? 's' : ''}</span>
            {schema.has_formulas && <span className="badge badge-green">Contains formulas</span>}
            <span className="badge badge-gray">{workbook.id}</span>
          </div>
        </div>
      </div>

      <div className="detail__layout">
        <div className="detail__sidebar">
          <SchemaPanel schema={schema} />
        </div>
        <div className="detail__main">
          <QueryChat workbookId={Number(id)} />
        </div>
      </div>
    </div>
  )
}
