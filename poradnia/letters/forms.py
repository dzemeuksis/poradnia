from atom.ext.crispy_forms.forms import HelperMixin, SingleButtonMixin
from atom.ext.tinycontent.forms import GIODOMixin
from atom.forms import PartialMixin
from crispy_forms.layout import BaseInput, Submit
from dal import autocomplete
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from poradnia.cases.models import Case

from .models import Attachment, Letter

CLIENT_FIELD_TEXT = _("Leave empty to use email field and create a new one user.")

EMAIL_TEXT = _(
    "The user account will be created automatically, so you have"
    "access to the archive and data about persons responsible for the case."
)

CASE_NAME_TEXT = _(
    "Short description of the case for organizational purposes. "
    "The institution name and two words will suffice."
)

REPLY_ALL_TITLE = _(
    "After choosing this option, your message will be sent to the "
    "client and the members of the legal team, who can see this "
    "case (admins and assigned team members). Select this option if your "
    "message is finalized and ready to be sent to the advicer's client."
)

SAVE_TO_REVIEW_TITLE = _(
    "After choosing this option, your message will be saved in the system "
    "as a draft. The admin will check the saved draft and will either suggest "
    "changes, or will send it to the client."
)

REPLY_TO_TEAM_TITLE = _(
    "After choosing this option, your message will only be sent to the members of "
    "the legal team who can see this case (admins and assigned team members). "
    "Select this option if you want to consult something within the team."
)

INFO_ABOUT_MARKDOWN = _(
    "This field supports <a href='https://www.markdownguide.org/cheat-sheet'>"
    "Markdown</a>"
)


class SimpleSubmit(BaseInput):
    input_type = "submit"
    field_classes = "btn"


class UserEmailField(forms.EmailField):
    def validate(self, value):
        "Check if value consists only of unique user emails."
        super().validate(value)
        if get_user_model().objects.filter(email=value).exists():
            raise ValidationError(
                _("E-mail %(email)s are already used. Please log in."),
                code="invalid",
                params={"email": value},
            )


