import { Link, useLocation } from 'react-router-dom'
import './Navbar.css'

export default function Navbar() {
  const location = useLocation()

  return (
    <nav className="navbar">
      <div className="nav-inner">
        <Link to="/" className="nav-logo">
          <div className="nav-logo-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FAF7F2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <polyline points="9 12 12 15 16 10"/>
            </svg>
          </div>
          <span className="nav-name">UNMASKED</span>
        </Link>

        <div className="nav-links">
          <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>Home</Link>
          <a href="#how-it-works" className="nav-link">How it works</a>
          <a href="#about" className="nav-link">About</a>
          <Link to="/investigate" className="nav-cta">Start investigation</Link>
        </div>
      </div>
    </nav>
  )
}
