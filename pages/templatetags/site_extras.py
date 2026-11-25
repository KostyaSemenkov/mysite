from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

import re as _re

register = template.Library()

# тёплые градиенты обложек-заглушек (по хэшу заголовка)
_COVER_GRADIENTS = [
    'linear-gradient(135deg, #7a4a2b 0%, #b9853c 100%)',
    'linear-gradient(135deg, #5a5a2f 0%, #96713f 100%)',
    'linear-gradient(135deg, #5d3a52 0%, #a3742f 100%)',
    'linear-gradient(135deg, #33200a 0%, #7a581f 100%)',
]


@register.filter
def cover_gradient(title):
    import hashlib
    h = int(hashlib.md5(str(title).encode('utf8')).hexdigest(), 16)
    return _COVER_GRADIENTS[h % len(_COVER_GRADIENTS)]


@register.filter
def split(value, separator=','):
    return [p for p in str(value).split(separator)]


@register.filter
def trim(value):
    return str(value).strip()


@register.simple_tag
def content_type_id(obj):
    return ContentType.objects.get_for_model(obj).pk


@register.simple_tag(takes_context=True)
def is_favorite(context, obj):
    user = context['request'].user
    if not user.is_authenticated:
        return False
    from pages.models import Favorite
    ct = ContentType.objects.get_for_model(obj)
    return Favorite.objects.filter(user=user, content_type=ct,
                                   object_id=str(obj.pk)).exists()


@register.filter
def highlight(text, q):
    """Подсветка подстроки <mark>; исходный текст всегда экранируется.

    text может быть пользовательским (заголовок темы форума), поэтому
    mark_safe допустим только поверх уже экранированных кусков.
    """
    text = str(text)
    q = str(q or '').strip()
    if not q:
        return text  # обычная строка — шаблон экранирует сам
    pattern = _re.compile(_re.escape(q), _re.IGNORECASE)
    out, pos = [], 0
    for m in pattern.finditer(text):
        out.append(escape(text[pos:m.start()]))
        out.append(format_html('<mark>{}</mark>', m.group(0)))
        pos = m.end()
    out.append(escape(text[pos:]))
    return mark_safe(''.join(out))


@register.filter
def opt(question, letter):
    return {'a': question.option_a, 'b': question.option_b,
            'c': question.option_c, 'd': question.option_d}.get(letter, '')


@register.filter
def lookup(d, key):
    try:
        return d.get(key) or []
    except AttributeError:
        return []


@register.filter
def score_color(score):
    score = int(score or 0)
    if score >= 80:
        return 'text-emerald-400'
    if score >= 50:
        return 'text-indigo-300'
    return 'text-warn'


# youtube-nocookie: режим расширенной конфиденциальности (без трекинга до клика)
_EMBED_YT = 'https://www.youtube-nocookie.com/embed/'


@register.filter
def video_embed(url):
    """YouTube/VK ссылка → embed URL для iframe."""
    url = str(url or '')
    m = _re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{6,})', url)
    if m:
        return _EMBED_YT + m.group(1)
    m = _re.search(r'vk\.com/video(-?\d+_\d+)', url)
    if m:
        return 'https://vk.com/video_ext.php?oid=' + m.group(1).replace('_', '&id=') + '&hd=2'
    return url


@register.filter
def stars(rating):
    n = max(0, min(5, int(rating or 0)))
    return '★' * n + '☆' * (5 - n)


@register.simple_tag
def img_dims(image_field):
    """width/height у картинки: браузер резервирует место до её загрузки.

    Если файл недоступен, берём пропорцию обложки по умолчанию (16:9).
    """
    try:
        width, height = image_field.width, image_field.height
    except Exception:
        width, height = 1200, 675
    return format_html('width="{}" height="{}"', width, height)
