/**
 * Каркас сайта внутри SPA «Досок»: шапка с меню, футер, переключатель темы.
 * Иконки и токены берутся с основного сайта (тот же origin).
 */
import { getCurrentUser } from '../api'

const ICONS = '/static/img/icons.svg'

const NAV = [
  { href: '/', label: 'Главная' },
  { href: '/blog/', label: 'Блог' },
  { href: '/projects/', label: 'Проекты' },
  { href: '/talks/', label: 'Выступления' },
  { href: '/forum/', label: 'Форум' },
  { href: '/useful/', label: 'Полезности' },
  { href: '/quiz/', label: 'Тренажёр' },
  { href: '/about/', label: 'Обо мне' },
]

export function ThemeToggle({ className = 'site-theme-toggle' }: { className?: string }) {
  const toggle = () => {
    const h = document.documentElement
    h.dataset.theme = h.dataset.theme === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', h.dataset.theme)
  }
  return (
    <button className={className} title="Переключить тему" aria-label="Переключить тему" onClick={toggle}>
      <svg className="icon ico-sun"><use href={`${ICONS}#sun`} /></svg>
      <svg className="icon ico-moon"><use href={`${ICONS}#moon`} /></svg>
    </button>
  )
}

export function SiteHeader() {
  const me = getCurrentUser()
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <a href="/" className="site-logo">
          <span className="site-logo-title">Лемурзильня тестировщика</span>
          <span className="site-logo-tag">уголок в меру упитанного тестировщика</span>
        </a>
        <nav className="site-nav">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className={n.href === '/boards/' ? 'active' : ''}>{n.label}</a>
          ))}
          <a href="/search/" title="Поиск по сайту" aria-label="Поиск">
            <svg className="icon"><use href={`${ICONS}#search`} /></svg>
          </a>
          <ThemeToggle />
          {me ? (
            <a href="/profile/" className="site-nav-user">{me.username}</a>
          ) : (
            <a href="/accounts/login/?next=/boardapp/sso/" className="site-nav-user">Войти</a>
          )}
          <a href="/contacts/" className="btn-warm site-nav-cta">Связаться</a>
        </nav>
      </div>
    </header>
  )
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div>
          <div className="site-logo-title">Лемурзильня тестировщика</div>
          <p className="site-footer-about">уголок в меру упитанного тестировщика</p>
        </div>
        <div>
          <div className="site-footer-cap">Разделы</div>
          <div className="site-footer-links">
            <a href="/blog/">Блог</a>
            <a href="/projects/">Проекты</a>
            <a href="/talks/">Выступления</a>
            <a href="/forum/">Форум</a>
            <a href="/useful/">Полезности</a>
            <a href="/quiz/">Тренажёр</a>
          </div>
        </div>
        <div>
          <div className="site-footer-cap">Документы</div>
          <div className="site-footer-links">
            <a href="/offer/">Оферта</a>
            <a href="/privacy/">Конфиденциальность</a>
            <a href="/blog/rss/">RSS</a>
          </div>
        </div>
      </div>
      <div className="site-footer-bottom">© {new Date().getFullYear()} Лемурзильня тестировщика</div>
    </footer>
  )
}

export default function SiteChrome({ children }: { children: React.ReactElement }) {
  return (
    <div className="site-chrome">
      <SiteHeader />
      <main className="site-main">{children}</main>
      <SiteFooter />
    </div>
  )
}
