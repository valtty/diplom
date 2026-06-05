from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('careers/apply/', views.master_job_apply, name='master_job_apply'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/job-applications/', views.admin_job_applications, name='admin_job_applications'),
    path('dashboard/portfolio-moderation/', views.admin_portfolio_moderation, name='admin_portfolio_moderate'),
    path('services/', views.ServiceListView.as_view(), name='services'),
    path('service/add/', views.ServiceCreateView.as_view(), name='service_add'),
    path('service/<int:service_id>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('service/<int:service_id>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    path('service/<slug:slug>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('service/id/<int:service_id>/', views.ServiceDetailView.as_view(), name='service_detail_by_id'),
    path('masters/', views.MasterListView.as_view(), name='masters'),
    path('master/<int:master_id>/', views.MasterDetailView.as_view(), name='master_detail'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('promotions/', views.PromotionListView.as_view(), name='promotions'),
    path('dashboard/promotions/', views.promotion_dashboard, name='promotion_dashboard'),
    path('dashboard/schedule/', views.schedule_dashboard, name='schedule_dashboard'),
    path('api/available-slots/', views.available_slots, name='available_slots'),
    path('dashboard/promotions/<int:promotion_id>/delete/', views.promotion_delete, name='promotion_delete'),
    path('certificates/', views.certificates, name='certificates'),
    path('blog/', views.BlogListView.as_view(), name='blog'),
    path('blog/new/', views.blog_create, name='blog_create'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('blog/comment/<int:comment_id>/delete/', views.blog_delete_comment, name='blog_delete_comment'),
    path('dashboard/blog/moderation/', views.blog_moderation, name='blog_moderation'),
    path('dashboard/blog/<int:post_id>/<slug:action>/', views.blog_moderate_action, name='blog_moderate_action'),
    path('dashboard/author-request/', views.author_request, name='author_request'),
    path('dashboard/author-requests/', views.author_requests_manage, name='author_requests_manage'),
    path('dashboard/author-requests/<int:request_id>/<slug:action>/', views.author_request_action, name='author_request_action'),
    path('contacts/', views.contacts, name='contacts'),
    path('profile/', views.profile_page, name='profile'),

    # CRUD для мастеров (как в журнале)
    path('master/add/', views.MasterCreateView.as_view(), name='master_add'),
    path('master/<int:master_id>/edit/', views.MasterUpdateView.as_view(), name='master_edit'),
    path('master/<int:master_id>/delete/', views.MasterDeleteView.as_view(), name='master_delete'),
    path('master/<int:master_id>/', views.MasterDetailView.as_view(), name='master_detail'),

    # CRUD для клиентов (как в журнале)
    path('clients/', views.ClientListView.as_view(), name='clients'),
    path('client/<int:client_id>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('client/add/', views.ClientCreateView.as_view(), name='client_add'),
    path('client/<int:client_id>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('client/<int:client_id>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    # Записи на процедуру
    path('appointments/', views.appointments_redirect, name='appointments'),
    path('appointment/new/', views.appointment_create, name='appointment_create'),
    path('appointment/<int:appointment_id>/', views.AppointmentDetailView.as_view(), name='appointment_detail'),
    path('appointment/<int:appointment_id>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    path('appointment/<int:appointment_id>/confirm/', views.appointment_confirm, name='appointment_confirm'),
    path('appointment/<int:appointment_id>/complete/', views.appointment_complete, name='appointment_complete'),
    path('payments/yookassa/webhook/', views.yookassa_webhook, name='yookassa_webhook'),
    path('payments/card/<int:transaction_id>/', views.payment_card, name='payment_card'),
    path('certificates/activate/', views.activate_certificate, name='activate_certificate'),

    # Отзывы
    path('review/<int:appointment_id>/new/', views.review_create, name='review_create'),

    # Портфолио для мастеров
    path('portfolio/add/', views.portfolio_add, name='portfolio_add'),
    path('portfolio/<int:image_id>/delete/', views.portfolio_delete, name='portfolio_delete'),

    # Алиасы для старых ссылок
    path('dashboard/services/', views.ServiceListView.as_view(), name='admin_services'),
    path('dashboard/masters/', views.MasterListView.as_view(), name='admin_masters'),
]