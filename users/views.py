from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import CustomUser
from .forms import CustomUserCreationForm
from django.db.models import Avg
from datetime import date, timedelta

from main.loyalty_utils import accrue_welcome_bonus
from main.models import (
    Appointment,
    BonusTransaction,
    Certificate,
    Client,
    Master,
    PaymentTransaction,
    Review,
)


class CustomLoginView(LoginView):
    template_name = 'main/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('main:index')

    def form_invalid(self, form):
        messages.error(self.request, 'Неверное имя пользователя или пароль')
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('main:index')


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'main/signup.html'
    success_url = reverse_lazy('main:index')

    def form_valid(self, form):
        # Сохраняем пользователя
        user = form.save()

        # Создаем профиль клиента
        client = Client.objects.create(user=user)
        welcome_amount = accrue_welcome_bonus(user, client)

        # Аутентифицируем и логиним пользователя
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)

        if user is not None:
            login(self.request, user)
            if welcome_amount:
                messages.success(
                    self.request,
                    f'Регистрация прошла успешно! Начислено {welcome_amount} приветственных бонусов.',
                )
            else:
                messages.success(self.request, 'Регистрация прошла успешно!')
            return redirect('main:index')
        else:
            messages.error(self.request, 'Ошибка при входе после регистрации')
            return redirect('main:index')


@login_required
def profile_view(request):
    """Личный кабинет пользователя"""
    user = request.user

    if user.role == 'MASTER':
        master, created = Master.objects.get_or_create(user=user)
        appointments = Appointment.objects.filter(master=master).order_by('-date', '-time')

        today = date.today()
        week_end = today + timedelta(days=6)
        week_appointments = (
            Appointment.objects.filter(master=master, date__gte=today, date__lte=week_end)
            .exclude(status="cancelled")
            .select_related("client__user", "service")
            .order_by("date", "time")
        )
        master_week_days = []
        for offset in range(7):
            day = today + timedelta(days=offset)
            master_week_days.append(
                {
                    "date": day,
                    "appointments": [a for a in week_appointments if a.date == day],
                }
            )

        master_reviews = Review.objects.filter(
            master=master, is_published=True
        ).select_related("client__user").order_by("-created_at")
        avg_rating = master_reviews.aggregate(avg=Avg("rating"))["avg"]
        context = {
            'user': user,
            'master': master,
            'appointments': appointments,
            'master_week_days': master_week_days,
            'is_master': True,
            'is_admin': False,
            'bonus_transactions': [],
            'certificates': [],
            'payments': PaymentTransaction.objects.filter(appointment__master=master),
            'master_reviews': master_reviews,
            'master_avg_rating': round(avg_rating, 1) if avg_rating else 0,
            'master_review_count': master_reviews.count(),
        }
    elif user.role == 'ADMIN' or user.is_superuser:
        client = Client.objects.filter(user=user).first()
        if client:
            appointments = Appointment.objects.filter(client=client).order_by('-date', '-time')
        else:
            appointments = Appointment.objects.none()
        context = {
            'user': user,
            'appointments': appointments,
            'is_admin': True,
            'is_master': False,
            'bonus_transactions': [],
            'certificates': Certificate.objects.all()[:20],
            'payments': PaymentTransaction.objects.all()[:50],
        }
    else:  # CLIENT
        client, created = Client.objects.get_or_create(user=user)
        # Получаем только записи этого клиента
        appointments = Appointment.objects.filter(client=client).order_by('-date', '-time')

        context = {
            'user': user,
            'client': client,
            'appointments': appointments,
            'is_master': False,
            'is_admin': False,
            'bonus_transactions': BonusTransaction.objects.filter(user=user),
            'certificates': Certificate.objects.filter(buyer_email=user.email) | Certificate.objects.filter(recipient_email=user.email),
            'payments': PaymentTransaction.objects.filter(appointment__client=client) | PaymentTransaction.objects.filter(certificate__buyer_email=user.email),
        }

    return render(request, 'main/profile.html', context)


@login_required
def profile_edit(request):
    """Редактирование профиля"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone = request.POST.get('phone', '')

        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']

        user.save()
        messages.success(request, 'Профиль успешно обновлен!')
        return redirect('users:profile')

    return render(request, 'main/profile_edit.html', {'user': request.user})

def logout_view(request):
    logout(request)
    return redirect('main:index')
