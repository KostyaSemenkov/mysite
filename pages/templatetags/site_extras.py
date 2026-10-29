from django import template
from django.contrib.contenttypes.models import ContentType

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
    """Подсветка подстроки <mark>."""
    text = str(text)
    q = str(q or '').strip()
    if not q:
        return text
    import re as _re
    pattern = _re.compile('(' + _re.escape(q) + ')', _re.IGNORECASE)
    from django.utils.safestring import mark_safe
    return mark_safe(pattern.sub(
        lambda m: '<mark>' + m.group(0) + '</mark>', text))


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
