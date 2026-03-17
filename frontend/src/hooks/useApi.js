const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function apiFetch(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function uploadWorkbook(file) {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch('/workbooks/', { method: 'POST', body: formData })
}

export async function listWorkbooks() {
  return apiFetch('/workbooks/')
}

export async function getWorkbook(id) {
  return apiFetch(`/workbooks/${id}`)
}

export async function runQuery(workbookId, question) {
  return apiFetch('/queries/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workbook_id: workbookId, question }),
  })
}

export async function getQueryHistory(workbookId) {
  return apiFetch(`/queries/${workbookId}/history`)
}