class NewCaseForm(SingleButtonMixin, PartialMixin, GIODOMixin, ModelForm):
    attachment_cls = Attachment
    attachment_rel_field = "letter"
    attachment_file_field = "attachment"
    action_text = _("Report case")

    client = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        label=_("Client"),
        required=False,
        help_text=CLIENT_FIELD_TEXT,
        widget=autocomplete.ModelSelect2("users:autocomplete"),
    )
    email = forms.EmailField(required=False, label=_("User e-mail"))
    email_registration = UserEmailField(
        required=True, help_text=EMAIL_TEXT, label=_("E-mail")
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.form_method = "post"
        self.fields["name"].help_text = CASE_NAME_TEXT

        if settings.RICH_TEXT_ENABLED:
            self.fields["text"].help_text = INFO_ABOUT_MARKDOWN

        if self._is_super_staff():
            self.fields["client"].initial = self.user
            self.fields["client"].queryset = (
                get_user_model().objects.for_user(self.user).all()
            )
        else:
            del self.fields["client"]
            del self.fields["email"]

        if not self.user.is_anonymous:  # is registered
            del self.fields["email_registration"]

        if not (self.user.is_anonymous or self._is_super_staff()):
            del self.fields["giodo"]
        elif self._is_super_staff():
            self.fields["giodo"].required = False

    def _is_super_staff(self):
        return self.user.has_perm("cases.can_select_client")

    def clean(self):
        client_or_email = self.cleaned_data.get("email") or self.cleaned_data.get(
            "client"
        )

        if self.user.has_perm("cases.can_select_client") and not client_or_email:
            raise ValidationError(_("Have to enter user email or select a client"))
        return super().clean()

    def get_user(self):
        if self.user.is_anonymous:
            return get_user_model().objects.get_by_email_or_create(
                self.cleaned_data["email_registration"]
            )
        return self.user

    def get_client(self, user):
        if self.user.is_anonymous and self.cleaned_data["email_registration"]:
            return user
        if not self.user.has_perm("cases.can_select_client"):
            return self.user
        elif self.cleaned_data["client"]:
            return self.cleaned_data["client"]
        elif self.cleaned_data["email"]:
            return get_user_model().objects.get_by_email_or_create(
                self.cleaned_data["email"]
            )
        return self.user

    def get_case(self, client, user):
        case = Case(name=self.cleaned_data["name"], created_by=user, client=client)
        case.save()
        return case

    def save(self, commit=True, *args, **kwargs):
        user = self.get_user()
        obj = super().save(commit=False, *args, **kwargs)
        obj.status = obj.STATUS.done
        obj.genre = obj.GENRE.mail
        obj.created_by = user
        obj.created_by_is_staff = user.is_staff
        obj.client = self.get_client(user)
        if not obj.case_id:
            obj.case = self.get_case(client=obj.client, user=user)
        if commit:
            obj.save()
        return obj

    class Meta:
        fields = ["name", "text"]
        model = Letter


class AddLetterForm(HelperMixin, PartialMixin, ModelForm):
    SEND_STAFF = "send_staff"
    PROJECT = "project"
    SEND = "send"

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.case = kwargs.pop("case")
        self.user_can_send = self.user.has_perm("cases.can_send_to_client", self.case)
        super().__init__(*args, **kwargs)
        self.helper.form_action = reverse(
            "letters:add", kwargs={"case_pk": self.case.pk}
        )
        self.helper.form_tag = False
        self._fill_footer()
        self._add_buttons()
        self.fields["name"].initial = "Odp: {}".format(self.case)

        if settings.RICH_TEXT_ENABLED:
            self.fields["text"].help_text = INFO_ABOUT_MARKDOWN

    def _add_buttons(self):
        if self.user_can_send:
            self.helper.add_input(
                Submit(
                    name=self.SEND,
                    value=_("Reply to all"),
                    title=REPLY_ALL_TITLE,
                    css_class="btn-primary",
                )
            )
            self.helper.add_input(
                Submit(
                    name=self.PROJECT,
                    value=_("Save to review"),
                    title=SAVE_TO_REVIEW_TITLE,
                    css_class="btn-primary",
                )
            )
            self.helper.add_input(
                SimpleSubmit(
                    name=self.SEND_STAFF,
                    input_type="submit",
                    value=_("Write to staff"),
                    title=REPLY_TO_TEAM_TITLE,
                    css_class="btn-info",
                )
            )
        else:
            if self.user.is_staff:
                self.helper.add_input(
                    Submit(
                        name=self.PROJECT,
                        value=_("Save to review"),
                        title=SAVE_TO_REVIEW_TITLE,
                        css_class="btn-primary",
                    )
                )
                self.helper.add_input(
                    Submit(
                        name=self.SEND_STAFF,
                        value=_("Write to staff"),
                        title=REPLY_TO_TEAM_TITLE,
                        css_class="btn-info",
                    )
                )
            else:
                self.helper.add_input(
                    Submit(name="send", value=_("Reply"), css_class="btn-primary")
                )

    def _fill_footer(self):
        if self.user.is_staff and hasattr(self.user, "profile"):
            footer = self.user.profile.email_footer
            if footer:
                self.fields["text"].initial = "\n\n%s" % footer

    def get_status(self):
        if not self.user.is_staff:
            return Letter.STATUS.done
        if not self.user_can_send:
            return Letter.STATUS.staff
        if self.SEND_STAFF in self.data or self.PROJECT in self.data:
            return Letter.STATUS.staff
        return Letter.STATUS.done

    def get_genre(self):
        if not self.user.is_staff:
            return Letter.GENRE.mail
        if self.SEND_STAFF in self.data:
            return Letter.GENRE.comment
        return Letter.GENRE.mail

    def save(self, commit=True, *args, **kwargs):
        obj = super().save(commit=False, *args, **kwargs)
        obj.status = self.get_status()
        obj.genre = self.get_genre()
        obj.created_by = self.user
        obj.created_by_is_staff = self.user.is_staff
        obj.case = self.case
        if self.user.is_staff:
            if self.PROJECT in self.data:
                self.case.has_project = True
            elif obj.status == Letter.STATUS.done:
                self.case.handled = True
        else:
            self.case.handled = False
            if self.case.status == Case.STATUS.closed:
                self.case.update_status(reopen=True, save=False)
        self.case.save()
        if commit:
            obj.save()
        return obj

    class Meta:
        fields = ["name", "text"]
        model = Letter


class SendLetterForm(SingleButtonMixin, PartialMixin, ModelForm):
    comment = forms.CharField(
        widget=forms.widgets.Textarea, label=_("Comment for staff"), required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        ins = kwargs["instance"]
        super().__init__(*args, **kwargs)
        self.helper.form_action = ins.get_send_url()

    def save(self, commit=True, *args, **kwargs):
        obj = super().save(commit=False, *args, **kwargs)
        obj.modified_by = self.user
        obj.status = obj.STATUS.done
        obj.save()

        obj.case.handled = True
        obj.case.has_project = False
        obj.case.save()

        obj.send_notification(actor=self.user, verb="send_to_client")
        if self.cleaned_data["comment"]:
            msg = Letter.objects.create(
                case=obj.case,
                genre=Letter.GENRE.comment,
                created_by=self.user,
                created_by_is_staff=self.user.is_staff,
                text=self.cleaned_data["comment"],
                status=obj.STATUS.staff,
            )
            msg.send_notification(actor=self.user, verb="drop_a_note")
        return obj

    class Meta:
        model = Letter
        fields = []


class AttachmentForm(ModelForm):
    class Meta:
        fields = ["attachment"]
        model = Attachment


class LetterForm(SingleButtonMixin, PartialMixin, ModelForm):  # eg. edit form
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.helper.form_action = kwargs["instance"].get_edit_url()
        self.helper.form_method = "post"

    def save(self, commit=True, *args, **kwargs):
        obj = super().save(commit=False, *args, **kwargs)
        obj.modified_by = self.user
        obj.save()
        return obj

    class Meta:
        fields = ["name", "text"]
        model = Letter
