from django.contrib import admin
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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "duration_minutes", "popular", "is_active")
    list_filter = ("is_active", "popular", "category")
    search_fields = ("name", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ("full_name", "specialization", "experience", "rating", "is_active")
    list_filter = ("is_active", "specialization", "services")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    filter_horizontal = ("services",)
    fields = (
        "user",
        "photo",
        "bio",
        "experience",
        "work_experience",
        "specialization",
        "certificates",
        "social_instagram",
        "services",
        "rating",
        "is_active",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user",)
        return ()

    def full_name(self, obj):
        return obj.full_name

    full_name.short_description = "Имя"


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "birth_date", "bonus_balance", "created_at")
    search_fields = ("user__username", "user__first_name", "user__last_name")

    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    full_name.short_description = 'Имя'


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ("master", "design_type", "color_scheme", "is_approved", "show_on_homepage", "uploaded_at")
    list_filter = ("master", "design_type", "color_scheme", "is_approved", "show_on_homepage")
    search_fields = ("master__user__username", "description")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "discount_percent", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "description", "promo_code")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_number", "amount", "recipient_name", "is_activated", "created_at")
    list_filter = ("is_activated",)
    search_fields = ("certificate_number", "buyer_name", "recipient_name")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "master", "service", "date", "status", "is_prepaid", "bonus_used")
    list_filter = ("status", "date", "master", "is_prepaid")
    search_fields = ("client__user__username", "master__user__username", "comment")
    date_hierarchy = "date"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("client", "master", "rating", "created_at", "is_published")
    list_filter = ("rating", "is_published", "master")
    search_fields = ("client__user__username", "text")


@admin.register(BonusTransaction)
class BonusTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "type", "source", "created_at")
    list_filter = ("type", "source")
    search_fields = ("user__username", "description")


@admin.register(LoyaltySettings)
class LoyaltySettingsAdmin(admin.ModelAdmin):
    list_display = ("bonus_percent", "bonus_to_rub_rate", "welcome_bonus", "referral_bonus", "is_active")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "amount", "payment_method", "status", "is_test", "created_at")
    list_filter = ("status", "payment_method", "is_test")
    search_fields = ("payment_id",)


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ("event", "transaction", "signature_valid", "created_at")
    list_filter = ("signature_valid", "event")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "moderation_status", "is_published", "created_at")
    list_filter = ("category", "is_published", "moderation_status")
    search_fields = ("title", "excerpt")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "is_approved", "created_at")
    list_filter = ("is_approved",)


@admin.register(MasterSchedule)
class MasterScheduleAdmin(admin.ModelAdmin):
    list_display = ("master", "weekday", "start_time", "end_time", "is_active")
    list_filter = ("weekday", "is_active")


@admin.register(AuthorRequest)
class AuthorRequestAdmin(admin.ModelAdmin):
    list_display = ("master", "status", "created_at")
    list_filter = ("status",)


@admin.register(MasterJobApplication)
class MasterJobApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("full_name", "email", "phone")


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("master", "work_date", "start_time", "end_time", "is_day_off")
    list_filter = ("work_date", "master", "is_day_off")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "hero_background", "certificate_background")