/* Общее поведение страниц сайта: мобильное меню, появление секций, счётчики,
   кнопка «наверх», cookie-баннер, защита от двойной отправки, диалоги и
   показ пароля. Всё — прогрессивное улучшение: без этого файла страница
   остаётся полной и читаемой. */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* POST с CSRF-токеном из <meta name="csrf-token">; таймаут — чтобы запрос не висел вечно */
  window.sitePost = function (url, body) {
    var meta = $('meta[name="csrf-token"]');
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': meta ? meta.content : '',
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: body || '',
      signal: window.AbortSignal && AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined
    });
  };

  /* ── мобильное меню ── */
  (function () {
    var button = $('[data-menu-toggle]');
    var nav = document.getElementById('mobile-nav');
    if (!button || !nav) return;
    function setOpen(open) {
      nav.classList.toggle('hidden', !open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    button.addEventListener('click', function () { setOpen(nav.classList.contains('hidden')); });
    nav.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { setOpen(false); button.focus(); }
    });
  })();

  /* ── появление секций при скролле (CSS прячет только при наличии .js) ── */
  (function () {
    var els = $$('.reveal');
    if (!els.length) return;
    if (!('IntersectionObserver' in window) || reduceMotion) {
      els.forEach(function (el) { el.classList.add('is-visible'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  })();

  /* ── счётчики: в HTML стоит итоговое число, анимируем только при появлении ── */
  (function () {
    var counters = $$('.counter[data-target]');
    if (!counters.length || reduceMotion || !('IntersectionObserver' in window)) return;
    counters.forEach(function (el) {
      var target = parseInt(el.dataset.target, 10) || 0;
      if (target <= 0) return;
      el.textContent = '0';
      var t0 = null, dur = 900;
      var io = new IntersectionObserver(function (entries) {
        if (!entries[0].isIntersecting) return;
        io.disconnect();
        requestAnimationFrame(function step(t) {
          if (t0 === null) t0 = t;
          var p = Math.min(1, (t - t0) / dur);
          el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
          if (p < 1) requestAnimationFrame(step);
        });
      }, { threshold: 0.4 });
      io.observe(el);
    });
  })();

  /* ── кнопка «наверх» ── */
  (function () {
    var btn = document.getElementById('scroll-top');
    if (!btn) return;
    var onScroll = function () { btn.classList.toggle('visible', window.scrollY > 500); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
      var main = document.getElementById('content');
      if (main) main.focus({ preventScroll: true });
    });
  })();

  /* ── cookie-баннер ── */
  (function () {
    var banner = document.getElementById('cookie-banner');
    if (!banner) return;
    var accepted = false;
    try { accepted = !!localStorage.getItem('cookies_ok'); } catch (e) { /* хранение запрещено */ }
    if (accepted) { banner.remove(); return; }
    banner.classList.add('visible');
    var button = $('[data-cookie-accept]', banner);
    if (!button) return;
    button.addEventListener('click', function () {
      try { localStorage.setItem('cookies_ok', '1'); } catch (e) { /* баннер покажется снова */ }
      banner.remove();
    });
  })();

  /* ── двойное нажатие «Отправить» не шлёт форму второй раз ── */
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (form.dataset.submitting) { event.preventDefault(); return; }
    form.dataset.submitting = '1';
  });
  // возврат из кэша страницы возвращает и признак «отправлена» — снимаем его
  window.addEventListener('pageshow', function () {
    $$('form[data-submitting]').forEach(function (form) { delete form.dataset.submitting; });
  });

  /* ── диалоги: [data-dialog-open="id"] открывает <dialog>, [data-dialog-close] закрывает ── */
  document.addEventListener('click', function (event) {
    var opener = event.target.closest('[data-dialog-open]');
    if (opener) {
      var dialog = document.getElementById(opener.dataset.dialogOpen);
      if (dialog && dialog.showModal) dialog.showModal();
      return;
    }
    var closer = event.target.closest('[data-dialog-close]');
    if (closer) {
      var open = closer.closest('dialog');
      if (open) open.close();
      return;
    }
    var more = event.target.closest('[data-testimonials-more]');
    if (more) {
      $$('.testimonial[hidden]', more.closest('section')).forEach(function (el) { el.hidden = false; });
      more.remove();
    }
  });

  /* ── показать/скрыть пароль: [data-password-toggle="id поля"] (можно несколько через пробел) ── */
  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-password-toggle]');
    if (!button) return;
    var inputs = button.dataset.passwordToggle.split(/\s+/)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    if (!inputs.length) return;
    var show = inputs[0].type === 'password';
    inputs.forEach(function (input) { input.type = show ? 'text' : 'password'; });
    button.setAttribute('aria-pressed', show ? 'true' : 'false');
    button.textContent = show ? 'Скрыть пароль' : 'Показать пароль';
  });

  /* ── после отправки с ошибками переводим фокус на первое неверное поле ── */
  (function () {
    var list = $('.errorlist:not(.nonfield)');
    if (!list) return;
    var row = list.closest('p, li, div');
    var field = row ? row.querySelector('input:not([type=hidden]), textarea, select') : null;
    if (!field) return;
    field.setAttribute('aria-invalid', 'true');
    if (list.id) {
      var described = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
      if (described.indexOf(list.id) === -1) described.push(list.id);
      field.setAttribute('aria-describedby', described.join(' '));
    }
    var active = document.activeElement;
    if (!active || !active.closest || !active.closest('form')) field.focus();
  })();
})();
