from django.db import models
from django_cte import CTEManager


class Apple(models.Model):
    name = models.CharField('名前', max_length=20)
    parent = models.ForeignKey('self',
                               on_delete=models.SET_NULL,
                               null=True,
                               blank=True)

    objects = CTEManager()

    class Meta:
        db_table = 'apple'
