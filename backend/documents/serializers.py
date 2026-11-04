from rest_framework import serializers

from .models import DEFAULT_TITLE, TITLE_MAX_LENGTH, Document


class OwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)


class DocumentSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    title = serializers.CharField(
        max_length=TITLE_MAX_LENGTH,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={"max_length": f"العنوان طويل جدًا ({TITLE_MAX_LENGTH} حرف كحد أقصى)."},
    )

    class Meta:
        model = Document
        fields = ["id", "title", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

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
