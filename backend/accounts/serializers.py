from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .presence import presence_color

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of the current user (never includes the password)."""

    # The color collaborators see for this user (avatar, caret, selection).
    color = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "color", "date_joined"]
        read_only_fields = fields

    def get_color(self, user) -> str:
        return presence_color(user)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    display_name = serializers.CharField(min_length=2, max_length=60, trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("يوجد حساب مسجّل بهذا البريد الإلكتروني.")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "كلمتا المرور غير متطابقتين."})

        # Run Django's password validators (length, common passwords, similarity...).
        candidate = User(email=attrs["email"], display_name=attrs["display_name"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            display_name=validated_data["display_name"],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"].strip().lower(),
            password=attrs["password"],
        )
        # Same message for "unknown email" and "wrong password" so attackers
        # cannot discover which emails are registered.
        if user is None:
            raise serializers.ValidationError(
                "البريد الإلكتروني أو كلمة المرور غير صحيحة.", code="authorization"
            )
        attrs["user"] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """Fields a user may change about themselves (settings page)."""

    display_name = serializers.CharField(
        min_length=2,
        max_length=60,
        trim_whitespace=True,
        error_messages={
            "min_length": "الاسم يجب أن يكون حرفين على الأقل.",
            "max_length": "الاسم طويل جدًا (60 حرفًا كحد أقصى).",
            "blank": "الاسم لا يمكن أن يكون فارغًا.",
        },
    )

    class Meta:
        model = User
        fields = ["display_name"]

    def validate_display_name(self, value):
        return " ".join(value.split())


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("كلمة المرور الحالية غير صحيحة.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "كلمتا المرور غير متطابقتين."})
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": "اختر كلمة مرور مختلفة عن الحالية."})
        try:
            validate_password(attrs["new_password"], user=self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs
