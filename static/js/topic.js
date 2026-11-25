/* Реакции на теме форума: «Полезно» и «Согласен». */
(function () {
  'use strict';

  var root = document.getElementById('reactions');
  if (!root) return;

  root.querySelectorAll('button[data-kind]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var kind = btn.dataset.kind;
      var on = btn.dataset.on === '1';
      window.sitePost(root.dataset.url, 'kind=' + kind)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          btn.dataset.on = on ? '0' : '1';
          btn.setAttribute('aria-pressed', on ? 'false' : 'true');
          var count = root.querySelector('[data-count="' + kind + '"]');
          var icon = root.querySelector('[data-icon="' + kind + '"]');
          if (count) count.textContent = data.counts[kind];
          if (icon) icon.textContent = (kind === 'fire' ? '🔥' : '👍') + (on ? '' : '✓');
        })
        .catch(function () { /* сеть ошиблась — состояние не меняем */ });
    });
  });
})();
