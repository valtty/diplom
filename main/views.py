import hashlib
import hmac
import json
import random
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from users.mixins import AdminRequiredMixin

from .booking_slots import BOOKING_SLOT_MINUTES, align_start_datetime, intervals_overlap
from .loyalty_utils import accrue_completion_bonus
from .forms import (
    AppointmentForm,
    BlogCommentForm,
    BlogPostForm,
    CertificatePurchaseForm,
    ClientForm,
    MasterForm,
    MasterJobApplicationForm,
    PortfolioImageForm,
    PromotionForm,
    ReviewForm,
    ScheduleBulkForm,
    ScheduleForm,
    ServiceForm,
)
from .models import (
    Appointment,
    AuthorRequest,
    BlogComment,
    BlogPost,
    BonusTransaction,
    Category,
    Certificate,
    Client,
    LoyaltySettings,
    Master,
    MasterJobApplication,
    MasterSchedule,
    PaymentLog,
    PaymentTransaction,
    PortfolioImage,
    Promotion,
    Review,
    Schedule,
    Service,
    SiteSettings,
)
from .payment_validation import validate_card_payment
from .portfolio_static import home_portfolio_image_urls


# Публичные страницы
def index(request):
    promotions = Promotion.objects.filter(is_active=True).order_by("end_date")[:6]
    services = (
        Service.objects.filter(is_active=True, popular=True)
        .select_related("category")[:6]
    )
    masters = (
        Master.objects.filter(is_active=True)
        .prefetch_related("services")
        .annotate(
            avg_rating=Avg("reviews__rating", filter=Q(reviews__is_published=True)),
            reviews_count=Count("reviews", filter=Q(reviews__is_published=True)),
        )
        .order_by("-rating")[:3]
    )
    portfolio_url = reverse("main:portfolio")
    portfolio_home_cells = [
        {"src": src, "alt": f"Работа {i + 1}", "href": portfolio_url}
        for i, src in enumerate(home_portfolio_image_urls())
    ]
    site_settings = SiteSettings.objects.first()
    reviews = Review.objects.filter(is_published=True)[:5]
    blog_posts = (
    BlogPost.objects
    .filter(is_published=True, moderation_status="approved")
    .select_related("author")
    .order_by("-created_at")[:3]
)
    context = {
        "services": services,
        "masters": masters,
        "portfolio_home_cells": portfolio_home_cells,
        "promotions": promotions,
        "reviews": reviews,
        "site_settings": site_settings,
        "blog_posts": blog_posts,
        "career_form": MasterJobApplicationForm(),
    }
    return render(request, "main/index.html", context)


def master_job_apply(request):
    """Публичная отправка заявки мастера (форма на главной)."""
    if request.method != "POST":
        return redirect("main:index")
    form = MasterJobApplicationForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Заявка отправлена. Мы свяжемся с вами.")
    else:
        messages.error(request, "Проверьте корректность полей формы.")
    return redirect(reverse("main:index") + "#careers")


def portfolio(request):
    portfolio_images = PortfolioImage.objects.select_related("master").filter(is_approved=True).order_by("-uploaded_at")
    if request.GET.get("master"):
        portfolio_images = portfolio_images.filter(master_id=request.GET["master"])
    if request.GET.get("design_type"):
        portfolio_images = portfolio_images.filter(design_type=request.GET["design_type"])
    if request.GET.get("color_scheme"):
        portfolio_images = portfolio_images.filter(color_scheme=request.GET["color_scheme"])
    return render(
        request,
        "main/portfolio.html",
        {
            "portfolio_images": portfolio_images,
            "masters": Master.objects.filter(is_active=True),
            "design_choices": PortfolioImage.DESIGN_CHOICES,
            "color_choices": PortfolioImage.COLOR_CHOICES,
        },
    )


def contacts(request):
    return render(request, "main/contacts.html")


