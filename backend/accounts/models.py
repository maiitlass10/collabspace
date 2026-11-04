from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """
    Custom user model.

    - Users sign in with their email address (no username).
    - `display_name` is what other collaborators will see in the editor.
    """

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("البريد الإلكتروني", unique=True)
    display_name = models.CharField("الاسم الظاهر", max_length=60)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.display_name} <{self.email}>"
