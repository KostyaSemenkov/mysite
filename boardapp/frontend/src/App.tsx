import { Navigate, Route, HashRouter as Router, Routes } from 'react-router-dom'
import { getToken } from './api'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import BoardsPage from './pages/BoardsPage'
import BoardEditorPage from './pages/BoardEditorPage'
import SiteChrome from './components/SiteChrome'

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
              <BoardEditorPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}
