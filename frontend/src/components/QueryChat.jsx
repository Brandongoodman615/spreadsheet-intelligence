import { useState, useRef, useEffect } from 'react'
import { runQuery } from '../hooks/useApi'
import AnswerCard from './AnswerCard'
import './QueryChat.css'

export default function QueryChat({ workbookId }) {
  const [results, setResults] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (results.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [results])

  async function submit(e) {
    e.preventDefault()
    const q = question.trim()
    if (!q || loading) return

    setLoading(true)
    setError(null)
    setQuestion('')

    try {
      const result = await runQuery(workbookId, q)
      setResults((prev) => [result, ...prev])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="query-chat">
      <form className="query-chat__form card" onSubmit={submit} role="search">
        <label htmlFor="query-input" className="sr-only">
          Ask a question about your workbook
        </label>
        <input
          ref={inputRef}
          id="query-input"
          className="query-chat__input"
          type="text"
          placeholder="Ask anything about your data…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
          autoComplete="off"
          autoFocus
        />
        <button
          type="submit"
          className="btn btn-primary query-chat__submit"
          disabled={!question.trim() || loading}
          aria-label="Run query"
        >
          {loading ? (
            <span className="query-chat__spinner" aria-hidden="true" />
          ) : (
            'Ask'
          )}
        </button>
      </form>

      {error && (
        <p className="error-message" role="alert">{error}</p>
      )}

      {loading && (
        <div className="query-chat__loading" role="status" aria-live="polite">
          <span className="query-chat__spinner" aria-hidden="true" />
          <span>Generating SQL and running query…</span>
        </div>
      )}

      {results.length === 0 && !loading && (
        <div className="query-chat__empty">
          <p>Ask a question to get started.</p>
          <ul className="query-chat__suggestions" aria-label="Example questions">
            <li>What is the total revenue?</li>
            <li>Show the top 5 rows by sales</li>
            <li>How many unique customers are there?</li>
          </ul>
        </div>
      )}

      <div
        className="query-chat__results"
        aria-live="polite"
        aria-label="Query results"
      >
        {results.map((r, i) => (
          <AnswerCard key={i} result={r} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
