from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from django.views.generic.edit import ProcessFormView, ModelFormMixin

from opentech.apply.funds.models import ApplicationSubmission
from opentech.apply.users.decorators import staff_required

from .forms import ConceptDeterminationForm, ProposalDeterminationForm
from .models import Determination


def get_form_for_stage(submission):
    forms = [ConceptDeterminationForm, ProposalDeterminationForm]
    index = [
        i for i, stage in enumerate(submission.workflow.stages)
        if submission.stage.name == stage.name
    ][0]
    return forms[index]


class CreateOrUpdateView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except self.model.DoesNotExist:
            self.object = None

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except self.model.DoesNotExist:
            self.object = None

        return super().post(request, *args, **kwargs)


class DeterminationCreateOrUpdateView(CreateOrUpdateView):
    model = Determination
    template_name = 'determinations/determination_form.html'

    def get_object(self, queryset=None):
        return self.model.objects.get(submission=self.submission, author=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.submission = get_object_or_404(ApplicationSubmission, id=self.kwargs['submission_pk'])

        # TODO add proper permission
        # if not self.submission.phase.has_perm(request.user, 'add_determination') or \
        if not self.submission.has_permission_to_add_determination(request.user):
            raise PermissionDenied()

        if self.request.POST:
            return self.get(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        try:
            has_submitted_determination = not self.submission.determination.is_draft
        except ObjectDoesNotExist:
            has_submitted_determination = False

        return super().get_context_data(
            submission=self.submission,
            has_submitted_determination=has_submitted_determination,
            title="Update Determination draft" if self.object else 'Add Determination',
            **kwargs
        )

    def get_form_class(self):
        return get_form_for_stage(self.submission)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['submission'] = self.submission

        if self.object:
            kwargs['initial'] = self.object.determination_data
            kwargs['initial']['determination'] = self.object.determination

        return kwargs

    def get_success_url(self):
        return self.submission.get_absolute_url()


@method_decorator(staff_required, name='dispatch')
class DeterminationDetailView(DetailView):
    model = Determination

    def dispatch(self, request, *args, **kwargs):
        determination = self.get_object()

        if request.user != determination.submission.lead and not request.user.is_superuser:
            raise PermissionDenied

        if determination.is_draft:
            return HttpResponseRedirect(reverse_lazy('apply:determinations:form', args=(determination.submission.id,)))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        determination = self.get_object().determination
        form_used = get_form_for_stage(self.get_object().submission)
        determination_data = {}

        for name, field in form_used.base_fields.items():
            try:
                # Add titles which exist
                title = form_used.titles[field.group]
                determination_data.setdefault(title, [])
            except AttributeError:
                pass

            value = determination[name]
            try:
                choices = dict(field.choices)
            except AttributeError:
                pass
            else:
                # Update the stored value to the display value
                value = choices[int(value)]

            determination_data.setdefault(field.label, str(value))

        return super().get_context_data(
            determination_data=determination_data,
            **kwargs
        )