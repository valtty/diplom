# Generated manually for MasterJobApplication and portfolio flags

from django.db import migrations, models


def approve_existing_portfolio(apps, schema_editor):
    PortfolioImage = apps.get_model("main", "PortfolioImage")
    PortfolioImage.objects.all().update(is_approved=True, show_on_homepage=False)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_sitesettings_appointment_certificate_applied_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MasterJobApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=200, verbose_name="ФИО")),
                ("phone", models.CharField(max_length=50, verbose_name="Телефон")),
                ("email", models.EmailField(max_length=254, verbose_name="Email")),
                ("experience", models.CharField(blank=True, max_length=300, verbose_name="Стаж / опыт")),
                ("portfolio_url", models.URLField(blank=True, verbose_name="Ссылка на портфолио")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "Новая"),
                            ("review", "На рассмотрении"),
                            ("accepted", "Принята"),
                            ("rejected", "Отклонена"),
                        ],
                        default="new",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                ("admin_notes", models.TextField(blank=True, verbose_name="Заметки администратора")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлено")),
            ],
            options={
                "verbose_name": "Заявка мастера на работу",
                "verbose_name_plural": "Заявки мастеров на работу",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="portfolioimage",
            name="show_on_homepage",
            field=models.BooleanField(
                default=False,
                help_text="Администратор отмечает работы для блока на главной. Остальные одобренные — только на странице портфолио.",
                verbose_name="Показывать на главной (до 7 работ)",
            ),
        ),
        migrations.AlterField(
            model_name="portfolioimage",
            name="is_approved",
            field=models.BooleanField(default=False, verbose_name="Одобрено администратором"),
        ),
        migrations.RunPython(approve_existing_portfolio, migrations.RunPython.noop),
    ]
