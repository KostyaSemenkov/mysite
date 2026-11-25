/* «Путь тестировщика»: отметки «пройдено» и полоса прогресса. */
(function () {
  'use strict';

  function refreshBar(percent) {
    var bar = document.querySelector('[data-progress-bar]');
    if (bar) bar.value = percent;
    var label = document.querySelector('[data-progress-label]');
    if (label) label.textContent = percent + '%';
  }

  document.querySelectorAll('.path-check[data-item]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      window.sitePost('/path/' + btn.dataset.item + '/toggle/')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.ok) return;
          btn.classList.toggle('done', data.done);
          btn.setAttribute('aria-pressed', data.done ? 'true' : 'false');
          refreshBar(data.percent);
        })
        .catch(function () { /* сеть ошиблась — отметка остаётся прежней */ });
    });
  });
})();
