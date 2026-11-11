import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class DigitsOnlyPasswordValidator:
    def validate(self, password, user=None):
        if not re.fullmatch(r"[0-9]+", password):
            raise ValidationError(
                _("La contraseña debe contener únicamente números."),
                code="password_not_digits",
            )

    def get_help_text(self):
        return _("La contraseña debe contener únicamente números.")
