import { Link } from 'react-router-dom'
import NetworkGraphBg from '../components/NetworkGraphBg'
import './Landing.css'

export default function Landing() {
  return (
    <div className="landing">
      <div className="landing-inner">

        {/* Hero */}
        <section className="hero">
          <NetworkGraphBg />
          <div className="hero-content">
            <div className="hero-pill">
              <span className="live-dot" />
              Autonomous fraud investigation
            </div>
            <h1 className="hero-h1">
              Trace every rupee.<br />
              Unmask every <span className="accent">mule.</span>
            </h1>
            <p className="hero-p">
              Submit a fraudster's UPI ID — our system maps the entire money
              trail and builds FIR-ready evidence in minutes, not months.
            </p>
            <Link to="/investigate" className="hero-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              Start investigation
            </Link>
            <div className="hero-trust">
              <span className="trust-item">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                End-to-end encrypted
              </span>
              <span className="trust-item">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                Results in 2-5 min
              </span>
              <span className="trust-item">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                FIR-ready report
              </span>
            </div>
          </div>
        </section>

        {/* Bento Stats */}
        <section className="bento">
          <div className="b-card b-big b-dark">
            <p className="b-label">Total cases investigated</p>
            <p className="b-num large">12,847</p>
            <p className="b-sub">Across 28 states and 6 banking networks</p>
            <div className="mini-bars">
              {[20,28,22,35,30,42,38,48,45,58].map((h, i) => (
                <div key={i} className="mini-bar" style={{
                  height: `${h}px`,
                  background: `rgba(196,112,75,${0.3 + i * 0.03})`,
                  animationDelay: `${0.2 + i * 0.1}s`
                }} />
              ))}
            </div>
          </div>

          <div className="b-card b-terra">
            <p className="b-label">Avg. investigation</p>
            <p className="b-num">3.2 min</p>
            <p className="b-sub">vs. 3-6 months manual</p>
            <div className="b-badge-row">
              <span className="b-badge-light">99.8% faster</span>
            </div>
          </div>

          <div className="b-card b-cream">
            <p className="b-label">Money traced</p>
            <p className="b-num dark">₹847 Cr</p>
            <p className="b-sub">Total fraud amount mapped through mule networks</p>
            <span className="b-trend success">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg>
              +23% this month
            </span>
          </div>

          <div className="b-card b-cream">
            <p className="b-label">Mule accounts flagged</p>
            <p className="b-num danger">34,219</p>
            <p className="b-sub">Risk scores compounding with every investigation</p>
            <div className="risk-bar-row">
              <div className="risk-segment" style={{ flex: 3, background: 'var(--danger)' }} />
              <div className="risk-segment" style={{ flex: 2, background: 'var(--warning)' }} />
              <div className="risk-segment" style={{ flex: 1, background: 'var(--border)' }} />
            </div>
            <div className="risk-labels">
              <span className="risk-label danger-text">High risk</span>
              <span className="risk-label warning-text">Medium</span>
              <span className="risk-label">Low</span>
            </div>
          </div>

          <div className="b-card b-big b-dark">
            <div className="b-card-header">
              <div>
                <p className="b-label"><span className="live-dot" /> Live network intelligence</p>
                <p className="b-num" style={{ fontSize: '22px' }}>93 nodes mapped</p>
                <p className="b-sub">Latest investigation — OLX marketplace scam syndicate</p>
              </div>
              <Link to="/investigate" className="b-view-btn">View full network</Link>
            </div>
            <svg className="net-mini" viewBox="0 0 420 80" xmlns="http://www.w3.org/2000/svg">
              {[[30,40,90,25],[30,40,80,60],[90,25,150,18],[90,25,160,50],[80,60,150,70],[150,18,220,12],[150,18,210,42],[160,50,230,60],[210,42,280,28],[210,42,270,65],[280,28,340,22],[280,28,330,50],[340,22,390,38]].map(([x1,y1,x2,y2], i) => (
                <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                  stroke={i < 3 ? '#C4704B' : i < 7 ? '#A63D2F' : '#8B7D6B'}
                  strokeWidth={i < 3 ? 1 : 0.7}
                  className="net-edge"
                  style={{ animationDelay: `${0.2 + i * 0.12}s` }}
                />
              ))}
              {[[30,40,5,'#C4704B'],[90,25,4,'#A63D2F'],[80,60,3.5,'#D4A843'],[150,18,4,'#A63D2F'],[160,50,3,'#D4A843'],[150,70,2.5,'#8B7D6B'],[220,12,2.5,'#8B7D6B'],[210,42,3.5,'#A63D2F'],[230,60,2.5,'#D4A843'],[280,28,3.5,'#A63D2F'],[270,65,2.5,'#8B7D6B'],[340,22,2.5,'#8B7D6B'],[330,50,3,'#D4A843'],[390,38,2.5,'#8B7D6B']].map(([cx,cy,r,fill], i) => (
                <circle key={i} cx={cx} cy={cy} r={r} fill={fill}
                  className="net-node"
                  style={{ animationDelay: `${0.1 + i * 0.1}s` }}
                />
              ))}
            </svg>
          </div>
        </section>

        {/* CTA */}
        <section className="cta-section">
          <h2 className="cta-h2">Lost money to UPI fraud?</h2>
          <p className="cta-p">
            Don't wait 6 months for a manual investigation. Submit the fraud UPI ID
            and get a complete evidence dossier in minutes.
          </p>
          <Link to="/investigate" className="cta-btn">
            Start your investigation — it's free
          </Link>
          <p className="cta-note">No signup needed. Your data stays private.</p>
        </section>

      </div>
    </div>
  )
}
