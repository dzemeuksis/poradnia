import unittest
import datetime
from os.path import join, dirname
from datetime import timedelta
from email import message_from_file

from django.test import TestCase
from django.utils.timezone import utc
from django_mailbox.models import Mailbox

from cases.factories import CaseFactory
from letters.factories import LetterFactory
from letters.models import Letter, mail_process
from users.factories import UserFactory


class QuerySetTestCase(TestCase):
    def _for_user(self, status, exists, is_superuser=False, is_staff=False):
        user = UserFactory(is_superuser=is_superuser, is_staff=is_staff)
        obj = LetterFactory(status=status, case__created_by=user)
        self.assertEqual(Letter.objects.for_user(user).filter(pk=obj.pk).exists(), exists)

    def test_for_user_admin_done(self):
        self._for_user(status=Letter.STATUS.done,
                       exists=True,
                       is_superuser=True,
                       is_staff=True)

    def test_for_user_admin_staff(self):
        self._for_user(status=Letter.STATUS.staff,
                       exists=True,
                       is_superuser=True,
                       is_staff=True)

    def test_for_user_staff_done(self):
        self._for_user(status=Letter.STATUS.done,
                       exists=True,
                       is_superuser=False,
                       is_staff=True)

    def test_for_user_staff_staff(self):
        self._for_user(status=Letter.STATUS.staff,
                       exists=True,
                       is_superuser=False,
                       is_staff=True)

    def test_for_user_client_done(self):
        self._for_user(status=Letter.STATUS.done,
                       exists=True,
                       is_superuser=False,
                       is_staff=False)

    def test_for_user_client_staff(self):
        self._for_user(status=Letter.STATUS.staff,
                       exists=False,
                       is_superuser=False,
                       is_staff=False)


class LastQuerySetTestCase(TestCase):
    def setUp(self):
        self.now = datetime.datetime.utcnow().replace(tzinfo=utc)
        self.case = CaseFactory()

    def test_lr_staff_letter_no_return(self):
        # staff letter no return (no return)
        LetterFactory(case=self.case,
                      created_by__is_staff=True)
        with self.assertRaises(IndexError):
            Letter.objects.case(self.case).last_received()

    def test_lr_new_client_letter_setup(self):
        l = LetterFactory(case=self.case,
                          created_by__is_staff=False)
        self.assertEqual(Letter.objects.case(self.case).last_received(), l)

    def test_lr_new_client_letter_update(self):
        l = LetterFactory(case=self.case,
                          created_by__is_staff=False)
        self.assertEqual(Letter.objects.case(self.case).last_received(), l)
        new = LetterFactory(case=self.case,
                            created_by__is_staff=False)
        self.assertEqual(Letter.objects.case(self.case).last_received(), new)
        t = self.now-timedelta(days=10)
        old = LetterFactory(created_on=t,
                            case=self.case,
                            created_by__is_staff=False)
        old.created_on = t
        old.save()
        self.assertEqual(Letter.objects.case(self.case).last_received(), new)

    def test_lr_new_letter_from_staff(self):
        l = LetterFactory(created_on=self.now+timedelta(days=2),
                          case=self.case,
                          created_by__is_staff=False)
        LetterFactory(created_on=self.now+timedelta(days=10),
                      case=self.case,
                      created_by__is_staff=True)
        self.assertEqual(Letter.objects.case(self.case).last_received(), l)

    def test_last_staff_send(self):
        l = LetterFactory(status='done', case=self.case, created_by__is_staff=True)
        self.assertEqual(Letter.objects.case(self.case).last_staff_send(), l)

        LetterFactory(status='staff', case=self.case, created_by__is_staff=True)
        self.assertEqual(Letter.objects.case(self.case).last_staff_send(), l)

        l2 = LetterFactory(status='done', case=self.case, created_by__is_staff=True)
        self.assertEqual(Letter.objects.case(self.case).last_staff_send(), l2)


class ReceiveEmailTestCase(TestCase):
    def setUp(self):
        self.mailbox = Mailbox.objects.create(from_email='from@example.com')
        super(TestCase, self).setUp()

    @staticmethod
    def _get_email_object(filename):  # See coddingtonbear/django-mailbox#89
        path = join(dirname(__file__), 'messages', filename)
        fp = open(path, 'rb')
        return message_from_file(fp)

    def test_user_identification(self):
        user = UserFactory(email='user@example.com')
        message = self._get_email_object('cc_message.eml')
        msg = self.mailbox._process_message(message)
        mail_process(sender=self.mailbox, message=msg)
        self.assertEqual(user, msg.letter_set.all()[0].created_by)

    def test_cc_message(self):
        case = CaseFactory(pk=639)
        message = self._get_email_object('cc_message.eml')
        msg = self.mailbox._process_message(message)
        msg.save()

        mail_process(sender=self.mailbox, message=msg)

        self.assertEqual(case, msg.letter_set.all()[0].case)
