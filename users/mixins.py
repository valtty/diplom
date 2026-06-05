from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages


class AdminRequiredMixin(AccessMixin):
    """Миксин для проверки прав администратора"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser or request.user.role == 'ADMIN':
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'Доступ запрещен. Только для администраторов.')
        return redirect('main:index')


class MasterRequiredMixin(AccessMixin):
    """Миксин для проверки прав мастера"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.role == 'MASTER':
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'Доступ запрещен. Только для мастеров.')
        return redirect('main:index')