import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import './index.css'
import { AppShell } from './components/AppShell'
import { RoleProvider } from './hooks/useRole'
import { BatchDetailPage, BatchesPage } from './pages/BatchesPage'
import { DashboardPage } from './pages/DashboardPage'
import { FindingDetailPage } from './pages/FindingDetailPage'
import { FindingsQueuePage } from './pages/FindingsPage'
import { CompliancePage, NotFoundPage, QueuesPage, RulePacksPage } from './pages/MiscPages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RoleProvider>
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
      </RoleProvider>
    </QueryClientProvider>
  </StrictMode>,
)
