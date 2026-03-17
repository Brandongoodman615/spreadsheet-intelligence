import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import WorkbookDetail from './pages/WorkbookDetail'
import './App.css'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <a href="/" className="app-logo">
          <span className="logo-icon">&#9783;</span>
          Spreadsheet Intelligence
        </a>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/workbooks/:id" element={<WorkbookDetail />} />
        </Routes>
      </main>
    </div>
  )
}
