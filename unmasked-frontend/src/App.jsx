import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Investigate from './pages/Investigate'
import CaseResults from './pages/CaseResults'
import Navbar from './components/Navbar'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/investigate" element={<Investigate />} />
        <Route path="/cases/:caseId" element={<CaseResults />} />
      </Routes>
    </BrowserRouter>
  )
}
