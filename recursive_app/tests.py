from django.db import connection
from django.db.models import Value, IntegerField
from django.test import TestCase, override_settings
from django_cte import With

from recursive_app.factories import AppleFactory
from recursive_app.models import Apple


@override_settings(DEBUG=True)
class TestRecursive(TestCase):
    def setUp(self):
        toko = AppleFactory(name='東光')
        senshu = AppleFactory(name='千秋', parent=toko)
        shinano_gold = AppleFactory(name='シナノゴールド', parent=senshu)
        AppleFactory(name='奥州ロマン', parent=shinano_gold)
        AppleFactory(name='秋映', parent=senshu)

        kokko = AppleFactory(name='国光')
        fuji = AppleFactory(name='フジ', parent=kokko)
        AppleFactory(name='シナノスイート', parent=fuji)

    def assertCte(self, actual):
        # 件数
        self.assertEqual(len(actual), 3)

        # シナノゴールド自身があること
        own = actual[0]
        self.assertEqual(own.node, 0)
        self.assertEqual(own.name, 'シナノゴールド')

        # シナノゴールドの親(千秋)
        parent = actual[1]
        self.assertEqual(parent.node, 1)
        self.assertEqual(parent.name, '千秋')

        # 千秋の親(東光)
        grandparent = actual[2]
        self.assertEqual(grandparent.node, 2)
        self.assertEqual(grandparent.name, '東光')

    def print_query(self):
        print('=' * 30)
        for query in connection.queries:
            print(query['sql'])

    def test_1_raw_sql(self):
        shinano_gold = Apple.objects.get(name='シナノゴールド')

        apples = Apple.objects.raw(
            """
            WITH RECURSIVE tree
                (node, id, name, parent_id)
            AS (
                    SELECT 0 AS node, base.id, base.name, base.parent_id
                    FROM apple AS base
                    WHERE base.id = %s
                UNION ALL
                    SELECT tree.node + 1 AS node, 
                           apple.id,
                           apple.name,
                           apple.parent_id
                    FROM apple
                        INNER JOIN tree
                            ON apple.id = tree.parent_id
            ) SELECT * 
              FROM tree
              ORDER BY node;
            """
            , [shinano_gold.pk])

        self.assertCte(apples)
        self.print_query()

    def test_2_django_cte(self):
        def make_cte(cte):
            shinano_gold = Apple.objects.get(name='シナノゴールド')

            return Apple.objects.filter(
                id=shinano_gold.pk
            ).annotate(
                node=Value(0, output_field=IntegerField()),
            ).union(
                cte.join(Apple, id=cte.col.parent_id)
                   .annotate(node=cte.col.node + Value(1, output_field=IntegerField())),
                all=True,
            )

        cte = With.recursive(make_cte)

        apples = (
            cte.queryset()
               .with_cte(cte)
               .annotate(node=cte.col.node)
            .order_by('node')
        )

        self.assertCte(apples)
        self.print_query()

    def test_3_django_cte_root(self):
        def make_cte(cte):
            kokko = Apple.objects.get(name='国光')

            return Apple.objects.filter(
                id=kokko.pk
            ).annotate(
                node=Value(0, output_field=IntegerField()),
            ).union(
                cte.join(Apple, id=cte.col.parent_id)
                    .annotate(node=cte.col.node + Value(1, output_field=IntegerField())),
                all=True,
                    )

        cte = With.recursive(make_cte)

        apples = (
            cte.queryset()
                .with_cte(cte)
                .annotate(node=cte.col.node)
                .order_by('node')
        )

        self.assertEqual(len(apples), 1)
        apple = apples.get()
        self.assertEqual(apple.node, 0)
        self.assertEqual(apple.name, '国光')

        self.print_query()

    def test_4_cte_to_dict(self):
        def make_cte(cte):
            shinano_gold = Apple.objects.get(name='シナノゴールド')

            return Apple.objects.filter(
                id=shinano_gold.pk
            ).values(
                'id',
                'parent',
                'name',
                node=Value(0, output_field=IntegerField()),
            ).union(
                cte.join(Apple, id=cte.col.parent_id)
                    .values(
                        'id',
                        'parent',
                        'name',
                        node=cte.col.node + Value(1, output_field=IntegerField())),
                all=True,
            )

        cte = With.recursive(make_cte)

        apples = (
            cte.queryset()
                .with_cte(cte)
                .annotate(node=cte.col.node)
                .order_by('node')
        )

        # 途中で values() を使って dict 化しているため、共通の assertCte() は使えない
        # 件数
        self.assertEqual(len(apples), 3)

        # シナノゴールド自身があること
        own = apples[0]
        self.assertEqual(own['node'], 0)
        self.assertEqual(own['name'], 'シナノゴールド')

        # シナノゴールドの親(千秋)
        own = apples[1]
        self.assertEqual(own['node'], 1)
        self.assertEqual(own['name'], '千秋')

        # 千秋の親(東光)
        own = apples[2]
        self.assertEqual(own['node'], 2)
        self.assertEqual(own['name'], '東光')

        self.print_query()
