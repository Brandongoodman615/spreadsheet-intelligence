import { useState } from 'react'
import './AnswerCard.css'

export default function AnswerCard({ result }) {
  const [showSql, setShowSql] = useState(false)

  const isTable = Array.isArray(result.answer)
  const isSingleValue = result.answer !== null && !isTable

  const formatScalar = (val) => {
    if (typeof val === 'number') {
      // Clean up floating point noise (e.g. 250885.99999999997 → 250,886)
      const rounded = Math.round(val * 1e9) / 1e9
      return Number.isInteger(rounded)
        ? rounded.toLocaleString()
        : rounded.toLocaleString(undefined, { maximumFractionDigits: 4 })
    }
    return String(val)
  }

  return (
    <article className="answer-card card" aria-label={`Answer to: ${result.question}`}>
      <div className="answer-card__question">
        <span className="answer-card__q-icon" aria-hidden="true">?</span>
        <p>{result.question}</p>
      </div>

      <div className="answer-card__body">
        {result.answer === null ? (
          <p className="answer-card__empty">No results found.</p>
        ) : isSingleValue ? (
          <div className="answer-card__value" aria-live="polite">
            <span className="answer-card__big-value">{formatScalar(result.answer)}</span>
          </div>
        ) : (
          <div className="answer-card__table-wrapper" role="region" aria-label="Query results">
            <PreviewTable rows={result.preview_rows} />
            {result.attribution.rows_matched > 5 && (
              <p className="answer-card__row-count">
                Showing 5 of {result.attribution.rows_matched} rows
              </p>
            )}
          </div>
        )}

        {result.explanation && (
          <p className="answer-card__explanation">{result.explanation}</p>
        )}
      </div>

      <div className="answer-card__attribution">
        <div className="answer-card__attr-chips">
          {result.attribution.sheets.map((s) => (
            <span key={s} className="badge badge-blue">{s}</span>
          ))}
          <span className="badge badge-gray">
            {result.attribution.rows_matched} row{result.attribution.rows_matched !== 1 ? 's' : ''}
          </span>
        </div>

        <button
          className="btn btn-ghost answer-card__sql-toggle"
          onClick={() => setShowSql((v) => !v)}
          aria-expanded={showSql}
          aria-controls={`sql-block-${result.question}`}
        >
          {showSql ? 'Hide SQL' : 'View SQL'}
        </button>
      </div>

      {showSql && (
        <div
          className="answer-card__sql"
          id={`sql-block-${result.question}`}
          role="region"
          aria-label="Generated SQL"
        >
          <pre><code>{result.sql}</code></pre>
        </div>
      )}
    </article>
  )
}

function PreviewTable({ rows }) {
  if (!rows || rows.length === 0) return null
  const headers = Object.keys(rows[0])

  return (
    <div className="preview-table-wrapper">
      <table className="preview-table" aria-label="Result preview">
        <thead>
          <tr>
            {headers.map((h) => <th key={h}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {headers.map((h) => (
                <td key={h}>{row[h] === null || row[h] === undefined ? '—' : String(row[h])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
