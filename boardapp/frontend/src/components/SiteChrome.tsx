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
  { href: '/ai/', label: 'ИИ-новости' },
  { href: '/forum/', label: 'Форум' },
  { href: '/useful/', label: 'Полезности' },
  { href: '/quiz/', label: 'Тренажёр' },
  { href: '/path/', label: 'Путь' },
]

/**
 * Переключатель темы общий с сайтом: тему меняет /static/js/theme.js,
 * слушающий кнопки [data-theme-toggle]. Иконка и подпись («в тёмную» / «в светлую»)
 * следуют за темой через tokens.css.
 */
export function ThemeToggle({ className = 'theme-toggle' }: { className?: string }) {
  return (
    <button type="button" className={className} data-theme-toggle>
      <svg className="icon ico-sun" aria-hidden="true"><use href={`${ICONS}#sun`} /></svg>
      <svg className="icon ico-moon" aria-hidden="true"><use href={`${ICONS}#moon`} /></svg>
      <span className="visually-hidden theme-to-dark">Включить тёмную тему</span>
      <span className="visually-hidden theme-to-light">Включить светлую тему</span>
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
        {/* Разделы: на планшетах и ноутбуках — второй строкой под названием (все видны),
            на широких экранах — в общей строке. Раскладка — в styles.css (.site-nav). */}
        <nav className="site-nav" aria-label="Основное меню">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="site-nav-link">{n.label}</a>
          ))}
        </nav>
        <div className="site-controls">
          <a href="/search/" aria-label="Поиск по сайту">
            <svg className="icon" aria-hidden="true"><use href={`${ICONS}#search`} /></svg>
          </a>
          {me ? (
            <a href="/profile/" className="site-nav-user">{me.username}</a>
          ) : (
            <a href="/accounts/login/?next=/boardapp/sso/" className="site-nav-user">Войти</a>
          )}
          <ThemeToggle className="theme-toggle small" />
        </div>
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
        <nav aria-label="Разделы сайта">
          <div className="site-footer-cap">Разделы</div>
          <div className="site-footer-links">
            <a href="/blog/">Блог</a>
            <a href="/projects/">Проекты</a>
            <a href="/talks/">Выступления</a>
            <a href="/forum/">Форум</a>
            <a href="/useful/">Полезности</a>
            <a href="/quiz/">Тренажёр</a>
          </div>
        </nav>
        <nav aria-label="Документы">
          <div className="site-footer-cap">Документы</div>
          <div className="site-footer-links">
            <a href="/offer/">Оферта</a>
            <a href="/privacy/">Конфиденциальность</a>
            <a href="/blog/rss/">RSS</a>
          </div>
        </nav>
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
