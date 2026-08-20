from django import forms

from .models import Role


class RoleForm(forms.ModelForm):
    name = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex.: Professor",
            }
        ),
    )

    class Meta:
        model = Role
        fields = [
            "name",
            "description",
            "icon",
            "color",
            "display_order",
        ]

        widgets = {
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "icon": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "color": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "display_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 0,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["name"].initial = self.instance.group.name
