import factory

from opentech.apply.funds.tests.factories import ApplicationSubmissionFactory
from opentech.apply.users.tests.factories import StaffFactory

from ..models import Review
from ..views import get_form_for_stage


class ReviewDataFactory(factory.DictFactory):
    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        submission = kwargs.pop('submission')
        form = get_form_for_stage(submission)(request=None, submission=None)
        form_fields = {}
        for field_name, field in form.fields.items():
            form_fields[field_name] = 0

        form_fields.update(**kwargs)
        return super()._build(model_class, *args, **form_fields)


class ReviewFactory(factory.DjangoModelFactory):
    class Meta:
        model = Review

    submission = factory.SubFactory(ApplicationSubmissionFactory)
    author = factory.SubFactory(StaffFactory)
    review = factory.Dict({'submission': factory.SelfAttribute('..submission')}, dict_factory=ReviewDataFactory)
    is_draft = False
