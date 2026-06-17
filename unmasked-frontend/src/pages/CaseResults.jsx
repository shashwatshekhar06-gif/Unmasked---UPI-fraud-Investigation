import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import cytoscape from 'cytoscape'
import ReactMarkdown from 'react-markdown'
import './CaseResults.css'

const API = 'http://localhost:8080/api/cases'
const AGENT_API = 'http://localhost:8000'

function riskColor(s) {
  if (s >= 0.7) return '#A63D2F'
  if (s >= 0.4) return '#D4A843'
  if (s >= 0.15) return '#C4704B'
  return '#8B7D6B'
}

function riskLabel(s) {
  if (s >= 0.7) return 'High risk'
  if (s >= 0.4) return 'Medium'
  if (s >= 0.15) return 'Low risk'
  return 'Unknown'
}

export default function CaseResults() {
  const { caseId } = useParams()
  const [report, setReport] = useState(null)
  const [caseData, setCaseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [graphStats, setGraphStats] = useState({ nodes: 0, edges: 0 })
  const [downloading, setDownloading] = useState(false)

  const graphRef = useRef(null)
  const cyRef = useRef(null)

  useEffect(() => {
    fetchData()
    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [caseId])

  const fetchData = async () => {
    try {
      const [caseRes, reportRes] = await Promise.all([
        fetch(`${API}/${caseId}`),
        fetch(`${API}/${caseId}/report`),
      ])
      if (caseRes.ok) setCaseData(await caseRes.json())
      if (reportRes.ok) {
        const r = await reportRes.json()
        setReport(r)
        setTimeout(() => buildGraph(r.graphJson), 200)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const downloadPdf = async () => {
    setDownloading(true)
    try {
      const res = await fetch(`${AGENT_API}/report/${caseId}/pdf`)
      if (!res.ok) throw new Error('PDF generation failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `UNMASKED_Report_${caseId.substring(0, 8).toUpperCase()}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      alert('Failed to download PDF. Please try again.')
      console.error(e)
    } finally {
      setDownloading(false)
    }
  }

  const buildGraph = useCallback((graphJson) => {
    if (!graphRef.current) return
    const data = typeof graphJson === 'string' ? JSON.parse(graphJson) : graphJson
    if (!data.nodes || !data.edges) return
    if (cyRef.current) cyRef.current.destroy()

    const elements = []
    const seenEdges = new Set()

    data.nodes.forEach(n => {
      elements.push({
        data: {
          id: n.id,
          label: n.id.length > 15 ? n.id.substring(0, 13) + '\u2026' : n.id,
          fullLabel: n.id,
          risk: n.risk_score || 0,
          depth: n.depth || 0,
          bank: n.bank || '',
          flags: n.flags || [],
        },
      })
    })

    data.edges.forEach((e, i) => {
      const key = `${e.source}-${e.target}-${e.amount}`
      if (!seenEdges.has(key)) {
        seenEdges.add(key)
        elements.push({
          data: { id: `e${i}`, source: e.source, target: e.target, label: `\u20B9${Math.round(e.amount).toLocaleString()}` },
        })
      }
    })

    setGraphStats({ nodes: data.nodes.length, edges: seenEdges.size })

    cyRef.current = cytoscape({
      container: graphRef.current,
      elements,
      style: [
        { selector: 'node', style: {
          'background-color': ele => riskColor(ele.data('risk')),
          'label': 'data(label)', 'font-size': '7px', 'font-family': 'Inter, system-ui, sans-serif',
          'color': '#2D2419', 'text-valign': 'bottom', 'text-margin-y': 5,
          'width': ele => Math.max(14, 10 + ele.data('risk') * 24),
          'height': ele => Math.max(14, 10 + ele.data('risk') * 24),
          'border-width': 2, 'border-color': ele => riskColor(ele.data('risk')), 'border-opacity': 0.25,
        }},
        { selector: 'edge', style: {
          'width': 0.8, 'line-color': '#E8E0D4', 'target-arrow-color': '#C4704B',
          'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'arrow-scale': 0.5,
          'label': 'data(label)', 'font-size': '5.5px', 'font-family': 'monospace',
          'color': '#8B7D6B', 'text-rotation': 'autorotate', 'text-margin-y': -5, 'opacity': 0.7,
        }},
        { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#C4704B', 'border-opacity': 1 }},
      ],
      layout: { name: 'cose', animate: true, animationDuration: 1200, nodeRepulsion: 7000, idealEdgeLength: 75, gravity: 0.35, padding: 35, fit: true },
      minZoom: 0.25, maxZoom: 3,
    })

    cyRef.current.on('tap', 'node', evt => setSelectedNode(evt.target.data()))
    cyRef.current.on('tap', evt => { if (evt.target === cyRef.current) setSelectedNode(null) })
  }, [])

  if (loading) return (
    <div className="results-loading"><div className="spinner" /><p>Loading investigation results...</p></div>
  )

  if (!report) return (
    <div className="results-empty">
      <div className="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D4CFC7" strokeWidth="1.5" strokeLinecap="round">
          <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>
      <h2 className="empty-title">Report not found</h2>
      <p className="empty-text">This case may still be processing, or the case ID is invalid.</p>
      <Link to="/investigate" className="empty-btn">Start new investigation</Link>
    </div>
  )

  const confidence = ((report.confidenceOverall || 0) * 100).toFixed(0)
  const isUnknownVpa = graphStats.nodes <= 1

  return (
    <div className="results">
      <div className="results-inner">

        <section className="summary-card">
          <div className="summary-top">
            <div>
              <p className="summary-label">Investigation complete</p>
              <h1 className="summary-pattern">{report.scamPattern || 'Unknown pattern'}</h1>
              <p className="summary-advisory">Matched: {report.matchedAdvisory || 'No advisory'}</p>
            </div>
            <div className="summary-actions">
              <button className="download-btn" onClick={downloadPdf} disabled={downloading}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                {downloading ? 'Generating...' : 'Download PDF report'}
              </button>
              <Link to="/investigate" className="new-case-btn">New investigation</Link>
            </div>
          </div>

          <div className="summary-stats">
            <div className="sstat">
              <span className="sstat-num" style={{ color: parseFloat(confidence) >= 50 ? '#7A9E7E' : '#C4704B' }}>{confidence}%</span>
              <span className="sstat-label">Overall confidence</span>
            </div>
            <div className="sstat-divider" />
            <div className="sstat"><span className="sstat-num">{report.networkSize}</span><span className="sstat-label">Network nodes</span></div>
            <div className="sstat-divider" />
            <div className="sstat"><span className="sstat-num">{graphStats.edges}</span><span className="sstat-label">Connections</span></div>
            <div className="sstat-divider" />
            <div className="sstat"><span className="sstat-num trail-status">{report.trailStatus?.replace(/_/g, ' ')}</span><span className="sstat-label">Trail status</span></div>
          </div>

          {isUnknownVpa && (
            <div className="trail-note info-note">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{flexShrink: 0, marginTop: 1}}>
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              <span>This VPA has not been seen in our investigation network before. We have registered it in our system. If it appears in future fraud cases, your case will be automatically linked and you will benefit from the expanded intelligence.</span>
            </div>
          )}

          {!isUnknownVpa && report.trailStatus?.includes('cold') && report.networkSize > 5 && (
            <div className="trail-note">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{flexShrink: 0, marginTop: 1}}>
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>The direct money trail for this transaction went cold, but network intelligence from prior investigations revealed <b>{report.networkSize} connected accounts</b> linked to this fraud VPA.</span>
            </div>
          )}
        </section>

        {!isUnknownVpa && (
          <div className="graph-detail-grid">
            <section className="graph-section">
              <div className="graph-top">
                <h2 className="section-title">Fraud network map</h2>
                <div className="graph-pills"><span className="pill">{graphStats.nodes} nodes</span><span className="pill">{graphStats.edges} edges</span></div>
              </div>
              <div className="graph-box" ref={graphRef} />
              <div className="legend-row">
                <span className="legend"><span className="ldot" style={{background:'#A63D2F'}}/> High risk</span>
                <span className="legend"><span className="ldot" style={{background:'#D4A843'}}/> Medium</span>
                <span className="legend"><span className="ldot" style={{background:'#C4704B'}}/> Low</span>
                <span className="legend"><span className="ldot" style={{background:'#8B7D6B'}}/> Unknown</span>
              </div>
            </section>

            {selectedNode && (
              <aside className="node-detail">
                <div className="nd-head"><h3 className="nd-title">Account detail</h3><button className="close-x" onClick={() => setSelectedNode(null)}>&#10005;</button></div>
                <div className="nd-vpa">{selectedNode.fullLabel}</div>
                <div className="nd-row"><span className="nd-label">Bank</span><span className="nd-value">{selectedNode.bank || 'Unknown'}</span></div>
                <div className="nd-row"><span className="nd-label">Risk score</span><span className="nd-value" style={{ color: riskColor(selectedNode.risk) }}>{(selectedNode.risk * 100).toFixed(0)}% — {riskLabel(selectedNode.risk)}</span></div>
                <div className="nd-row"><span className="nd-label">Depth</span><span className="nd-value">Hop {selectedNode.depth}</span></div>
                {selectedNode.flags?.length > 0 && (
                  <div className="nd-flags">{selectedNode.flags.map((f, i) => <span key={i} className="flag-chip">{f.replace(/_/g, ' ')}</span>)}</div>
                )}
              </aside>
            )}
          </div>
        )}

        {isUnknownVpa && (
          <section className="unknown-guidance">
            <h2 className="section-title">What you can do right now</h2>
            <div className="guidance-cards">
              <div className="guidance-card"><div className="gc-num">1</div><div><h3 className="gc-title">File a complaint on cybercrime.gov.in</h3><p className="gc-desc">Register your complaint on the national cyber crime portal. Download the PDF report above and attach it as evidence.</p></div></div>
              <div className="guidance-card"><div className="gc-num">2</div><div><h3 className="gc-title">Call 1930 — Cyber Crime Helpline</h3><p className="gc-desc">Report within the golden hour. Banks can freeze the recipient account within 2 hours of a helpline request.</p></div></div>
              <div className="guidance-card"><div className="gc-num">3</div><div><h3 className="gc-title">Contact your bank immediately</h3><p className="gc-desc">Report the unauthorized transaction. Under RBI guidelines, if reported within 3 days, you have zero liability.</p></div></div>
              <div className="guidance-card"><div className="gc-num">4</div><div><h3 className="gc-title">Preserve all evidence</h3><p className="gc-desc">Screenshot the UPI transaction, save call recordings, WhatsApp chats, and any communication with the fraudster.</p></div></div>
            </div>
          </section>
        )}

        <section className="report-section">
          <div className="report-top-bar">
            <h2 className="section-title">Evidence report</h2>
            <button className="download-btn-sm" onClick={downloadPdf} disabled={downloading}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              {downloading ? 'Generating...' : 'Download PDF'}
            </button>
          </div>
          <div className="report-body"><ReactMarkdown>{report.reportMarkdown}</ReactMarkdown></div>
        </section>

      </div>
    </div>
  )
}
