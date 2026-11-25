/* Тренажёр «Песочница»: корзина магазина с намеренно оставленными багами.
   Баги в логике — часть задания, ищите их в списке находок. */
(function () {
  var cart = {};
  var $ = function (id) { return document.getElementById(id); };
  function recalc() {
    var count = 0, total = 0;
    for (var id in cart) { count += cart[id].qty; total += cart[id].price * cart[id].qty; }
    // БАГ #4: счётчик штук округляет вниз (Math.floor вместо round для дробных qty)
    $('cart-count').textContent = Math.floor(count);
    $('cart-total').textContent = Math.round(total);
    var delivery = total >= 1000 ? 0 : 300;
    // БАГ #5: бесплатная доставка не работает (delivery всегда 300, несмотря на условие)
    delivery = 300;
    $('delivery-cost').textContent = delivery + ' ₽';
    var promo = $('promo').checked ? total * 0.1 : 0;
    // БАГ #6: промокод вычитается из суммы ДО доставки, но должен от суммы товаров; тут вычитаем 10% от total+delivery
    promo = $('promo').checked ? (total + delivery) * 0.1 : 0;
    var grand = total + delivery - promo;
    // БАГ #7: итог округляется вниз до сотен (теряются копейки)
    grand = Math.floor(grand / 100) * 100;
    $('grand-total').textContent = 'Итого: ' + grand + ' ₽';
    return { total: total, delivery: delivery, promo: promo, grand: grand };
  }
  document.querySelectorAll('[data-add]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var card = btn.closest('[data-id]');
      var id = card.dataset.id;
      var qty = parseFloat(card.querySelector('[data-qty]').value) || 0;
      // БАГ #1: можно добавить 0 или отрицательное количество
      if (qty <= 0) { alert('Товар добавлен (qty=' + qty + ')'); return; }
      // БАГ #2: количество не суммируется — каждый клик затирает предыдущее
      cart[id] = { qty: qty, price: parseInt(card.dataset.price) };
      // БАГ #3: цена бананов не учитывает скидку 20% от 3 кг
      recalc();
    });
  });
  $('checkout').addEventListener('click', function () {
    var r = recalc();
    var res = $('order-result');
    res.classList.remove('hidden');
    // БАГ #8: кнопка «Оформить» показывает «Заказ оформлен» даже при пустой корзине
    res.innerHTML = '✅ Заказ оформлен! Итого к оплате: ' + r.grand + ' ₽' +
      '<br><span style="color:var(--muted);font-size:12px">Номер заказа: LEM-' + Date.now() + '</span>';
  });
  $('promo').addEventListener('change', recalc);

  // сверка с эталоном
  $('check-btn').addEventListener('click', function () {
    var found = $('findings').value.toLowerCase();
    var bugs = [
      ['1. Валидация: можно добавить 0 или отрицательное количество', ['отрицательн', 'нулевое', 'меньше', '0']],
      ['2. Корзина: количество не суммируется при повторном добавлении', ['затирает', 'не суммирует', 'перезаписыва', 'заменяет']],
      ['3. Скидка 20% от 3 кг бананов не применяется', ['скидк', 'банан']],
      ['4. Счётчик товаров некорректен при дробном количестве', ['счётчик', 'счетчик', 'количество штук', 'округля']],
      ['5. Бесплатная доставка от 1000 ₽ не активируется', ['доставк']],
      ['6. Промокод считает 10% от суммы С доставкой (должен без)', ['промокод', 'промо']],
      ['7. Итоговая сумма округляется вниз до сотен', ['итог', 'округлен', 'сумма']],
      ['8. «Оформить» работает при пустой корзине', ['пуст', 'нулевая корзина', 'без товаров', '0 товаров']],
    ];
    var hit = 0, html = '<div class="space-y-2">';
    bugs.forEach(function (b) {
      var isFound = b[1].some(function (kw) { return found.includes(kw); });
      if (isFound) hit++;
      html += '<div class="flex items-start gap-2 text-sm"><span style="color:' +
        (isFound ? 'var(--accent-light)' : 'var(--muted)') + '">' +
        (isFound ? '✓' : '✗') + '</span><span class="' +
        (isFound ? 'text-white' : 'text-slate-400') + '">' + b[0] + '</span></div>';
    });
    html += '</div><p class="mt-3 text-sm text-slate-400">Найдено: <b class="text-indigo-300">' + hit +
      ' из 8</b> — ' + (hit >= 6 ? 'отличная находчивость! 🐒' : hit >= 4 ? 'хорошая база, смотрите что пропустили' :
      'загляните в подсказки в статье о чек-листах') + '</p>';
    var box = $('check-result');
    box.innerHTML = html;
    box.classList.remove('hidden');
  });
})();
