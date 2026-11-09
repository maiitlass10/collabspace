from django.contrib import admin

from .models import Document, DocumentAccess


class DocumentAccessInline(admin.TabularInline):
    model = DocumentAccess
    fk_name = "document"
    extra = 0
    autocomplete_fields = ["user"]
    readonly_fields = ["invited_by", "created_at"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "created_at", "updated_at"]
    list_select_related = ["owner"]
    search_fields = ["title", "owner__email", "owner__display_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [DocumentAccessInline]
