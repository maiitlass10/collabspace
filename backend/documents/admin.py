from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "created_at", "updated_at"]
    list_select_related = ["owner"]
    search_fields = ["title", "owner__email", "owner__display_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
