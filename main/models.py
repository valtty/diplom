import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from users.models import CustomUser


class Category(models.Model):
    name = models.CharField("Название категории", max_length=150)
    slug = models.SlugField("Slug", unique=True)
    description = models.TextField("Описание", blank=True)
    icon = models.CharField("Иконка Font Awesome", max_length=100, blank=True)
    order = models.IntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Категория услуг"
        verbose_name_plural = "Категории услуг"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField("Название услуги", max_length=200)
    slug = models.SlugField("Slug", unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        verbose_name="Категория",
        null=True,
        blank=True,
        related_name="services",
    )
    description = models.TextField("Описание")
    price = models.DecimalField("Цена", max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField("Длительность (минут)", default=120)
    image = models.ImageField("Фото услуги", upload_to="services/", blank=True, null=True)
    popular = models.BooleanField("Популярная услуга", default=False)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Master(models.Model):
    SPECIALIZATION_CHOICES = [
        ("manicure", "Маникюр"),
        ("pedicure", "Педикюр"),
        ("design", "Дизайн"),
        ("all", "Все направления"),
    ]
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"role": CustomUser.Role.MASTER},
        related_name="master_profile",
    )
    bio = models.TextField("О мастере", max_length=1000, blank=True)
    experience = models.PositiveIntegerField("Стаж (лет)", default=1)
    work_experience = models.CharField("Опыт работы (текст)", max_length=150, blank=True)
    specialization = models.CharField(
        "Специализация", max_length=20, choices=SPECIALIZATION_CHOICES, default="all"
    )
    certificates = models.TextField("Сертификаты", blank=True)
    can_publish_blog = models.BooleanField("Может публиковать статьи", default=False)
    social_instagram = models.URLField("Instagram", blank=True, null=True)
    rating = models.DecimalField("Рейтинг", max_digits=3, decimal_places=2, default=Decimal("0.00"))
    photo = models.ImageField("Фото мастера", upload_to="masters/", blank=True, null=True)
    services = models.ManyToManyField(Service, verbose_name="Услуги", blank=True)
    is_active = models.BooleanField("Работает", default=True)
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Мастер"
        verbose_name_plural = "Мастера"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username


class Client(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"role": CustomUser.Role.CLIENT},
        related_name="client_profile",
    )
    birth_date = models.DateField("Дата рождения", blank=True, null=True)
    bonus_balance = models.IntegerField("Бонусный баланс", default=0)
    referred_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class PortfolioImage(models.Model):
    DESIGN_CHOICES = [
        ("french", "Френч"),
        ("gradient", "Градиент"),
        ("glitter", "Блестки"),
        ("stones", "Стразы"),
        ("molding", "Лепка"),
        ("stamping", "Стемпинг"),
        ("other", "Другое"),
    ]
    COLOR_CHOICES = [
        ("pink", "Розовый"),
        ("red", "Красный"),
        ("white", "Белый"),
        ("black", "Черный"),
        ("blue", "Синий"),
        ("green", "Зеленый"),
        ("purple", "Фиолетовый"),
        ("multicolor", "Многоцветный"),
    ]
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        verbose_name="Мастер",
        related_name="portfolio_images",
    )
    image = models.ImageField("Фото работы", upload_to="portfolio/")
    description = models.CharField("Описание", max_length=255, blank=True)
    design_type = models.CharField("Тип дизайна", max_length=20, choices=DESIGN_CHOICES, default="other")
    color_scheme = models.CharField(
        "Цветовая схема", max_length=20, choices=COLOR_CHOICES, default="multicolor"
    )
    video_url = models.URLField("Ссылка на видео", blank=True, null=True)
    is_approved = models.BooleanField("Одобрено администратором", default=False)
    show_on_homepage = models.BooleanField(
        "Показывать на главной (до 7 работ)",
        default=False,
        help_text="Администратор отмечает работы для блока на главной. Остальные одобренные — только на странице портфолио.",
    )
    uploaded_at = models.DateTimeField("Дата загрузки", auto_now_add=True)

    class Meta:
        verbose_name = "Фото портфолио"
        verbose_name_plural = "Фото портфолио"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Работа {self.master.full_name} от {self.uploaded_at.date()}"


