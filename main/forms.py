from datetime import date, datetime, timedelta

from django import forms

from users.models import CustomUser

from .booking_slots import BOOKING_SLOT_MINUTES, intervals_overlap, is_half_hour_time
from .models import (
    Appointment,
    BlogComment,
    BlogPost,
    Category,
    Certificate,
    Client,
    Master,
    MasterJobApplication,
    PortfolioImage,
    Promotion,
    Review,
    Schedule,
    Service,
)

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = [
            "name",
            "slug",
            "category",
            "description",
            "price",
            "duration_minutes",
            "image",
            "popular",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "duration_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "popular": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "description", "icon", "order", "is_active"]


class MasterForm(forms.ModelForm):
    class Meta:
        model = Master
        fields = [
            "user",
            "bio",
            "experience",
            "work_experience",
            "specialization",
            "certificates",
            "social_instagram",
            "photo",
            "services",
            "is_active",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "certificates": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "experience": forms.NumberInput(attrs={"class": "form-control"}),
            "work_experience": forms.TextInput(attrs={"class": "form-control"}),
            "specialization": forms.Select(attrs={"class": "form-control"}),
            "social_instagram": forms.URLInput(attrs={"class": "form-control"}),
            "photo": forms.FileInput(attrs={"class": "form-control"}),
            "services": forms.SelectMultiple(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = False
        if self.instance.pk:
            if "user" in self.fields:
                del self.fields["user"]
        else:
            self.fields["user"].required = True
            self.fields["user"].label = "Пользователь (мастер)"
            taken_ids = Master.objects.values_list("user_id", flat=True)
            self.fields["user"].queryset = (
                CustomUser.objects.filter(role=CustomUser.Role.MASTER)
                .exclude(pk__in=taken_ids)
                .order_by("username")
            )
            self.fields["user"].help_text = (
                "Выберите пользователя с ролью «Мастер», у которого ещё нет карточки мастера. "
                "Создайте такого пользователя в Django admin (Пользователи), если список пуст."
            )


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["birth_date", "bonus_balance", "referred_by"]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "bonus_balance": forms.NumberInput(attrs={"class": "form-control"}),
            "referred_by": forms.Select(attrs={"class": "form-control"}),
        }


class AppointmentForm(forms.ModelForm):
    certificate_number = forms.CharField(
        required=False,
        label="Номер сертификата",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "FN-2026XXXX-XXXXXX"}),
    )

    class Meta:
        model = Appointment
        fields = [
            "master",
            "service",
            "date",
            "time",
            "design_preference",
            "promo_code_applied",
            "bonus_used",
            "payment_option",
            "comment",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "time": forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 7200}),
            "design_preference": forms.Textarea(
                attrs={"rows": 2, "class": "form-control", "placeholder": "Ссылка на желаемый дизайн"}
            ),
            "promo_code_applied": forms.Select(attrs={"class": "form-control"}),
            "bonus_used": forms.NumberInput(attrs={"class": "form-control"}),
            "payment_option": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(
                attrs={"rows": 3, "class": "form-control", "placeholder": "Ваши пожелания..."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["master"].queryset = Master.objects.filter(is_active=True)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["promo_code_applied"].queryset = Promotion.objects.filter(is_active=True)
        self.fields["master"].widget.attrs.update({"class": "form-control"})
        self.fields["service"].widget.attrs.update({"class": "form-control"})
        self.fields["master"].empty_label = "--------- Выберите мастера ---------"
        self.fields["service"].empty_label = "--------- Выберите услугу ---------"
        self.fields["promo_code_applied"].required = False
        self.fields["date"].widget.attrs["min"] = date.today().isoformat()

    def clean(self):
        cleaned_data = super().clean()
        selected_date = cleaned_data.get("date")
        selected_time = cleaned_data.get("time")
        master = cleaned_data.get("master")
        if selected_date and selected_date < date.today():
            self.add_error("date", "Нельзя выбрать прошедшую дату.")
        if selected_date and selected_time:
            appointment_dt = datetime.combine(selected_date, selected_time)
            if appointment_dt < datetime.now():
                self.add_error("time", "Нельзя выбрать прошедшее время.")
        if master and selected_date and selected_time:
            if not is_half_hour_time(selected_time):
                self.add_error("time", "Запись доступна только в :00 или :30.")
            start = datetime.combine(selected_date, selected_time)
            end = start + timedelta(minutes=BOOKING_SLOT_MINUTES)
            for appt in Appointment.objects.filter(master=master, date=selected_date).exclude(status="cancelled"):
                a0 = datetime.combine(selected_date, appt.time)
                a1 = a0 + timedelta(minutes=BOOKING_SLOT_MINUTES)
                if intervals_overlap(start, end, a0, a1):
                    self.add_error("time", "Это окно пересекается с другой записью. Выберите другое время.")
                    break

        payment_option = cleaned_data.get("payment_option")
        certificate_number = (cleaned_data.get("certificate_number") or "").strip()

        # Поле сертификата используется ТОЛЬКО при выборе оплаты сертификатом
        if payment_option != "certificate":
            cleaned_data["certificate_number"] = ""
        else:
            if not certificate_number:
                self.add_error("certificate_number", "Введите номер сертификата.")
        return cleaned_data


class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = [
            "title",
            "slug",
            "description",
            "discount_percent",
            "services",
            "start_date",
            "end_date",
            "is_active",
            "promo_code",
            "image",
            "conditions",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "discount_percent": forms.NumberInput(attrs={"class": "form-control"}),
            "services": forms.SelectMultiple(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "promo_code": forms.TextInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "conditions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class CertificatePurchaseForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = [
            "amount",
            "buyer_name",
            "buyer_email",
            "recipient_name",
            "recipient_email",
            "message",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Например, 3000"}),
            "buyer_name": forms.TextInput(attrs={"class": "form-control"}),
            "buyer_email": forms.EmailInput(attrs={"class": "form-control"}),
            "recipient_name": forms.TextInput(attrs={"class": "form-control"}),
            "recipient_email": forms.EmailInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "text"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5, "class": "form-control"}),
            "text": forms.Textarea(
                attrs={"rows": 4, "class": "form-control", "placeholder": "Напишите ваш отзыв..."}
            ),
        }

class PortfolioImageForm(forms.ModelForm):
    class Meta:
        model = PortfolioImage
        fields = ["image", "description", "design_type", "color_scheme", "video_url"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control", "placeholder": "Описание фото"}),
            "design_type": forms.Select(attrs={"class": "form-control"}),
            "color_scheme": forms.Select(attrs={"class": "form-control"}),
            "video_url": forms.URLInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
        }


class BlogCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"class": "form-control", "rows": 3})}


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "slug", "excerpt", "content", "image", "category"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "excerpt": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
        }


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = [
            "master",
            "work_date",
            "start_time",
            "end_time",
            "break_start",
            "break_end",
            "is_day_off",
        ]
        widgets = {
            "master": forms.Select(attrs={"class": "form-control"}),
            "work_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "start_time": forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
            "break_start": forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
            "break_end": forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
            "is_day_off": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        labels = {
            "start_time": "Начало работы",
            "end_time": "Конец работы",
            "break_start": "Начало перерыва",
            "break_end": "Конец перерыва",
        }
        for key, label in labels.items():
            t = cleaned_data.get(key)
            if t and not is_half_hour_time(t):
                self.add_error(key, f"{label}: только :00 или :30.")
        return cleaned_data


class ScheduleBulkForm(forms.Form):
    master = forms.ModelChoiceField(
        queryset=Master.objects.filter(is_active=True),
        label="Мастер",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    date_from = forms.DateField(
        label="С даты",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    date_to = forms.DateField(
        label="По дату",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    start_time = forms.TimeField(
        label="Начало работы",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
    )
    end_time = forms.TimeField(
        label="Конец работы",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
    )
    break_start = forms.TimeField(
        label="Начало перерыва",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
    )
    break_end = forms.TimeField(
        label="Конец перерыва",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control", "step": 1800}),
    )
    is_day_off = forms.BooleanField(
        label="Отметить выбранные даты как выходные",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    weekdays = forms.MultipleChoiceField(
        label="Только дни недели (опционально)",
        required=False,
        choices=[
            ("0", "Пн"),
            ("1", "Вт"),
            ("2", "Ср"),
            ("3", "Чт"),
            ("4", "Пт"),
            ("5", "Сб"),
            ("6", "Вс"),
        ],
        widget=forms.CheckboxSelectMultiple(),
    )
    blocked_slots = forms.CharField(
        label="Заблокированные слоты (через запятую, опционально)",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "13:00, 17:00"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        break_start = cleaned_data.get("break_start")
        break_end = cleaned_data.get("break_end")

        if date_from and date_to and date_to < date_from:
            self.add_error("date_to", "Дата 'по' не может быть меньше даты 'с'.")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "Конец работы должен быть позже начала.")

        if (break_start and not break_end) or (break_end and not break_start):
            self.add_error("break_start", "Укажите обе границы перерыва или оставьте пустыми.")
            self.add_error("break_end", "Укажите обе границы перерыва или оставьте пустыми.")
        if break_start and break_end and break_end <= break_start:
            self.add_error("break_end", "Конец перерыва должен быть позже начала.")

        if start_time and end_time and break_start and break_end:
            if not (start_time <= break_start < end_time and start_time < break_end <= end_time):
                self.add_error("break_start", "Перерыв должен быть внутри рабочего времени.")

        for key, label in (
            ("start_time", "Начало работы"),
            ("end_time", "Конец работы"),
            ("break_start", "Начало перерыва"),
            ("break_end", "Конец перерыва"),
        ):
            t = cleaned_data.get(key)
            if t and not is_half_hour_time(t):
                self.add_error(key, f"{label}: только :00 или :30.")
        return cleaned_data


class MasterJobApplicationForm(forms.ModelForm):
    class Meta:
        model = MasterJobApplication
        fields = ["full_name", "phone", "email", "experience", "portfolio_url"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "fn-home-input fn-home-input--placeholder", "placeholder": "ФИО"}),
            "phone": forms.TextInput(attrs={"class": "fn-home-input fn-home-input--placeholder", "placeholder": "Номер телефона"}),
            "email": forms.EmailInput(attrs={"class": "fn-home-input fn-home-input--placeholder", "placeholder": "Email"}),
            "experience": forms.TextInput(attrs={"class": "fn-home-input fn-home-input--placeholder", "placeholder": "Стаж"}),
            "portfolio_url": forms.URLInput(attrs={"class": "fn-home-input fn-home-input--placeholder", "placeholder": "https://"}),
        }