# Публичные списки
class ServiceListView(ListView):
    model = Service
    context_object_name = "services"
    template_name = "main/services.html"

    def get_queryset(self):
        return (
            Service.objects.filter(is_active=True)
            .select_related("category")
            .order_by("category__order", "category__name", "name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        services = list(self.get_queryset())
        categories = Category.objects.filter(is_active=True).order_by("order", "name")

        service_groups = []
        grouped_ids = set()
        for category in categories:
            cat_services = [s for s in services if s.category_id == category.pk]
            if cat_services:
                service_groups.append({"title": category.name, "services": cat_services})
                grouped_ids.update(s.pk for s in cat_services)

        uncategorized = [s for s in services if s.pk not in grouped_ids]
        if uncategorized:
            service_groups.append({"title": "Другие услуги", "services": uncategorized})

        context["service_groups"] = service_groups
        return context


class ServiceDetailView(DetailView):
    model = Service
    template_name = "main/service_detail.html"
    context_object_name = "service"
    def get_object(self, queryset=None):
        queryset = Service.objects.select_related("category")
        if self.kwargs.get("slug"):
            return get_object_or_404(queryset, slug=self.kwargs["slug"])
        return get_object_or_404(queryset, pk=self.kwargs["service_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.object
        context["masters"] = Master.objects.filter(is_active=True, services=service)
        context["related_services"] = Service.objects.filter(
            is_active=True, category=service.category
        ).exclude(id=service.id)[:4]
        return context


class MasterListView(ListView):
    model = Master
    context_object_name = "masters"
    template_name = "main/masters.html"

    def get_queryset(self):
        queryset = Master.objects.filter(is_active=True).annotate(
            avg_rating=Avg("reviews__rating", filter=Q(reviews__is_published=True)),
            reviews_count=Count("reviews", filter=Q(reviews__is_published=True)),
        )
        specialization = self.request.GET.get("specialization")
        if specialization:
            queryset = queryset.filter(
                Q(specialization=specialization) | Q(specialization="all")
            )
        if self.request.GET.get("q"):
            queryset = queryset.filter(user__first_name__icontains=self.request.GET["q"])
        return queryset.order_by("-rating", "user__first_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["specialization_choices"] = [
            (value, label)
            for value, label in Master.SPECIALIZATION_CHOICES
            if value != "all"
        ]
        context["active_specialization"] = self.request.GET.get("specialization", "")
        return context


class MasterDetailView(DetailView):
    model = Master
    template_name = "main/master_detail.html"
    context_object_name = "master"
    pk_url_kwarg = "master_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        master = self.get_object()
        portfolio = PortfolioImage.objects.filter(master=master)
        if not (self.request.user.is_authenticated and (self.request.user.is_superuser or self.request.user.role == "ADMIN" or self.request.user == master.user)):
            portfolio = portfolio.filter(is_approved=True)
        if self.request.GET.get("design_type"):
            portfolio = portfolio.filter(design_type=self.request.GET["design_type"])
        if self.request.GET.get("color_scheme"):
            portfolio = portfolio.filter(color_scheme=self.request.GET["color_scheme"])
        context["portfolio"] = portfolio
        context["services"] = master.services.filter(is_active=True)
        rev_qs = Review.objects.filter(master=master, is_published=True).select_related("client__user")
        context["reviews"] = rev_qs
        context["review_count"] = rev_qs.count()
        avg_rating = rev_qs.aggregate(Avg("rating"))["rating__avg"]
        context["avg_rating"] = round(avg_rating, 1) if avg_rating else 0
        context["design_choices"] = PortfolioImage.DESIGN_CHOICES
        context["color_choices"] = PortfolioImage.COLOR_CHOICES
        return context


# CRUD для услуг (только админ)
class ServiceCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = "main/service_form.html"
    success_url = reverse_lazy("main:services")

    def form_valid(self, form):
        if not form.instance.slug:
            form.instance.slug = slugify(form.instance.name)
        messages.success(self.request, f"Услуга '{form.instance.name}' успешно создана!")
        return super().form_valid(form)


class ServiceUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = "main/service_form.html"
    pk_url_kwarg = "service_id"
    success_url = reverse_lazy("main:services")

    def form_valid(self, form):
        messages.success(self.request, f"Услуга '{form.instance.name}' успешно обновлена!")
        return super().form_valid(form)


class ServiceDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Service
    template_name = "main/service_confirm_delete.html"
    pk_url_kwarg = "service_id"
    success_url = reverse_lazy("main:services")

    def form_valid(self, form):
        messages.success(self.request, "Услуга успешно удалена!")
        return super().form_valid(form)


# CRUD для мастеров (только админ)
class MasterCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Master
    form_class = MasterForm
    template_name = "main/master_form.html"
    context_object_name = "master"
    success_url = reverse_lazy("main:masters")

    def form_valid(self, form):
        instance = form.save(commit=False)
        if self.request.FILES.get("photo"):
            instance.photo = self.request.FILES["photo"]
        instance.save()
        form.save_m2m()
        messages.success(self.request, "Мастер успешно создан!")
        return redirect(self.get_success_url())


class MasterUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Master
    form_class = MasterForm
    template_name = "main/master_form.html"
    context_object_name = "master"
    pk_url_kwarg = "master_id"
    success_url = reverse_lazy("main:masters")

    def form_valid(self, form):
        instance = form.save(commit=False)
        if self.request.FILES.get("photo"):
            instance.photo = self.request.FILES["photo"]
        instance.save()
        form.save_m2m()
        messages.success(self.request, "Мастер успешно обновлён!")
        return redirect(self.get_success_url())


class MasterDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Master
    template_name = "main/master_confirm_delete.html"
    pk_url_kwarg = "master_id"
    success_url = reverse_lazy("main:masters")

    def form_valid(self, form):
        # Удаляем связанного пользователя
        master = self.get_object()
        user = master.user
        if user and not user.is_superuser:
            user.delete()
        messages.success(self.request, "Мастер успешно удален!")
        return super().form_valid(form)


# CRUD для клиентов (только админ)
class ClientListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Client
    context_object_name = "clients"
    template_name = "main/clients.html"

    def get_queryset(self):
        return Client.objects.all().order_by("user__first_name")


class ClientDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Client
    template_name = "main/client_detail.html"
    context_object_name = "client"
    pk_url_kwarg = "client_id"


class ClientCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "main/client_form.html"
    success_url = reverse_lazy("main:clients")

    def form_valid(self, form):
        from users.models import CustomUser
        import random
        import string

        # Генерируем случайное имя пользователя
        username = f"client_{''.join(random.choices(string.digits, k=6))}"
        password = 'client123'

        # Создаем пользователя
        user = CustomUser.objects.create_user(
            username=username,
            password=password,
            first_name=self.request.POST.get('first_name', ''),
            last_name=self.request.POST.get('last_name', ''),
            phone=self.request.POST.get('phone', ''),
            role='CLIENT'
        )
        form.instance.user = user

        messages.success(self.request, f"Клиент успешно создан!")
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "main/client_form.html"
    pk_url_kwarg = "client_id"
    success_url = reverse_lazy("main:clients")

    def form_valid(self, form):
        # Обновляем данные пользователя
        client = self.get_object()
        user = client.user
        user.first_name = self.request.POST.get('first_name', user.first_name)
        user.last_name = self.request.POST.get('last_name', user.last_name)
        user.phone = self.request.POST.get('phone', user.phone)
        user.email = self.request.POST.get('email', user.email)
        user.save()

        messages.success(self.request, f"Клиент успешно обновлен!")
        return super().form_valid(form)


class ClientDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Client
    template_name = "main/client_confirm_delete.html"
    pk_url_kwarg = "client_id"
    success_url = reverse_lazy("main:clients")

    def form_valid(self, form):
        client = self.get_object()
        user = client.user
        if user and not user.is_superuser:
            user.delete()
        messages.success(self.request, "Клиент успешно удален!")
        return super().form_valid(form)


# Записи на процедуру
@login_required
def appointments_redirect(request):
    """Список записей — в личном кабинете."""
    return redirect("users:profile")


class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = "main/appointment_detail.html"
    context_object_name = "appointment"
    pk_url_kwarg = "appointment_id"


@login_required
def appointment_create(request):
    if request.user.role not in ["CLIENT", "MASTER"]:
        messages.error(request, "Для записи нужен клиентский или мастер-профиль")
        return redirect("main:index")

    client, _ = Client.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.client = client
            appointment.status = "pending"
            schedule = Schedule.objects.filter(master=appointment.master, work_date=appointment.date).first()
            if not schedule:
                messages.error(request, "У мастера нет рабочего окна в выбранный день.")
                return render(request, "main/appointment_form.html", {"form": form, "client": client})
            if schedule.is_day_off:
                messages.error(request, "Выбранный день помечен как выходной.")
                return render(request, "main/appointment_form.html", {"form": form, "client": client})
            start_dt = datetime.combine(appointment.date, appointment.time)
            end_dt = start_dt + timedelta(minutes=BOOKING_SLOT_MINUTES)
            work_start = datetime.combine(appointment.date, schedule.start_time)
            work_end = datetime.combine(appointment.date, schedule.end_time)
            if start_dt < work_start or end_dt > work_end:
                messages.error(request, "Выбранное окно (2 часа) не помещается в график мастера.")
                return render(request, "main/appointment_form.html", {"form": form, "client": client})
            if schedule.break_start and schedule.break_end:
                break_start_dt = datetime.combine(appointment.date, schedule.break_start)
                break_end_dt = datetime.combine(appointment.date, schedule.break_end)
                if intervals_overlap(start_dt, end_dt, break_start_dt, break_end_dt):
                    messages.error(request, "Окно записи пересекается с перерывом мастера.")
                    return render(request, "main/appointment_form.html", {"form": form, "client": client})
            blocked_slots = schedule.blocked_slots or []
            if appointment.time.strftime("%H:%M") in blocked_slots:
                messages.error(request, "Этот слот заблокирован администратором.")
                return render(request, "main/appointment_form.html", {"form": form, "client": client})
            discount_multiplier = Decimal("1.00")
            if appointment.promo_code_applied:
                discount_multiplier -= Decimal(appointment.promo_code_applied.discount_percent) / Decimal("100")
            full_price = max(Decimal("0"), appointment.service.price * discount_multiplier)
            max_bonus = int(full_price * Decimal("0.5"))
            if appointment.bonus_used > max_bonus:
                appointment.bonus_used = max_bonus
            if appointment.bonus_used > client.bonus_balance:
                appointment.bonus_used = client.bonus_balance

            payment_option = form.cleaned_data.get("payment_option")
            certificate_number = form.cleaned_data.get("certificate_number", "").strip()
            certificate = None
            if payment_option == "certificate":
                certificate = Certificate.objects.filter(
                    certificate_number=certificate_number, is_activated=False
                ).first()
                if not certificate:
                    messages.error(request, "Сертификат не найден или уже использован.")
                    return render(request, "main/appointment_form.html", {"form": form, "client": client})
                if certificate.valid_until and certificate.valid_until < date.today():
                    messages.error(request, "Срок действия сертификата истек.")
                    return render(request, "main/appointment_form.html", {"form": form, "client": client})
                if certificate.service and certificate.service != appointment.service:
                    messages.error(request, "Сертификат не подходит для выбранной услуги.")
                    return render(request, "main/appointment_form.html", {"form": form, "client": client})
                appointment.certificate_applied = certificate
                appointment.payment_option = "certificate"
            full_price = max(Decimal("0"), full_price - Decimal(appointment.bonus_used))
            appointment.prepayment_amount = (full_price * Decimal("0.2")).quantize(Decimal("0.01"))

            # Правила оплаты и статус:
            # - card: предоплата 20%, подтверждение после оплаты
            # - bonus / certificate: запись сразу подтверждена
            appointment.is_prepaid = False
            if appointment.payment_option == "certificate":
                appointment.prepayment_amount = Decimal("0.00")
                appointment.status = "confirmed"
            elif appointment.payment_option == "bonus":
                appointment.status = "confirmed"

            appointment.save()
            if appointment.bonus_used > 0:
                client.bonus_balance -= appointment.bonus_used
                client.save(update_fields=["bonus_balance"])
                BonusTransaction.objects.create(
                    user=client.user,
                    amount=appointment.bonus_used,
                    type="spending",
                    source="appointment",
                    appointment=appointment,
                    description="Списание бонусов при записи",
                )
            if appointment.payment_option == "card":
                payment_id = f"test-prepay-{uuid.uuid4().hex[:12]}"
                transaction = PaymentTransaction.objects.create(
                    appointment=appointment,
                    amount=full_price,
                    prepaid_amount=appointment.prepayment_amount,
                    status="pending",
                    payment_id=payment_id,
                    payment_method="card",
                    is_test=True,
                )
                return redirect("main:payment_card", transaction_id=transaction.id)
            else:
                if appointment.certificate_applied:
                    messages.success(request, "Запись подтверждена. Оплата будет произведена сертификатом в салоне.")
                elif appointment.payment_option == "bonus":
                    messages.success(request, "Запись подтверждена с оплатой бонусами.")
                else:
                    messages.success(request, "Запись создана без онлайн-предоплаты.")
                return redirect("users:profile")
        else:
            # Показываем ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        initial = {}
        master_id = request.GET.get("master")
        service_id = request.GET.get("service")

        if master_id:
            try:
                initial["master"] = Master.objects.get(pk=master_id)
            except Master.DoesNotExist:
                pass
        if service_id:
            try:
                initial["service"] = Service.objects.get(pk=service_id)
            except Service.DoesNotExist:
                pass

        form = AppointmentForm(initial=initial)

    return render(request, "main/appointment_form.html", {"form": form, "client": client})


@login_required
def appointment_cancel(request, appointment_id):
    """Отмена записи"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.user.role == "CLIENT":
        client = get_object_or_404(Client, user=request.user)
        if appointment.client != client:
            messages.error(request, "У вас нет прав для отмены этой записи")
            return redirect("main:index")
    elif request.user.role != "ADMIN" and not request.user.is_superuser:
        messages.error(request, "У вас нет прав для отмены этой записи")
        return redirect("main:index")

    if appointment.date < date.today():
        messages.error(request, "Нельзя отменить прошедшую запись")
    elif appointment.status in ["cancelled", "completed"]:
        messages.error(request, f"Запись уже {appointment.get_status_display().lower()}")
    else:
        appointment.status = "cancelled"
        appointment.save()
        messages.success(request, "Запись отменена")

    return redirect("users:profile")


@login_required
def appointment_confirm(request, appointment_id):
    """Подтверждение записи мастером"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Проверяем, что пользователь - мастер и это его запись
    if request.user.role == "MASTER":
        master = get_object_or_404(Master, user=request.user)
        if appointment.master != master:
            messages.error(request, "Это не ваша запись")
            return redirect("users:profile")
    elif request.user.role != "ADMIN" and not request.user.is_superuser:
        messages.error(request, "У вас нет прав для подтверждения записи")
        return redirect("users:profile")

    if appointment.status != "pending":
        messages.error(request, "Можно подтвердить только ожидающие записи")
    else:
        appointment.status = "confirmed"
        appointment.save()
        messages.success(request, "Запись подтверждена")

    return redirect("users:profile")


@login_required
def appointment_complete(request, appointment_id):
    """Отметка о выполнении процедуры"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Проверяем, что пользователь - мастер и это его запись
    if request.user.role == "MASTER":
        master = get_object_or_404(Master, user=request.user)
        if appointment.master != master:
            messages.error(request, "Это не ваша запись")
            return redirect("users:profile")
    elif request.user.role != "ADMIN" and not request.user.is_superuser:
        messages.error(request, "У вас нет прав для отметки выполнения")
        return redirect("users:profile")

    if appointment.status != "confirmed":
        messages.error(request, "Можно отметить выполненной только подтверждённую запись")
    else:
        appointment.status = "completed"
        appointment.save()
        bonus_amount = accrue_completion_bonus(appointment)
        if bonus_amount:
            messages.success(
                request,
                f"Процедура отмечена как выполненная. Клиенту начислено {bonus_amount} бонусов.",
            )
        else:
            messages.success(request, "Процедура отмечена как выполненная")

    return redirect("users:profile")


# Отзывы
@login_required
def review_create(request, appointment_id):
    """Создание отзыва"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.user.role != "CLIENT":
        messages.error(request, "Только клиенты могут оставлять отзывы")
        return redirect("main:index")

    client = get_object_or_404(Client, user=request.user)

    if appointment.client != client:
        messages.error(request, "Это не ваша запись")
        return redirect("main:index")

    if appointment.status != "completed":
        messages.error(request, "Отзыв можно оставить только после выполненной процедуры")
        return redirect("main:index")

    if Review.objects.filter(appointment=appointment).exists():
        messages.error(request, "Отзыв к этой записи уже был оставлен")
        return redirect("main:master_detail", master_id=appointment.master_id)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.client = client
            review.master = appointment.master
            review.appointment = appointment
            review.save()
            client.bonus_balance += 50
            client.save(update_fields=["bonus_balance"])
            BonusTransaction.objects.create(
                user=client.user, amount=50, type="accrual", source="review", description="Бонус за отзыв"
            )
            messages.success(request, "Спасибо за отзыв! Начислено 50 бонусов.")
            return redirect("main:master_detail", master_id=appointment.master_id)
    else:
        form = ReviewForm()

    return render(request, "main/review_form.html", {"form": form, "appointment": appointment})


# Портфолио для мастеров
@login_required
def portfolio_add(request):
    """Добавление фото в портфолио"""
    if request.user.role != "MASTER":
        messages.error(request, "Только мастера могут добавлять фото")
        return redirect("main:index")

    master, _ = Master.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PortfolioImageForm(request.POST, request.FILES)
        if form.is_valid():
            portfolio = form.save(commit=False)
            portfolio.master = master
            portfolio.is_approved = request.user.role == "ADMIN"
            portfolio.save()
            if portfolio.is_approved:
                messages.success(request, "Фото добавлено и опубликовано.")
            else:
                messages.success(
                    request,
                    "Фото отправлено на модерацию. После одобрения администратором оно появится в портфолио.",
                )
            return redirect("main:master_detail", master_id=master.pk)
    else:
        form = PortfolioImageForm()

    return render(request, "main/portfolio_form.html", {"form": form})


@login_required
def portfolio_delete(request, image_id):
    """Удаление фото из портфолио"""
    image = get_object_or_404(PortfolioImage, id=image_id)

    is_owner = request.user.role == "MASTER" and image.master.user == request.user
    is_admin = request.user.role == "ADMIN" or request.user.is_superuser
    if not (is_owner or is_admin):
        messages.error(request, "У вас нет прав для удаления этого фото")
        return redirect("main:index")

    image.delete()
    messages.success(request, "Фото удалено")
    return redirect("main:master_detail", master_id=image.master.pk)


class PromotionListView(ListView):
    model = Promotion
    context_object_name = "promotions"
    template_name = "main/promotions.html"

    def get_queryset(self):
        return Promotion.objects.filter(is_active=True).order_by("end_date")


@login_required
def certificates(request):
    if request.method == "POST":
        form = CertificatePurchaseForm(request.POST)
        if form.is_valid():
            certificate = form.save()
            payment_id = f"test-cert-{uuid.uuid4().hex[:12]}"
            transaction = PaymentTransaction.objects.create(
                certificate=certificate,
                amount=certificate.amount,
                prepaid_amount=certificate.amount,
                status="pending",
                payment_id=payment_id,
                payment_method="card",
                is_test=True,
            )
            return redirect("main:payment_card", transaction_id=transaction.id)
    else:
        form = CertificatePurchaseForm()
    return render(request, "main/certificates.html", {"form": form})


@login_required
def activate_certificate(request):
    if request.user.role not in ["ADMIN", "MASTER"] and not request.user.is_superuser:
        return redirect("main:index")
    if request.method == "POST":
        cert_number = request.POST.get("certificate_number", "").strip()
        appointment_id = request.POST.get("appointment_id")
        certificate = Certificate.objects.filter(
            certificate_number=cert_number, is_activated=False
        ).first()
        if not certificate:
            messages.error(request, "Сертификат не найден или уже активирован.")
            return redirect("main:activate_certificate")
        certificate.is_activated = True
        certificate.activated_at = timezone.now()
        certificate.save(update_fields=["is_activated", "activated_at"])
        if appointment_id:
            appointment = Appointment.objects.filter(id=appointment_id).first()
            if appointment:
                appointment.certificate_applied = certificate
                appointment.status = "confirmed"
                appointment.save(update_fields=["certificate_applied", "status"])
        messages.success(request, "Сертификат активирован.")
        return redirect("users:profile")
    return render(request, "main/dashboard/certificate_activation.html")


@login_required
def schedule_dashboard(request):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    if request.method == "POST":
        bulk_form = ScheduleBulkForm(request.POST)
        if bulk_form.is_valid():
            master = bulk_form.cleaned_data["master"]
            date_from = bulk_form.cleaned_data["date_from"]
            date_to = bulk_form.cleaned_data["date_to"]
            start_time = bulk_form.cleaned_data["start_time"]
            end_time = bulk_form.cleaned_data["end_time"]
            break_start = bulk_form.cleaned_data.get("break_start")
            break_end = bulk_form.cleaned_data.get("break_end")
            is_day_off = bool(bulk_form.cleaned_data.get("is_day_off"))
            weekdays = set(int(x) for x in (bulk_form.cleaned_data.get("weekdays") or []))
            blocked_slots_raw = (bulk_form.cleaned_data.get("blocked_slots") or "").strip()
            blocked_slots = (
                [s.strip() for s in blocked_slots_raw.split(",") if s.strip()] if blocked_slots_raw else []
            )

            updated = 0
            current = date_from
            while current <= date_to:
                if weekdays and current.weekday() not in weekdays:
                    current += timedelta(days=1)
                    continue
                Schedule.objects.update_or_create(
                    master=master,
                    work_date=current,
                    defaults={
                        "start_time": start_time,
                        "end_time": end_time,
                        "break_start": break_start,
                        "break_end": break_end,
                        "is_day_off": is_day_off,
                        "blocked_slots": blocked_slots,
                    },
                )
                updated += 1
                current += timedelta(days=1)
            messages.success(request, f"Расписание сохранено для дат: {updated}.")
            return redirect("main:schedule_dashboard")
    else:
        bulk_form = ScheduleBulkForm()
    master_id = request.GET.get("master")
    schedules = Schedule.objects.all().select_related("master")
    if master_id:
        schedules = schedules.filter(master_id=master_id)
    return render(
        request,
        "main/dashboard/schedule_manage.html",
        {
            "bulk_form": bulk_form,
            "schedules": schedules,
            "masters": Master.objects.filter(is_active=True),
        },
    )


@login_required
def available_slots(request):
    master_id = request.GET.get("master")
    selected_date = request.GET.get("date")
    if not master_id or not selected_date:
        return JsonResponse({"slots": []})
    try:
        work_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"slots": []})
    schedule = Schedule.objects.filter(master_id=master_id, work_date=work_date, is_day_off=False).first()
    if not schedule:
        return JsonResponse({"slots": []})

    duration_minutes = BOOKING_SLOT_MINUTES

    busy_intervals = []
    for appt in Appointment.objects.filter(master_id=master_id, date=work_date).exclude(status="cancelled"):
        start_dt = datetime.combine(work_date, appt.time)
        end_dt = start_dt + timedelta(minutes=BOOKING_SLOT_MINUTES)
        busy_intervals.append((start_dt, end_dt))

    blocked = set(schedule.blocked_slots or [])
    slots = []
    day_end = datetime.combine(work_date, schedule.end_time)
    current = align_start_datetime(work_date, schedule.start_time)
    if current is None:
        return JsonResponse({"slots": []})
    while current + timedelta(minutes=duration_minutes) <= day_end:
        slot_str = current.strftime("%H:%M")
        candidate_end = current + timedelta(minutes=duration_minutes)

        in_break = False
        if schedule.break_start and schedule.break_end:
            break_start_dt = datetime.combine(work_date, schedule.break_start)
            break_end_dt = datetime.combine(work_date, schedule.break_end)
            in_break = intervals_overlap(current, candidate_end, break_start_dt, break_end_dt)

        is_past = current < datetime.now()
        is_blocked = slot_str in blocked
        overlaps_busy = any(
            intervals_overlap(current, candidate_end, bs, be) for bs, be in busy_intervals
        )

        if not (in_break or is_past or is_blocked or overlaps_busy):
            slots.append(slot_str)

        current += timedelta(minutes=duration_minutes)
    return JsonResponse({"slots": slots})


class BlogListView(ListView):
    model = BlogPost
    context_object_name = "posts"
    template_name = "main/blog.html"
    paginate_by = 6

    def get_queryset(self):
        queryset = BlogPost.objects.filter(is_published=True, moderation_status="approved")
        if self.request.GET.get("category"):
            queryset = queryset.filter(category=self.request.GET["category"])
        return queryset


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True, moderation_status="approved")
    post.views += 1
    post.save(update_fields=["views"])
    if request.method == "POST" and request.user.is_authenticated:
        comment_form = BlogCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            return redirect("main:blog_detail", slug=slug)
    else:
        comment_form = BlogCommentForm()
    return render(
        request,
        "main/blog_detail.html",
        {
            "post": post,
            "comment_form": comment_form,
            "similar_posts": BlogPost.objects.filter(category=post.category, is_published=True).exclude(id=post.id)[:3],
        },
    )


@login_required
def profile_page(request):
    return redirect("users:profile")


@login_required
def promotion_dashboard(request):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    if request.method == "POST":
        form = PromotionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Акция сохранена.")
            return redirect("main:promotion_dashboard")
    else:
        form = PromotionForm()
    return render(
        request,
        "main/dashboard/promotions_manage.html",
        {"form": form, "promotions": Promotion.objects.all().order_by("-start_date")},
    )


@login_required
def promotion_delete(request, promotion_id):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    get_object_or_404(Promotion, id=promotion_id).delete()
    messages.info(request, "Акция удалена.")
    return redirect("main:promotion_dashboard")


def _admin_only(request):
    return request.user.is_authenticated and (
        request.user.is_superuser or getattr(request.user, "role", None) == "ADMIN"
    )


@login_required
def admin_dashboard(request):
    """Центр управления сайтом (не Django admin)."""
    if not _admin_only(request):
        messages.error(request, "Доступ только для администратора.")
        return redirect("main:index")
    return render(
        request,
        "main/dashboard/admin_hub.html",
        {
            "pending_portfolio": PortfolioImage.objects.filter(is_approved=False).count(),
            "new_job_apps": MasterJobApplication.objects.filter(status="new").count(),
        },
    )


@login_required
def admin_job_applications(request):
    if not _admin_only(request):
        messages.error(request, "Доступ только для администратора.")
        return redirect("main:index")
    if request.method == "POST":
        app_id = request.POST.get("application_id")
        action = request.POST.get("action")
        app = get_object_or_404(MasterJobApplication, pk=app_id)
        new_st = request.POST.get("new_status")
        if action == "set_status" and new_st in dict(MasterJobApplication.STATUS_CHOICES):
            app.status = new_st
            app.admin_notes = (request.POST.get("admin_notes") or "").strip()
            app.save(update_fields=["status", "admin_notes", "updated_at"])
            messages.success(request, "Заявка обновлена.")
        return redirect("main:admin_job_applications")
    return render(
        request,
        "main/dashboard/job_applications.html",
        {
            "applications": MasterJobApplication.objects.all(),
            "job_status_choices": MasterJobApplication.STATUS_CHOICES,
        },
    )


@login_required
def admin_portfolio_moderation(request):
    if not _admin_only(request):
        messages.error(request, "Доступ только для администратора.")
        return redirect("main:index")
    if request.method == "POST":
        image_id = request.POST.get("image_id")
        action = request.POST.get("action")
        img = get_object_or_404(PortfolioImage, pk=image_id)
        if action == "approve":
            img.is_approved = True
            img.save(update_fields=["is_approved"])
            messages.success(request, "Работа одобрена.")
        elif action == "reject":
            img.is_approved = False
            img.show_on_homepage = False
            img.save(update_fields=["is_approved", "show_on_homepage"])
            messages.info(request, "Работа снята с публикации.")
        elif action == "toggle_home":
            if not img.is_approved:
                messages.error(request, "Сначала одобрите работу.")
            elif img.show_on_homepage:
                img.show_on_homepage = False
                img.save(update_fields=["show_on_homepage"])
                messages.success(request, "Убрано с главной.")
            else:
                count = PortfolioImage.objects.filter(
                    is_approved=True, show_on_homepage=True
                ).exclude(pk=img.pk).count()
                if count >= 7:
                    messages.error(request, "На главной уже 7 работ. Снимите отметку с другой.")
                else:
                    img.show_on_homepage = True
                    img.save(update_fields=["show_on_homepage"])
                    messages.success(request, "Добавлено на главную.")
        elif action == "delete":
            img.delete()
            messages.info(request, "Фото удалено.")
        return redirect("main:admin_portfolio_moderate")
    pending = PortfolioImage.objects.select_related("master").filter(is_approved=False).order_by(
        "-uploaded_at"
    )
    approved = (
        PortfolioImage.objects.select_related("master")
        .filter(is_approved=True)
        .order_by("-uploaded_at")
    )
    return render(
        request,
        "main/dashboard/portfolio_moderation.html",
        {"pending_images": pending, "approved_images": approved},
    )


@login_required
def blog_create(request):
    if request.user.role != "MASTER":
        messages.error(request, "Статьи могут добавлять только мастера.")
        return redirect("main:blog")
    master, _ = Master.objects.get_or_create(user=request.user)
    if not master.can_publish_blog:
        messages.info(request, "Нужна заявка на авторство.")
        return redirect("main:author_request")
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = master
            post.moderation_status = "pending"
            post.is_published = False
            post.save()
            messages.success(request, "Статья отправлена на модерацию.")
            return redirect("main:blog")
    else:
        form = BlogPostForm()
    return render(request, "main/dashboard/blog_post_form.html", {"form": form})


@login_required
def author_request(request):
    if request.user.role != "MASTER":
        return redirect("main:index")
    master, _ = Master.objects.get_or_create(user=request.user)
    if request.method == "POST":
        AuthorRequest.objects.create(master=master, message=request.POST.get("message", ""))
        messages.success(request, "Заявка отправлена администратору.")
        return redirect("users:profile")
    return render(request, "main/dashboard/author_request.html")


@login_required
def blog_moderation(request):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    return render(
        request,
        "main/dashboard/blog_moderation.html",
        {"posts": BlogPost.objects.exclude(moderation_status="approved")},
    )


@login_required
def blog_moderate_action(request, post_id, action):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    post = get_object_or_404(BlogPost, id=post_id)
    if action == "approve":
        post.moderation_status = "approved"
        post.is_published = True
    elif action == "reject":
        post.moderation_status = "rejected"
        post.is_published = False
    post.save()
    return redirect("main:blog_moderation")


@login_required
def blog_delete_comment(request, comment_id):
    comment = get_object_or_404(BlogComment, id=comment_id)
    if request.user.role == "ADMIN" or request.user.is_superuser:
        comment.delete()
        messages.success(request, "Комментарий удалён.")
    else:
        messages.error(request, "Удалять комментарии может только администратор.")
    return redirect("main:blog_detail", slug=comment.post.slug)


@login_required
def payment_card(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, status="pending")
    if request.method == "POST":
        ok, errs = validate_card_payment(
            request.POST.get("card_number", ""),
            request.POST.get("expiry", ""),
            request.POST.get("cvv", ""),
            request.POST.get("cardholder", ""),
        )
        if not ok:
            for e in errs:
                messages.error(request, e)
            return render(request, "main/payment_card.html", {"transaction": transaction})
        transaction.status = "paid"
        transaction.paid_at = timezone.now()
        transaction.save(update_fields=["status", "paid_at"])
        if transaction.appointment:
            transaction.appointment.status = "confirmed"
            transaction.appointment.save(update_fields=["status"])
        if transaction.certificate:
            certificate = transaction.certificate
            pdf_bytes = build_certificate_pdf(certificate)
            filename = f"certificate_{certificate.certificate_number}.pdf"
            certificate.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or None
            buyer_email = (certificate.buyer_email or "").strip()
            recipient_email = (certificate.recipient_email or "").strip()
            sent_to = []

            def send_certificate_email(to_addr, subject, body):
                if not to_addr:
                    return False
                msg = EmailMessage(subject, body, from_email=from_email, to=[to_addr])
                msg.attach(filename, pdf_bytes, "application/pdf")
                try:
                    msg.send(fail_silently=False)
                    sent_to.append(to_addr)
                    return True
                except Exception:
                    return False

            buyer_subject = "Спасибо за покупку сертификата Fleur Nails"
            buyer_body = (
                f"Здравствуйте, {certificate.buyer_name}!\n\n"
                f"Сертификат №{certificate.certificate_number} успешно оплачен.\n"
                f"Номинал: {certificate.amount} ₽.\n"
                f"Получатель: {certificate.recipient_name}.\n\n"
                f"PDF во вложении."
            )
            recipient_subject = "Вам подарили сертификат Fleur Nails"
            recipient_body = (
                f"Здравствуйте, {certificate.recipient_name}!\n\n"
                f"Вам подарили подарочный сертификат салона Fleur Nails №{certificate.certificate_number}.\n"
                f"Номинал: {certificate.amount} ₽.\n"
                f"Поздравление: {certificate.message or '—'}\n\n"
                f"PDF во вложении."
            )

            if (
                buyer_email
                and recipient_email
                and buyer_email.lower() == recipient_email.lower()
            ):
                combined = (
                    f"{buyer_body}\n\n"
                    f"{'—' * 20}\n\n"
                    f"{recipient_body}"
                )
                send_certificate_email(
                    buyer_email,
                    "Ваш подарочный сертификат Fleur Nails",
                    combined,
                )
            else:
                if buyer_email:
                    send_certificate_email(buyer_email, buyer_subject, buyer_body)
                if recipient_email:
                    send_certificate_email(recipient_email, recipient_subject, recipient_body)

            if sent_to:
                unique = sorted(set(sent_to), key=str.lower)
                messages.success(
                    request,
                    "Оплата прошла успешно. Сертификат отправлен на: " + ", ".join(unique),
                )
            elif buyer_email or recipient_email:
                messages.success(request, "Оплата прошла успешно.")
                messages.warning(
                    request,
                    "Не удалось отправить письмо на указанные адреса. "
                    "Проверьте настройки почты на сервере (SMTP).",
                )
            else:
                messages.success(request, "Оплата прошла успешно.")
                messages.warning(request, "Укажите email покупателя и получателя при оформлении сертификата.")
        else:
            messages.success(request, "Оплата прошла успешно.")
        return redirect("users:profile")
    return render(request, "main/payment_card.html", {"transaction": transaction})


@login_required
def author_requests_manage(request):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    return render(
        request,
        "main/dashboard/author_requests_manage.html",
        {"requests": AuthorRequest.objects.filter(status="pending")},
    )


@login_required
def author_request_action(request, request_id, action):
    if request.user.role != "ADMIN" and not request.user.is_superuser:
        return redirect("main:index")
    req = get_object_or_404(AuthorRequest, id=request_id)
    if action == "approve":
        req.status = "approved"
        req.master.can_publish_blog = True
        req.master.save(update_fields=["can_publish_blog"])
    elif action == "reject":
        req.status = "rejected"
    req.save(update_fields=["status"])
    return redirect("main:author_requests_manage")


@csrf_exempt
def yookassa_webhook(request):
    payload = {}
    try:
        import json

        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        pass
    signature = request.headers.get("X-Signature", "")
    secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "test_secret_key")
    expected_signature = hmac.new(secret_key.encode(), request.body, hashlib.sha1).hexdigest()
    valid = hmac.compare_digest(signature, expected_signature)
    PaymentLog.objects.create(event=payload.get("event", "unknown"), payload=payload, signature_valid=valid)
    return JsonResponse({"status": "ok"})


def build_certificate_pdf(certificate):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from io import BytesIO

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(60, 780, "Fleur Nails - Подарочный сертификат")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(60, 740, f"Номер: {certificate.certificate_number}")
        pdf.drawString(60, 720, f"Номинал: {certificate.amount} ₽")
        pdf.drawString(60, 700, f"Получатель: {certificate.recipient_name}")
        pdf.drawString(60, 680, f"Действителен до: {certificate.valid_until.strftime('%d.%m.%Y')}")
        pdf.drawString(60, 660, f"Поздравление: {certificate.message or 'Без текста'}")
        pdf.showPage()
        pdf.save()
        return buffer.getvalue()
    except Exception:
        return (
            f"Certificate {certificate.certificate_number}\n"
            f"Amount: {certificate.amount}\nRecipient: {certificate.recipient_name}\n"
        ).encode("utf-8")