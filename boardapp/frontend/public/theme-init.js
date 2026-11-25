/* Цветовая тема «Досок» — та же, что на сайте: выбор хранится в localStorage('theme'),
 * а применяется через <meta name="color-scheme"> до первой отрисовки страницы.
 * Значение мета-тега читает tokens.css (color-scheme и light-dark()). */
(function () {
  'use strict';
  try {
    var saved = localStorage.getItem('theme');
    if (saved !== 'light' && saved !== 'dark') return;
    var meta = document.querySelector('meta[name="color-scheme"]');
    if (meta) meta.content = saved;
  } catch (e) {
    /* хранение запрещено — следуем системной теме */
  }
})();
