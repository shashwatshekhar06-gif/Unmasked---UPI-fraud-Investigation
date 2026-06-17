import './NetworkGraphBg.css'

const NODES = [
  { x: 200, y: 90, r: 7, color: '#C4704B', delay: 0, isRoot: true },
  { x: 310, y: 55, r: 5, color: '#A63D2F', delay: 0.3 },
  { x: 130, y: 150, r: 5, color: '#D4A843', delay: 0.5 },
  { x: 320, y: 160, r: 4.5, color: '#A63D2F', delay: 0.7 },
  { x: 110, y: 55, r: 4, color: '#D4A843', delay: 0.4 },
  { x: 360, y: 110, r: 3.5, color: '#A63D2F', delay: 1.0 },
  { x: 80, y: 190, r: 3, color: '#8B7D6B', delay: 1.1 },
  { x: 170, y: 220, r: 4, color: '#A63D2F', delay: 1.3 },
  { x: 360, y: 230, r: 3, color: '#D4A843', delay: 1.4 },
  { x: 270, y: 240, r: 3.5, color: '#A63D2F', delay: 1.6 },
  { x: 60, y: 100, r: 2.5, color: '#8B7D6B', delay: 1.2 },
  { x: 370, y: 170, r: 2.5, color: '#8B7D6B', delay: 1.5 },
  { x: 210, y: 280, r: 2.5, color: '#8B7D6B', delay: 1.8 },
  { x: 320, y: 280, r: 2.5, color: '#D4A843', delay: 1.9 },
]

const EDGES = [
  [0, 1, '₹49,000'], [0, 2, '₹43,200'], [0, 3], [0, 4],
  [1, 5, '₹38,700'], [2, 6], [2, 7, '₹5,100'], [3, 8], [3, 9, '₹2,300'],
  [4, 10], [5, 11], [7, 12], [9, 13],
]

export default function NetworkGraphBg() {
  return (
    <svg className="net-bg" viewBox="0 0 420 310" xmlns="http://www.w3.org/2000/svg">
      {EDGES.map(([from, to, label], i) => (
        <g key={`e-${i}`}>
          <line
            x1={NODES[from].x} y1={NODES[from].y}
            x2={NODES[to].x} y2={NODES[to].y}
            className="net-edge"
            stroke={NODES[to].color}
            strokeWidth={to <= 4 ? 1.5 : 0.8}
            style={{ animationDelay: `${NODES[to].delay}s` }}
          />
          {label && (
            <text
              x={(NODES[from].x + NODES[to].x) / 2 + 8}
              y={(NODES[from].y + NODES[to].y) / 2 - 6}
              fill="#8B7D6B" fontSize="8" fontFamily="monospace"
            >{label}</text>
          )}
        </g>
      ))}

      {NODES[0].isRoot && (
        <>
          <circle cx={NODES[0].x} cy={NODES[0].y} r="6" fill="none" stroke="#C4704B" strokeWidth="0.5" className="net-ripple" />
          <circle cx={NODES[0].x} cy={NODES[0].y} r="6" fill="none" stroke="#C4704B" strokeWidth="0.5" className="net-ripple" style={{ animationDelay: '0.8s' }} />
        </>
      )}

      {NODES.map((n, i) => (
        <circle
          key={`n-${i}`}
          cx={n.x} cy={n.y} r={n.r}
          fill={n.color}
          className="net-node"
          style={{ animationDelay: `${n.delay}s` }}
        />
      ))}
    </svg>
  )
}
