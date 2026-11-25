import { useEffect } from 'react'

/** Заголовок вкладки — по названию страницы (иначе он остаётся одним на все маршруты). */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    const previous = document.title
    document.title = title
    return () => { document.title = previous }
  }, [title])
}
