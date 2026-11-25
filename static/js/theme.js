/* Переключатель цветовой темы — общий для сайта и «Досок».
 *
 * Состояние лежит в localStorage('theme'):
 *   нет значения — следуем системной теме;
 *   'light' | 'dark' — явный выбор пользователя.
 *
 * Тему переключает <meta name="color-scheme"> в <head> (значения
 * 'light dark' | 'light' | 'dark'); CSS следует за ним через color-scheme
 * и light-dark(), поэтому скрипт не трогает классы и атрибуты <html>.
 * Кнопка — любой элемент с data-theme-toggle.
 */
(function () {
  'use strict';

  var KEY = 'theme';
  var meta = document.querySelector('meta[name="color-scheme"]');
  if (!meta) return;

  function stored() {
    try {
      return localStorage.getItem(KEY);
    } catch (e) {
      return null; // запрет на хранение данных — работаем без сохранения
    }
  }

  function systemIsDark() {
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  function apply(value) {
    meta.content = (value === 'light' || value === 'dark') ? value : 'light dark';
  }

  function toggle() {
    var saved = stored();
    var renderedDark = saved ? saved === 'dark' : systemIsDark();
    var target = renderedDark ? 'light' : 'dark';
    // Цель совпала с системной темой — пользователь отменяет свою настройку:
    // снимаем выбор, чтобы сайт снова следовал системе (день/ночь).
    var backToSystem = (target === 'dark') === systemIsDark();
    try {
      if (backToSystem) {
        localStorage.removeItem(KEY);
      } else {
        localStorage.setItem(KEY, target);
      }
    } catch (e) {
      // тема применится, но не сохранится
    }
    apply(backToSystem ? null : target);
  }

  document.addEventListener('click', function (event) {
    var target = event.target;
    var button = target && target.closest ? target.closest('[data-theme-toggle]') : null;
    if (!button) return;
    event.preventDefault();
    toggle();
  });

  // выбор, сделанный в другой вкладке
  window.addEventListener('storage', function (event) {
    if (event.key === KEY || event.key === null) apply(event.newValue);
  });
})();
