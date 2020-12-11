import factory

from recursive_app.models import Apple


class AppleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Apple
