import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import cytoscape from 'cytoscape'
import { Client } from '@stomp/stompjs'
import SockJS from 'sockjs-client/dist/sockjs'
import './Investigate.css'

const API = 'http://localhost:8080/api/cases'

const AGENTS = [
  { key: 'transaction_tracer', label: 'Tracing money trail' },
  { key: 'identity_intelligence', label: 'Analyzing accounts' },
  { key: 'scam_classifier', label: 'Classifying scam pattern' },
  { key: 'network_expansion', label: 'Mapping fraud network' },
  { key: 'report_generator', label: 'Generating evidence report' },
]

function riskColor(s) {
  if (s >= 0.7) return '#A63D2F'
  if (s >= 0.4) return '#D4A843'
  if (s >= 0.15) return '#C4704B'
  return '#8B7D6B'
}

export default function Investigate() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ fraudVpa: '', transactionRef: '', amount: '', victimVpa: '' })
  const [phase, setPhase] = useState('form')
  const [agentStatus, setAgentStatus] = useState({})
  const [error, setError] = useState(null)
  const [caseId, setCaseId] = useState(null)
  const [graphReady, setGraphReady] = useState(false)
  const [nodeCount, setNodeCount] = useState(0)
  const [currentAction, setCurrentAction] = useState('')

  const graphRef = useRef(null)
  const cyRef = useRef(null)
  const pollRef = useRef(null)
  const stompRef = useRef(null)

  // Build graph depth by depth with smooth animation
  const buildGraphAnimated = useCallback((graphJson) => {
    if (!graphRef.current) return

    const data = typeof graphJson === 'string' ? JSON.parse(graphJson) : graphJson
    if (!data.nodes || !data.edges) return

    if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null }

    // Build all elements upfront
    const elements = []
    const seen = new Set()

    data.nodes.forEach(n => {
      elements.push({
        data: {
          id: n.id,
          label: n.id.length > 15 ? n.id.substring(0, 13) + '…' : n.id,
          fullLabel: n.id,
          risk: n.risk_score || 0,
          depth: n.depth || 0,
          bank: n.bank || '',
          flags: n.flags || [],
        },
        classes: 'hidden',
      })
    })

    data.edges.forEach((e, i) => {
      const key = `${e.source}-${e.target}-${e.amount}`
      if (!seen.has(key)) {
        seen.add(key)
        elements.push({
          data: {
            id: `e${i}`,
            source: e.source,
            target: e.target,
            label: `₹${Math.round(e.amount).toLocaleString()}`,
          },
          classes: 'hidden',
        })
      }
    })

    cyRef.current = cytoscape({
      container: graphRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': ele => riskColor(ele.data('risk') || 0),
            'label': 'data(label)',
            'font-size': '7px',
            'font-family': 'Inter, system-ui, sans-serif',
            'color': '#2D2419',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'width': ele => Math.max(14, 10 + (ele.data('risk') || 0) * 24),
            'height': ele => Math.max(14, 10 + (ele.data('risk') || 0) * 24),
            'border-width': 2,
            'border-color': ele => riskColor(ele.data('risk') || 0),
            'border-opacity': 0.25,
            'opacity': 1,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 0.8,
            'line-color': '#E8E0D4',
            'target-arrow-color': '#C4704B',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.5,
            'label': 'data(label)',
            'font-size': '5.5px',
            'font-family': 'monospace',
            'color': '#8B7D6B',
            'text-rotation': 'autorotate',
            'text-margin-y': -5,
            'opacity': 0.7,
          },
        },
        {
          selector: '.hidden',
          style: { 'opacity': 0 },
        },
        {
          selector: 'node:selected',
          style: { 'border-width': 3, 'border-color': '#C4704B', 'border-opacity': 1 },
        },
      ],
      layout: { name: 'preset' },
      minZoom: 0.25,
      maxZoom: 3,
    })

    // Run layout with ALL nodes first (they're invisible)
    cyRef.current.layout({
      name: 'cose',
      animate: false,
      nodeRepulsion: 7000,
      idealEdgeLength: 75,
      gravity: 0.35,
      padding: 35,
      fit: true,
    }).run()

    // Now reveal depth by depth
    const byDepth = {}
    data.nodes.forEach(n => {
      const d = n.depth || 0
      if (!byDepth[d]) byDepth[d] = []
      byDepth[d].push(n.id)
    })

    const depths = Object.keys(byDepth).map(Number).sort((a, b) => a - b)
    let totalRevealed = 0

    depths.forEach((depth, di) => {
      const layerDelay = di * 1000

      byDepth[depth].forEach((id, ni) => {
        setTimeout(() => {
          if (!cyRef.current) return
          const node = cyRef.current.getElementById(id)
          node.removeClass('hidden')
          node.animate({ style: { opacity: 1 } }, { duration: 350 })

          // Reveal connected edges
          node.connectedEdges().forEach(edge => {
            const src = edge.source()
            const tgt = edge.target()
            if (!src.hasClass('hidden') && !tgt.hasClass('hidden')) {
              edge.removeClass('hidden')
              edge.animate({ style: { opacity: 0.7 } }, { duration: 250 })
            }
          })

          totalRevealed++
          setNodeCount(totalRevealed)
        }, layerDelay + ni * 50)
      })
    })

    const totalTime = depths.length * 1000 + Math.max(...Object.values(byDepth).map(a => a.length)) * 50 + 500
    setTimeout(() => setGraphReady(true), totalTime)

  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.fraudVpa || !form.transactionRef || !form.amount) return

    setError(null)
    setPhase('running')
    setAgentStatus({})
    setGraphReady(false)
    setNodeCount(0)
    setCaseId(null)
    setCurrentAction('Submitting case...')

    if (cyRef.current) { cyRef.current.destroy(); cyRef.current = null }

    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          victimVpa: form.victimVpa || 'anonymous@upi',
          fraudVpa: form.fraudVpa,
          amount: parseFloat(form.amount),
          transactionRef: form.transactionRef,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Submission failed')
      }

      const data = await res.json()
      setCaseId(data.case_id)
      setCurrentAction('Investigation queued...')

      // Try WebSocket
      try { connectWs(data.case_id) } catch (e) { /* fallback to polling */ }

      // Poll as fallback
      startPolling(data.case_id)

    } catch (err) {
      setError(err.message)
      setPhase('form')
    }
  }

  const connectWs = (id) => {
    const client = new Client({
      webSocketFactory: () => new SockJS('http://localhost:8080/ws'),
      reconnectDelay: 3000,
      onConnect: () => {
        client.subscribe(`/topic/cases/${id}`, (msg) => {
          try {
            const event = JSON.parse(msg.body)
            if (event.agent && event.status) {
              setAgentStatus(prev => ({ ...prev, [event.agent]: event.status }))
              if (event.status === 'started') {
                const a = AGENTS.find(a => a.key === event.agent)
                if (a) setCurrentAction(a.label + '...')
              }
            }
          } catch (e) {}
        })
      },
    })
    client.activate()
    stompRef.current = client
  }

  const startPolling = (id) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/${id}`)
        const data = await res.json()
        if (data.status === 'complete') {
          clearInterval(pollRef.current)
          setPhase('done')
          setCurrentAction('')
          setAgentStatus(Object.fromEntries(AGENTS.map(a => [a.key, 'completed'])))
          fetchAndBuildGraph(id)
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current)
          setError('Investigation failed. Please try again.')
          setPhase('form')
        }
      } catch (e) {}
    }, 2500)
  }

  const fetchAndBuildGraph = async (id) => {
    try {
      const res = await fetch(`${API}/${id}/report`)
      if (res.ok) {
        const data = await res.json()
        if (data.graphJson) {
          buildGraphAnimated(data.graphJson)
        }
      }
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (stompRef.current) stompRef.current.deactivate()
      if (cyRef.current) cyRef.current.destroy()
    }
  }, [])

  const completedCount = Object.values(agentStatus).filter(s => s === 'completed').length

  return (
    <div className="inv">
      <div className="inv-inner">

        <aside className="inv-left">
          <div className="card">
            <h2 className="card-title">Report UPI fraud</h2>
            <p className="card-desc">Enter the fraudster's details. Investigation begins immediately.</p>

            <form onSubmit={handleSubmit}>
              <div className="field">
                <label>Fraud UPI ID</label>
                <input type="text" placeholder="scammer123@ybl" value={form.fraudVpa}
                  onChange={e => setForm(f => ({...f, fraudVpa: e.target.value}))}
                  disabled={phase === 'running'} required />
              </div>
              <div className="field-row">
                <div className="field">
                  <label>Transaction ref</label>
                  <input type="text" placeholder="UPI transaction ID" value={form.transactionRef}
                    onChange={e => setForm(f => ({...f, transactionRef: e.target.value}))}
                    disabled={phase === 'running'} required />
                </div>
                <div className="field">
                  <label>Amount (₹)</label>
                  <input type="number" placeholder="49000" value={form.amount}
                    onChange={e => setForm(f => ({...f, amount: e.target.value}))}
                    disabled={phase === 'running'} required />
                </div>
              </div>
              <div className="field">
                <label>Your UPI ID <span className="opt">(optional)</span></label>
                <input type="text" placeholder="yourname@okaxis" value={form.victimVpa}
                  onChange={e => setForm(f => ({...f, victimVpa: e.target.value}))}
                  disabled={phase === 'running'} />
              </div>
              <button type="submit" className="btn-submit" disabled={phase === 'running'}>
                {phase === 'running' ? 'Investigating...' : 'Start investigation'}
              </button>
            </form>

            {error && <div className="error-bar">{error}</div>}
          </div>

          {/* Progress */}
          {phase !== 'form' && (
            <div className="card">
              <div className="progress-head">
                <div className="progress-title-row">
                  <span className={`status-pip ${phase === 'done' ? 'done' : 'active'}`} />
                  <h3 className="progress-title">
                    {phase === 'done' ? 'Investigation complete' : 'Investigating'}
                  </h3>
                </div>
                {phase === 'running' && (
                  <span className="progress-pct">{Math.round((completedCount / AGENTS.length) * 100)}%</span>
                )}
              </div>

              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${phase === 'done' ? 100 : (completedCount / AGENTS.length) * 100}%` }} />
              </div>

              {currentAction && <p className="current-action">{currentAction}</p>}

              <div className="agent-list">
                {AGENTS.map(agent => {
                  const s = agentStatus[agent.key]
                  return (
                    <div key={agent.key} className={`agent-row ${s === 'completed' ? 'done' : s === 'started' ? 'active' : ''}`}>
                      <div className={`agent-dot ${s === 'completed' ? 'done' : s === 'started' ? 'active' : ''}`} />
                      <span className="agent-label">{agent.label}</span>
                      {s === 'started' && <span className="agent-status working">Working</span>}
                      {s === 'completed' && <span className="agent-status done-text">Done</span>}
                    </div>
                  )
                })}
              </div>

              {/* View report button */}
              {phase === 'done' && caseId && (
                <button className="btn-view-report" onClick={() => navigate(`/cases/${caseId}`)}>
                  View full investigation report →
                </button>
              )}
            </div>
          )}
        </aside>

        {/* Graph */}
        <main className="inv-right">
          <div className="card graph-card">
            <div className="graph-top">
              <h3 className="graph-title">Fraud network</h3>
              {nodeCount > 0 && (
                <div className="graph-pills">
                  <span className="pill">{nodeCount} nodes</span>
                  {phase === 'running' && <span className="pill pulse-pill">Building...</span>}
                </div>
              )}
            </div>

            {phase === 'form' && (
              <div className="graph-box empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D4CFC7" strokeWidth="1.2" strokeLinecap="round">
                  <circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><circle cx="12" cy="12" r="2"/>
                  <line x1="7.5" y1="7.5" x2="10.5" y2="10.5"/><line x1="13.5" y1="10.5" x2="16.5" y2="7.5"/><line x1="7.5" y1="16.5" x2="10.5" y2="13.5"/><line x1="13.5" y1="13.5" x2="16.5" y2="16.5"/>
                </svg>
                <p>Submit a fraud case to watch the<br/>network build in real time</p>
              </div>
            )}

            {phase === 'running' && nodeCount === 0 && (
              <div className="graph-box empty-state">
                <div className="spinner" />
                <p>Agents are tracing the network...</p>
              </div>
            )}

            <div className="graph-box" ref={graphRef}
              style={{ display: (nodeCount > 0 || phase === 'done') ? 'block' : 'none' }} />

            {nodeCount > 0 && (
              <div className="legend-row">
                <span className="legend"><span className="ldot" style={{background:'#A63D2F'}}/> High risk (&gt;70%)</span>
                <span className="legend"><span className="ldot" style={{background:'#D4A843'}}/> Medium (40-70%)</span>
                <span className="legend"><span className="ldot" style={{background:'#C4704B'}}/> Low (15-40%)</span>
                <span className="legend"><span className="ldot" style={{background:'#8B7D6B'}}/> Unknown</span>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
