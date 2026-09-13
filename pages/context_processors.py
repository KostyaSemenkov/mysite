from .models import Profile


def profile(request):
    """Профиль доступен во всех шаблонах (шапка, подвал)."""
    return {'profile': Profile.objects.first()}