class Promotion(models.Model):
    title = models.CharField("Название акции", max_length=200)
    slug = models.SlugField("Slug", unique=True)
    description = models.TextField("Описание")
    discount_percent = models.PositiveIntegerField(
        "Скидка (%)", validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    services = models.ManyToManyField(Service, verbose_name="Услуги", blank=True, related_name="promotions")
    start_date = models.DateField("Дата начала")
    end_date = models.DateField("Дата окончания")
    is_active = models.BooleanField("Активна", default=True)
    promo_code = models.CharField("Промокод", max_length=50, unique=True, blank=True, null=True)
    image = models.ImageField("Изображение", upload_to="promotions/", blank=True, null=True)
    conditions = models.TextField("Условия акции", blank=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ["-start_date"]

    def __str__(self):
        return self.title


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидание подтверждения"),
        ("confirmed", "Подтверждена"),
        ("completed", "Выполнена"),
        ("cancelled", "Отменена"),
    ]
    PAYMENT_OPTION_CHOICES = [
        ("card", "Предоплата картой"),
        ("bonus", "Оплата бонусами"),
        ("certificate", "Оплата сертификатом"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name="Клиент",
        related_name="appointments",
    )
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        verbose_name="Мастер",
        related_name="appointments",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        verbose_name="Услуга",
    )
    promo_code_applied = models.ForeignKey(
        Promotion,
        on_delete=models.SET_NULL,
        verbose_name="Примененная акция",
        null=True,
        blank=True,
    )
    certificate_applied = models.ForeignKey(
        "Certificate",
        on_delete=models.SET_NULL,
        verbose_name="Примененный сертификат",
        null=True,
        blank=True,
        related_name="appointments",
    )
    date = models.DateField("Дата")
    time = models.TimeField("Время")
    comment = models.TextField("Комментарий", max_length=500, blank=True)
    design_preference = models.TextField("Ссылка на желаемый дизайн", blank=True)
    bonus_used = models.IntegerField("Списано бонусов", default=0)
    payment_option = models.CharField(
        "Способ оплаты", max_length=20, choices=PAYMENT_OPTION_CHOICES, default="card"
    )
    prepayment_amount = models.DecimalField("Сумма предоплаты", max_digits=8, decimal_places=2, default=0)
    is_prepaid = models.BooleanField("Предоплата внесена", default=False)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ["-date", "-time"]
        constraints = [
            models.UniqueConstraint(fields=["master", "date", "time"], name="unique_master_time_slot"),
        ]

    def __str__(self):
        return f"{self.client.user.username} - {self.service.name} на {self.date}"


class Certificate(models.Model):
    certificate_number = models.CharField("Номер сертификата", max_length=50, unique=True, editable=False)
    amount = models.DecimalField("Номинал", max_digits=10, decimal_places=2)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Услуга")
    buyer_name = models.CharField("Имя покупателя", max_length=150)
    buyer_email = models.EmailField("Email покупателя")
    recipient_name = models.CharField("Имя получателя", max_length=150)
    recipient_email = models.EmailField("Email получателя")
    message = models.TextField("Поздравительное сообщение", blank=True)
    is_activated = models.BooleanField("Активирован", default=False)
    valid_until = models.DateField("Действителен до", null=True, blank=True)
    activated_at = models.DateTimeField("Дата активации", null=True, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    pdf_file = models.FileField("PDF файл", upload_to="certificates/", blank=True, null=True)

    class Meta:
        verbose_name = "Подарочный сертификат"
        verbose_name_plural = "Подарочные сертификаты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.certificate_number

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = f"FN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.valid_until:
            self.valid_until = (timezone.now() + timezone.timedelta(days=365)).date()
        super().save(*args, **kwargs)


class LoyaltySettings(models.Model):
    bonus_percent = models.DecimalField("Процент бонусов", max_digits=5, decimal_places=2, default=Decimal("10.00"))
    bonus_to_rub_rate = models.DecimalField("Курс бонуса к рублю", max_digits=6, decimal_places=2, default=Decimal("1.00"))
    welcome_bonus = models.IntegerField("Приветственный бонус", default=500)
    referral_bonus = models.IntegerField("Реферальный бонус", default=200)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Настройки бонусной системы"
        verbose_name_plural = "Настройки бонусной системы"

    def __str__(self):
        return "Настройки программы лояльности"


class BonusTransaction(models.Model):
    TYPE_CHOICES = [("accrual", "Начисление"), ("spending", "Списание")]
    SOURCE_CHOICES = [
        ("appointment", "Запись"),
        ("review", "Отзыв"),
        ("referral", "Реферал"),
        ("welcome", "Приветственный бонус"),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="bonus_transactions")
    amount = models.IntegerField("Сумма")
    type = models.CharField("Тип", max_length=20, choices=TYPE_CHOICES)
    source = models.CharField("Источник", max_length=20, choices=SOURCE_CHOICES)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField("Описание", max_length=255)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Бонусная транзакция"
        verbose_name_plural = "Бонусные транзакции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.amount} ({self.type})"


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ("pending", "В ожидании"),
        ("paid", "Оплачено"),
        ("failed", "Ошибка"),
        ("refunded", "Возврат"),
    ]
    METHOD_CHOICES = [("card", "Карта"), ("bonus", "Бонусы")]
    appointment = models.OneToOneField(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_transaction"
    )
    certificate = models.OneToOneField(
        Certificate, on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_transaction"
    )
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    prepaid_amount = models.DecimalField("Предоплата", max_digits=10, decimal_places=2, default=0)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_id = models.CharField("ID платежа", max_length=100, unique=True)
    payment_method = models.CharField("Метод оплаты", max_length=20, choices=METHOD_CHOICES, default="card")
    is_test = models.BooleanField("Тестовый платеж", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    paid_at = models.DateTimeField("Оплачено", null=True, blank=True)

    class Meta:
        verbose_name = "Платежная транзакция"
        verbose_name_plural = "Платежные транзакции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.payment_id} ({self.status})"


class PaymentLog(models.Model):
    transaction = models.ForeignKey(
        PaymentTransaction, on_delete=models.CASCADE, related_name="logs", null=True, blank=True
    )
    event = models.CharField("Событие", max_length=120)
    payload = models.JSONField("Payload", default=dict, blank=True)
    signature_valid = models.BooleanField("Подпись валидна", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Лог платежа"
        verbose_name_plural = "Логи платежей"
        ordering = ["-created_at"]


class Review(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name="Клиент",
    )
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        verbose_name="Мастер",
        related_name="reviews",
    )
    appointment = models.OneToOneField(
        "Appointment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="review",
        verbose_name="Запись",
    )
    rating = models.PositiveIntegerField("Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField("Текст отзыва", max_length=1000)
    created_at = models.DateTimeField("Дата", auto_now_add=True)
    is_published = models.BooleanField("Опубликован", default=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Отзыв от {self.client.user.username} на {self.master.full_name}"


class BlogPost(models.Model):
    MODERATION_CHOICES = [
        ("pending", "На модерации"),
        ("approved", "Одобрено"),
        ("rejected", "Отклонено"),
    ]
    CATEGORY_CHOICES = [
        ("care", "Уход"),
        ("design", "Дизайны"),
        ("tips", "Советы"),
        ("news", "Новости"),
    ]
    title = models.CharField("Заголовок", max_length=250)
    slug = models.SlugField("Slug", unique=True)
    content = models.TextField("Содержание")
    excerpt = models.TextField("Краткое описание")
    image = models.ImageField("Изображение", upload_to="blog/", blank=True, null=True)
    category = models.CharField("Категория", max_length=20, choices=CATEGORY_CHOICES)
    author = models.ForeignKey(Master, on_delete=models.SET_NULL, null=True, blank=True, related_name="blog_posts")
    views = models.IntegerField("Просмотры", default=0)
    is_published = models.BooleanField("Опубликовано", default=False)
    moderation_status = models.CharField(
        "Статус модерации",
        max_length=20,
        choices=MODERATION_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Статья блога"
        verbose_name_plural = "Статьи блога"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField("Комментарий")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    is_approved = models.BooleanField("Одобрен", default=True)

    class Meta:
        verbose_name = "Комментарий к статье"
        verbose_name_plural = "Комментарии к статьям"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.post.title}"


class MasterSchedule(models.Model):
    WEEKDAY_CHOICES = [
        (0, "Понедельник"),
        (1, "Вторник"),
        (2, "Среда"),
        (3, "Четверг"),
        (4, "Пятница"),
        (5, "Суббота"),
        (6, "Воскресенье"),
    ]
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="schedules")
    weekday = models.IntegerField("День недели", choices=WEEKDAY_CHOICES)
    start_time = models.TimeField("Начало работы")
    end_time = models.TimeField("Конец работы")
    break_start = models.TimeField("Начало перерыва", null=True, blank=True)
    break_end = models.TimeField("Конец перерыва", null=True, blank=True)
    is_active = models.BooleanField("Рабочий день", default=True)

    class Meta:
        verbose_name = "График мастера"
        verbose_name_plural = "Графики мастеров"
        unique_together = ("master", "weekday")
        ordering = ["master", "weekday"]


class Schedule(models.Model):
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="date_schedules")
    work_date = models.DateField("Дата работы")
    start_time = models.TimeField("Начало работы")
    end_time = models.TimeField("Конец работы")
    break_start = models.TimeField("Начало перерыва", null=True, blank=True)
    break_end = models.TimeField("Конец перерыва", null=True, blank=True)
    blocked_slots = models.JSONField("Заблокированные слоты", default=list, blank=True)
    is_day_off = models.BooleanField("Выходной", default=False)

    class Meta:
        verbose_name = "Расписание мастера"
        verbose_name_plural = "Расписание мастеров"
        unique_together = ("master", "work_date")
        ordering = ["work_date", "start_time"]


class MasterJobApplication(models.Model):
    """Заявка мастера на работу (форма на главной)."""

    STATUS_CHOICES = [
        ("new", "Новая"),
        ("review", "На рассмотрении"),
        ("accepted", "Принята"),
        ("rejected", "Отклонена"),
    ]

    full_name = models.CharField("ФИО", max_length=200)
    phone = models.CharField("Телефон", max_length=50)
    email = models.EmailField("Email")
    experience = models.CharField("Стаж / опыт", max_length=300, blank=True)
    portfolio_url = models.URLField("Ссылка на портфолио", blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="new")
    admin_notes = models.TextField("Заметки администратора", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Заявка мастера на работу"
        verbose_name_plural = "Заявки мастеров на работу"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.get_status_display()})"


class AuthorRequest(models.Model):
    STATUS_CHOICES = [("pending", "На рассмотрении"), ("approved", "Одобрено"), ("rejected", "Отклонено")]
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="author_requests")
    message = models.TextField("Комментарий", blank=True)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на авторство"
        verbose_name_plural = "Заявки на авторство"
        ordering = ["-created_at"]


class SiteSettings(models.Model):
    hero_background = models.ImageField("Фон баннера", upload_to="settings/", null=True, blank=True)
    certificate_background = models.ImageField(
        "Фон сертификата", upload_to="settings/", null=True, blank=True
    )

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"