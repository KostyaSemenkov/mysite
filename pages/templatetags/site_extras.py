from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


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
