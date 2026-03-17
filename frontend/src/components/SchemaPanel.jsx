import './SchemaPanel.css'

export default function SchemaPanel({ schema }) {
  if (!schema) return null

  return (
    <aside className="schema-panel card" aria-label="Workbook schema">
      <div className="schema-panel__header">
        <h2 className="schema-panel__title">Schema</h2>
        <span className="badge badge-blue">{schema.sheet_count} sheet{schema.sheet_count !== 1 ? 's' : ''}</span>
      </div>

      <div className="schema-panel__sheets">
        {schema.sheets.map((sheet) => (
          <details key={sheet.name} className="schema-sheet" open>
            <summary className="schema-sheet__summary">
              <span className="schema-sheet__name">{sheet.name}</span>
              <span className="badge badge-gray">{sheet.row_count} rows</span>
            </summary>
            <div className="schema-sheet__body">
              <p className="schema-sheet__table-name">
                <code>{sheet.table_name}</code>
              </p>
              <ul className="schema-sheet__columns" aria-label={`Columns in ${sheet.name}`}>
                {sheet.columns.map((col) => (
                  <li key={col.name} className="schema-col">
                    <span className="schema-col__name">{col.name}</span>
                    <span className="schema-col__dtype badge badge-gray">{col.dtype}</span>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        ))}
      </div>
    </aside>
  )
}
