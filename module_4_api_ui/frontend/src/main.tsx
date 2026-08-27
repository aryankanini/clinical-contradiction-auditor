import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import './index.css'
import { AppShell } from './components/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { BatchesPage, BatchDetailPage } from './pages/BatchesPage'
import { FindingsQueuePage } from './pages/FindingsPage'
import { FindingDetailPage } from './pages/FindingDetailPage'
import { QueuesPage, RulePacksPage, CompliancePage, NotFoundPage } from './pages/MiscPages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="batches" element={<BatchesPage />} />
            <Route path="batches/:batchId" element={<BatchDetailPage />} />
            <Route path="findings" element={<FindingsQueuePage />} />
            <Route path="findings/:findingId" element={<FindingDetailPage />} />
            <Route path="queues" element={<QueuesPage />} />
            <Route path="rule-packs" element={<RulePacksPage />} />
            <Route path="compliance" element={<CompliancePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
