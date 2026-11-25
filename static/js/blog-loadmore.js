/* «Показать ещё» в блоге: догружаем страницу списка и берём номер следующей
   из заголовка X-Next-Page (в самом фрагменте его нет). */
(function () {
  'use strict';

  var list = document.getElementById('posts-list');
  var button = document.getElementById('load-more');
  if (!list || !button) return;

  var nextPage = button.dataset.next || '';
  var label = button.textContent;

  button.addEventListener('click', function () {
    if (!nextPage) { button.remove(); return; }
    button.disabled = true;
    button.textContent = 'Загружаем…';
    var opts = { headers: { 'X-Load-More': '1' }, credentials: 'same-origin' };
    if (window.AbortSignal && AbortSignal.timeout) opts.signal = AbortSignal.timeout(15000);
    fetch('?page=' + nextPage, opts)
      .then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        nextPage = resp.headers.get('X-Next-Page') || '';
        return resp.text();
      })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        doc.querySelectorAll('.post-card').forEach(function (el) { list.appendChild(el); });
        if (!nextPage) button.remove();
      })
      .catch(function () { /* сеть ошиблась — кнопка остаётся, можно повторить */ })
      .then(function () {
        if (!document.body.contains(button)) return;
        button.disabled = false;
        button.textContent = label;
      });
  });
})();
