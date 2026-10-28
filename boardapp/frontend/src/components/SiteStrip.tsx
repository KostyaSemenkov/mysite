/**
 * Тонкая полоса сайта над канвасом редактора (как в Google Docs):
 * лого → на главную, «← Доски», название доски, тема, пользователь.
 */
import { getCurrentUser } from '../api'
import { ThemeToggle } from './SiteChrome'

const ICONS = '/static/img/icons.svg'

export default function SiteStrip({ title }: { title: string }) {
  const me = getCurrentUser()
  return (
    <div className="site-strip">
      <a href="/" className="site-strip-logo" title="На главную сайта">
        <svg className="icon"><use href={`${ICONS}#home`} /></svg>
        <span>Лемурзильня</span>
      </a>
      <span className="site-strip-sep" />
      <a href="/boards/#/" className="site-strip-back">← Доски</a>
      <span className="site-strip-title" title={title}>{title || 'Доска'}</span>
      <div className="site-strip-right">
        <ThemeToggle className="site-theme-toggle small" />
        {me && <span className="site-strip-user">{me.username}</span>}
        <a href="/" className="btn-warm ghost site-strip-site">На сайт</a>
      </div>
    </div>
  )
}
