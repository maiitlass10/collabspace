from django.contrib import admin

from .models import ActivityLog, Document, DocumentAccess, DocumentVersion


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


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "document", "actor", "action"]
    list_filter = ["action"]
    list_select_related = ["document", "actor"]
    search_fields = ["document__title", "actor__email"]
    readonly_fields = ["document", "actor", "action", "metadata", "created_at"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["created_at", "document", "label", "kind", "created_by"]
    list_filter = ["kind"]
    list_select_related = ["document", "created_by"]
    readonly_fields = ["document", "created_by", "kind", "created_at"]
