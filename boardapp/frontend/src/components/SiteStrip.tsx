/**
 * Тонкая полоса сайта над канвасом редактора (как в Google Docs):
 * лого → на главную, «← Доски», название доски, тема, пользователь.
 */
import { getCurrentUser } from '../api'
import { useDocumentTitle } from '../useDocumentTitle'
import { ThemeToggle } from './SiteChrome'

const ICONS = '/static/img/icons.svg'

export default function SiteStrip({ title }: { title: string }) {
  const me = getCurrentUser()
  const name = title || 'Доска'
  useDocumentTitle(`${name} — Доски`)
  return (
    <div className="site-strip">
      <a href="/" className="site-strip-logo" title="На главную сайта">
        <svg className="icon" aria-hidden="true"><use href={`${ICONS}#home`} /></svg>
        <span>Лемурзильня</span>
      </a>
      <span className="site-strip-sep" aria-hidden="true" />
      <a href="/boards/#/" className="site-strip-back">← Доски</a>
      {/* название доски — заголовок страницы; визуально оно и так перед глазами */}
      <h1 className="visually-hidden">{name}</h1>
      <span className="site-strip-title" title={name}>{name}</span>
      <div className="site-strip-right">
        <ThemeToggle className="theme-toggle small" />
        {me && <span className="site-strip-user">{me.username}</span>}
        <a href="/" className="btn-warm ghost site-strip-site">На сайт</a>
      </div>
    </div>
  )
}
