/* Мост SSO: страница /boards/api/auth/sso отдаёт токен «Досок» блоком данных,
   этот скрипт кладёт его в localStorage и возвращает пользователя в приложение.
   Вынесен в файл, чтобы на странице не было inline-скрипта (строгий CSP). */
(function () {
  'use strict';
  var node = document.getElementById('sso-data');
  try {
    var data = JSON.parse(node ? node.textContent : '{}');
    if (!data.token) throw new Error('no token');
    localStorage.setItem('boardapp_token', data.token);
    localStorage.setItem('boardapp_user', JSON.stringify(data.user));
    location.replace(data.next || '/boards/');
  } catch (e) {
    document.body.textContent = 'Не удалось войти в «Доски». Вернитесь на сайт и попробуйте снова.';
  }
})();
