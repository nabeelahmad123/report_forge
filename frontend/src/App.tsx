import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { useReportFlow } from './hooks/useReportFlow'
import { RegWatchPage } from './pages/RegWatchPage'
import { ReportPage } from './pages/ReportPage'

function App() {
  // Owned here, not inside ReportPage, so it survives navigating to
  // RegWatch and back rather than resetting on route unmount/remount.
  const reportFlow = useReportFlow()

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<ReportPage {...reportFlow} />} />
          <Route path="regwatch" element={<RegWatchPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
