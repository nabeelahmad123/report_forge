import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { RegWatchPage } from './pages/RegWatchPage'
import { ReportPage } from './pages/ReportPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ReportPage />} />
          <Route path="regwatch" element={<RegWatchPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
