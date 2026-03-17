import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { listWorkbooks } from '../hooks/useApi'
import UploadZone from '../components/UploadZone'
import './Home.css'

export default function Home() {
  const navigate = useNavigate()
  const [workbooks, setWorkbooks] = useState([])
  const [loadingList, setLoadingList] = useState(true)

  useEffect(() => {
    listWorkbooks()
      .then(setWorkbooks)
      .catch(() => {})
      .finally(() => setLoadingList(false))
  }, [])

  function handleUploaded(result) {
    navigate(`/workbooks/${result.id}`)
  }

  return (
    <div className="home">
      <div className="home__hero">
        <h1 className="home__title">Ask questions about your data</h1>
        <p className="home__subtitle">
          Upload an Excel workbook and query it in plain English.
          Exact answers, powered by SQL — not guesswork.
        </p>
      </div>

      <UploadZone onUploaded={handleUploaded} />

      <section className="home__history" aria-labelledby="history-heading">
        <h2 id="history-heading" className="home__section-title">Recent workbooks</h2>

        {loadingList ? (
          <p className="home__loading">Loading…</p>
        ) : workbooks.length === 0 ? (
          <p className="home__empty">No workbooks uploaded yet.</p>
        ) : (
          <ul className="workbook-list" aria-label="Recent workbooks">
            {workbooks.map((w) => (
              <li key={w.id}>
                <Link to={`/workbooks/${w.id}`} className="workbook-list__item card">
                  <div className="workbook-list__icon" aria-hidden="true">📊</div>
                  <div className="workbook-list__info">
                    <span className="workbook-list__name">{w.original_name}</span>
                    <span className="workbook-list__meta">
                      {w.sheet_count} sheet{w.sheet_count !== 1 ? 's' : ''}
                      {w.has_formulas && <span className="badge badge-blue" style={{ marginLeft: 6 }}>formulas</span>}
                    </span>
                  </div>
                  <span className="workbook-list__date">
                    {new Date(w.created_at).toLocaleDateString()}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
