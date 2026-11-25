import { lazy, Suspense } from 'react'
import { Navigate, Route, HashRouter as Router, Routes } from 'react-router-dom'
import { getToken } from './api'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import BoardsPage from './pages/BoardsPage'
import SiteChrome from './components/SiteChrome'

// Редактор с канвасом — самая тяжёлая часть приложения; грузим только тем,
// кто открыл доску, а не всем, кто заходит на страницу входа
const BoardEditorPage = lazy(() => import('./pages/BoardEditorPage'))

function RequireAuth({ children }: { children: React.ReactElement }) {
  // пускаем по токену; пользователя при необходимости подтянет ensureUser,
  // чтобы битая запись в localStorage не превращала страницу в пустую
  if (!getToken()) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<SiteChrome><LoginPage /></SiteChrome>} />
        <Route path="/register" element={<SiteChrome><RegisterPage /></SiteChrome>} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <SiteChrome><BoardsPage /></SiteChrome>
            </RequireAuth>
          }
        />
        <Route
          path="/board/:id"
          element={
            <RequireAuth>
              <Suspense fallback={<div className="page hint">Открываем доску…</div>}>
                <BoardEditorPage />
              </Suspense>
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}
