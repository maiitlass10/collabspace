from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.presence import presence_color

from .access import role_for
from .models import DEFAULT_TITLE, TITLE_MAX_LENGTH, ActivityLog, Document, DocumentAccess, DocumentVersion

User = get_user_model()


class OwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)


class DocumentSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    # My role on this document: "owner" | "editor" | "viewer".
    role = serializers.SerializerMethodField()
    title = serializers.CharField(
        max_length=TITLE_MAX_LENGTH,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={"max_length": f"العنوان طويل جدًا ({TITLE_MAX_LENGTH} حرف كحد أقصى)."},
    )

    class Meta:
        model = Document
        fields = ["id", "title", "owner", "role", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "role", "created_at", "updated_at"]

    def get_role(self, document):
        return role_for(self.context["request"].user, document)

    def validate_title(self, value):
        # Collapse internal whitespace: "  my    doc " -> "my doc"
        value = " ".join(value.split())
        if not value:
            # Creating without a title is fine (default title);
            # renaming to an empty title is not.
            if self.instance is not None:
                raise serializers.ValidationError("العنوان لا يمكن أن يكون فارغًا.")
            return DEFAULT_TITLE
        return value


class MemberUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    color = serializers.SerializerMethodField()

    def get_color(self, user) -> str:
        return presence_color(user)


class MemberSerializer(serializers.ModelSerializer):
    """One person a document is shared with."""

    user = MemberUserSerializer(read_only=True)

    class Meta:
        model = DocumentAccess
        fields = ["id", "user", "role", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


ROLE_ERRORS = {"invalid_choice": "الدور يجب أن يكون «محرِّر» أو «قارئ»."}


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={"invalid": "أدخل بريدًا إلكترونيًا صحيحًا."})
    role = serializers.ChoiceField(choices=DocumentAccess.ROLE_CHOICES, error_messages=ROLE_ERRORS)

    def validate_email(self, value):
        document = self.context["document"]
        user = User.objects.filter(email__iexact=value.strip(), is_active=True).first()
        if user is None:
            raise serializers.ValidationError("لا يوجد حساب بهذا البريد. اطلب من الشخص إنشاء حساب أولًا.")
        if user.pk == document.owner_id:
            raise serializers.ValidationError("أنت مالك هذا المستند بالفعل.")
        if DocumentAccess.objects.filter(document=document, user=user).exists():
            raise serializers.ValidationError("هذا الشخص لديه وصول إلى المستند بالفعل.")
        return user  # validated_data["email"] is the User object


class ChangeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=DocumentAccess.ROLE_CHOICES, error_messages=ROLE_ERRORS)


class PersonSerializer(serializers.Serializer):
    """A user as shown in the activity log / versions list (no email)."""

    id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    color = serializers.SerializerMethodField()

    def get_color(self, user) -> str:
        return presence_color(user)


class ActivitySerializer(serializers.ModelSerializer):
    actor = PersonSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ActivityLog
        fields = ["id", "action", "actor", "metadata", "created_at"]


class VersionSerializer(serializers.ModelSerializer):
    created_by = PersonSerializer(read_only=True, allow_null=True)
    label = serializers.CharField(
        max_length=DocumentVersion.LABEL_MAX_LENGTH,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={"max_length": f"الاسم طويل جدًا ({DocumentVersion.LABEL_MAX_LENGTH} حرف كحد أقصى)."},
    )

    class Meta:
        model = DocumentVersion
        fields = ["id", "label", "kind", "created_by", "created_at"]
        read_only_fields = ["id", "kind", "created_by", "created_at"]

    def validate_label(self, value):
        return " ".join(value.split())


class VersionDetailSerializer(VersionSerializer):
    """Includes the content (Yjs state, base64) so the browser can preview it."""

    state = serializers.SerializerMethodField()

    class Meta(VersionSerializer.Meta):
        fields = VersionSerializer.Meta.fields + ["state"]

    def get_state(self, version) -> str:
        import base64

        return base64.b64encode(bytes(version.yjs_state)).decode("ascii")
