from django.test import TestCase, RequestFactory
from django.urls import reverse

from opentech.apply.funds.tests.factories import ApplicationSubmissionFactory
from opentech.apply.users.tests.factories import UserFactory, StaffFactory


class SubmissionTestCase(TestCase):
    user_factory = None

    def setUp(self):
        self.factory = RequestFactory()
        self.user = self.user_factory()
        self.client.force_login(self.user)

    def submission_url(self, submission, view_name='detail'):
        view_name = f'funds:submissions:{ view_name }'
        url = reverse(view_name, kwargs={'pk': submission.id})
        request = self.factory.get(url, secure=True)
        return request.build_absolute_uri()

    def get_submission_page(self, submission, view_name='detail'):
        return self.client.get(self.submission_url(submission, view_name), secure=True, follow=True)

    def post_submission_page(self, submission, data, view_name='detail'):
        return self.client.post(self.submission_url(submission, view_name), data, secure=True, follow=True)

    def refresh(self, instance):
        return instance.__class__.objects.get(id=instance.id)


class TestStaffSubmissionView(SubmissionTestCase):
    user_factory = StaffFactory

    def test_can_view_a_submission(self):
        submission = ApplicationSubmissionFactory()
        response = self.get_submission_page(submission)
        self.assertContains(response, submission.title)

    def test_can_progress_stage(self):
        submission = ApplicationSubmissionFactory(status='concept_review_discussion', workflow_stages=2, lead=self.user)
        response = self.post_submission_page(submission, {'form-submitted-progress_form': '', 'action': 'invited_to_proposal'})

        # Cant use refresh from DB with FSM
        submission_original = self.refresh(submission)
        submission_next = submission_original.next

        self.assertRedirects(response, self.submission_url(submission_next))
        self.assertEqual(submission_original.status, 'invited_to_proposal')
        self.assertEqual(submission_next.status, 'draft_proposal')

    def test_cant_progress_stage_if_not_lead(self):
        submission = ApplicationSubmissionFactory(status='concept_review_discussion', workflow_stages=2)
        self.post_submission_page(submission, {'form-submitted-progress_form': '', 'action': 'invited_to_proposal'})

        submission = self.refresh(submission)

        self.assertEqual(submission.status, 'concept_review_discussion')
        self.assertIsNone(submission.next)


class TestApplicantSubmissionView(SubmissionTestCase):
    user_factory = UserFactory

    def test_can_view_own_submission(self):
        submission = ApplicationSubmissionFactory(user=self.user)
        response = self.get_submission_page(submission)
        self.assertContains(response, submission.title)

    def test_cant_view_others_submission(self):
        submission = ApplicationSubmissionFactory()
        response = self.get_submission_page(submission)
        self.assertEqual(response.status_code, 403)

    def test_can_edit_own_submission(self):
        submission = ApplicationSubmissionFactory(user=self.user, status='draft_proposal', workflow_stages=2)
        response = self.get_submission_page(submission, 'edit')
        self.assertContains(response, submission.title)

    def test_cant_edit_submission_incorrect_state(self):
        submission = ApplicationSubmissionFactory(user=self.user, workflow_stages=2)
        response = self.get_submission_page(submission, 'edit')
        self.assertEqual(response.status_code, 403)

    def test_cant_edit_other_submission(self):
        submission = ApplicationSubmissionFactory(status='draft_proposal', workflow_stages=2)
        response = self.get_submission_page(submission, 'edit')
        self.assertEqual(response.status_code, 403)
