from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Справочники (Directories)
# ---------------------------------------------------------------------------

class Nomenclature(models.Model):
    """Справочник Номенклатура — иерархический (услуги/товары компании)."""
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Группа'
    )
    name = models.CharField(max_length=255, verbose_name='Наименование')
    is_group = models.BooleanField(default=False, verbose_name='Это группа')
    description = models.TextField(blank=True, verbose_name='Описание')
    code = models.CharField(max_length=50, blank=True, verbose_name='Код')

    class Meta:
        verbose_name = 'Номенклатура'
        verbose_name_plural = 'Номенклатура'
        ordering = ['name']

    def __str__(self):
        prefix = '[Группа] ' if self.is_group else ''
        return f"{prefix}{self.name}"

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} / {self.name}"
        return self.name


class Client(models.Model):
    """Справочник Клиенты с сегментами."""
    name = models.CharField(max_length=255, verbose_name='Наименование')
    contact_person = models.CharField(max_length=255, blank=True, verbose_name='Контактное лицо')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    address = models.CharField(max_length=500, blank=True, verbose_name='Адрес')

    # Потребительские сегменты (Boolean-реквизиты)
    segment_b2b = models.BooleanField(default=False, verbose_name='B2B')
    segment_krasnodar = models.BooleanField(default=False, verbose_name='г. Краснодар')
    segment_rto = models.BooleanField(default=False, verbose_name='РТО')
    segment_small_business = models.BooleanField(default=False, verbose_name='Малый бизнес')
    segment_medium_business = models.BooleanField(default=False, verbose_name='Средний бизнес')
    segment_b2g = models.BooleanField(default=False, verbose_name='B2G (госсектор)')

    note = models.TextField(
        blank=True,
        verbose_name='Примечание',
        help_text='Ссылка на web-ресурс с информацией о клиенте'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_segments_display(self):
        segments = []
        if self.segment_b2b:
            segments.append('B2B')
        if self.segment_krasnodar:
            segments.append('г. Краснодар')
        if self.segment_rto:
            segments.append('РТО')
        if self.segment_small_business:
            segments.append('Малый бизнес')
        if self.segment_medium_business:
            segments.append('Средний бизнес')
        if self.segment_b2g:
            segments.append('B2G')
        return '; '.join(segments) if segments else '—'


class Competitor(models.Model):
    """Справочник Конкуренты."""
    name = models.CharField(max_length=255, verbose_name='Наименование')
    address = models.CharField(max_length=500, blank=True, verbose_name='Адрес')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Телефон')
    website = models.URLField(blank=True, verbose_name='Сайт')
    note = models.TextField(
        blank=True,
        verbose_name='Примечание',
        help_text='Ссылка на web-ресурс, на котором размещена информация об организации'
    )

    class Meta:
        verbose_name = 'Конкурент'
        verbose_name_plural = 'Конкуренты'
        ordering = ['name']

    def __str__(self):
        return self.name


class CostItem(models.Model):
    """Справочник Статьи затрат — иерархический (вид иерархии: иерархия элементов)."""
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская группа'
    )
    name = models.CharField(max_length=255, verbose_name='Наименование')
    is_group = models.BooleanField(default=False, verbose_name='Это группа')
    code = models.CharField(max_length=20, blank=True, verbose_name='Код')

    class Meta:
        verbose_name = 'Статья затрат'
        verbose_name_plural = 'Статьи затрат'
        ordering = ['code', 'name']

    def __str__(self):
        prefix = '[Группа] ' if self.is_group else ''
        return f"{prefix}{self.name}"

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} → {self.name}"
        return self.name


class Counterparty(models.Model):
    """Справочник Контрагенты (поставщики/арендодатели)."""
    name = models.CharField(max_length=255, verbose_name='Наименование')
    address = models.CharField(max_length=500, blank=True, verbose_name='Адрес')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    inn = models.CharField(max_length=12, blank=True, verbose_name='ИНН')
    website = models.URLField(blank=True, verbose_name='Сайт')

    class Meta:
        verbose_name = 'Контрагент'
        verbose_name_plural = 'Контрагенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class ValueProposition(models.Model):
    """Ценностное предложение (для разреза в расчёте капитальных затрат)."""
    name = models.CharField(max_length=255, verbose_name='Наименование')
    description = models.TextField(blank=True, verbose_name='Описание')
    target_segment = models.CharField(max_length=255, blank=True, verbose_name='Целевой сегмент')

    class Meta:
        verbose_name = 'Ценностное предложение'
        verbose_name_plural = 'Ценностные предложения'
        ordering = ['name']

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Перечисление ВидыЗатрат
# ---------------------------------------------------------------------------

COST_TYPE_ACQUISITION = 'acquisition'
COST_TYPE_RENT = 'rent'

COST_TYPE_CHOICES = [
    (COST_TYPE_ACQUISITION, 'Приобретение'),
    (COST_TYPE_RENT, 'Аренда'),
]


# ---------------------------------------------------------------------------
# Документ «Цены контрагентов»
# ---------------------------------------------------------------------------

class CounterpartyPricesDocument(models.Model):
    """Документ для ввода цен контрагентов."""
    number = models.CharField(max_length=20, verbose_name='Номер документа', blank=True)
    date = models.DateField(default=timezone.now, verbose_name='Дата')
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        verbose_name='Контрагент',
        related_name='price_documents'
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Цены контрагентов'
        verbose_name_plural = 'Цены контрагентов (документы)'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Цены контрагентов №{self.number or self.pk} от {self.date.strftime('%d.%m.%Y')} ({self.counterparty})"

    def save(self, *args, **kwargs):
        if not self.number:
            super().save(*args, **kwargs)
            self.number = str(self.pk).zfill(6)
            CounterpartyPricesDocument.objects.filter(pk=self.pk).update(number=self.number)
        else:
            super().save(*args, **kwargs)

    def post_document(self):
        """Провести документ — записать данные в регистр."""
        for item in self.items.all():
            CounterpartyPricesRegister.objects.update_or_create(
                counterparty=self.counterparty,
                cost_item=item.cost_item,
                cost_type=item.cost_type,
                defaults={
                    'price': item.price,
                    'date': self.date,
                    'document': self,
                }
            )


class CounterpartyPricesItem(models.Model):
    """Строка табличной части документа «Цены контрагентов»."""
    document = models.ForeignKey(
        CounterpartyPricesDocument,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Документ'
    )
    cost_item = models.ForeignKey(
        CostItem,
        on_delete=models.PROTECT,
        verbose_name='Статья затрат'
    )
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        default=COST_TYPE_ACQUISITION,
        verbose_name='Вид затрат'
    )
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Цена', default=0)

    class Meta:
        verbose_name = 'Строка цен контрагента'
        verbose_name_plural = 'Строки цен контрагента'

    def __str__(self):
        return f"{self.cost_item} — {self.get_cost_type_display()}: {self.price}"


# ---------------------------------------------------------------------------
# Регистр сведений «Цены контрагентов»
# ---------------------------------------------------------------------------

class CounterpartyPricesRegister(models.Model):
    """Регистр сведений для хранения актуальных цен контрагентов."""
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.CASCADE,
        verbose_name='Контрагент'
    )
    cost_item = models.ForeignKey(
        CostItem,
        on_delete=models.CASCADE,
        verbose_name='Статья затрат'
    )
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        verbose_name='Вид затрат'
    )
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Цена')
    date = models.DateField(verbose_name='Дата актуальности')
    document = models.ForeignKey(
        CounterpartyPricesDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Документ-источник'
    )

    class Meta:
        verbose_name = 'Цена контрагента (регистр)'
        verbose_name_plural = 'Цены контрагентов (регистр)'
        unique_together = [('counterparty', 'cost_item', 'cost_type')]
        ordering = ['counterparty', 'cost_item']

    def __str__(self):
        return f"{self.counterparty} | {self.cost_item} | {self.get_cost_type_display()} | {self.price} ₽"


# ---------------------------------------------------------------------------
# Документ «Расчёт капитальных затрат»
# ---------------------------------------------------------------------------

class CapitalExpensesDocument(models.Model):
    """Документ для расчёта капитальных затрат по ценностному предложению."""
    number = models.CharField(max_length=20, blank=True, verbose_name='Номер документа')
    date = models.DateField(default=timezone.now, verbose_name='Дата')
    value_proposition = models.ForeignKey(
        ValueProposition,
        on_delete=models.PROTECT,
        verbose_name='Ценностное предложение',
        related_name='capital_expenses'
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Расчёт капитальных затрат'
        verbose_name_plural = 'Расчёты капитальных затрат'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"РКЗ №{self.number or self.pk} от {self.date.strftime('%d.%m.%Y')} ({self.value_proposition})"

    def save(self, *args, **kwargs):
        if not self.number:
            super().save(*args, **kwargs)
            self.number = str(self.pk).zfill(6)
            CapitalExpensesDocument.objects.filter(pk=self.pk).update(number=self.number)
        else:
            super().save(*args, **kwargs)

    def get_total(self):
        from django.db.models import Sum
        result = self.items.aggregate(total=Sum('total'))['total']
        return result or 0

    def post_document(self):
        """Провести документ — записать в регистр расчёта."""
        CapitalExpensesRegister.objects.filter(document=self).delete()
        for item in self.items.all():
            CapitalExpensesRegister.objects.create(
                document=self,
                value_proposition=self.value_proposition,
                cost_item=item.cost_item,
                cost_type=item.cost_type,
                counterparty=item.counterparty,
                price=item.price,
                quantity=item.quantity,
                total=item.total,
            )


class CapitalExpensesItem(models.Model):
    """Строка табличной части документа «Расчёт капитальных затрат»."""
    document = models.ForeignKey(
        CapitalExpensesDocument,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Документ'
    )
    cost_item = models.ForeignKey(
        CostItem,
        on_delete=models.PROTECT,
        verbose_name='Статья затрат'
    )
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        default=COST_TYPE_ACQUISITION,
        verbose_name='Вид затрат'
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Контрагент'
    )
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Цена')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name='Количество')
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма')

    class Meta:
        verbose_name = 'Строка расчёта затрат'
        verbose_name_plural = 'Строки расчёта затрат'

    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cost_item} — {self.get_cost_type_display()}: {self.total} ₽"


# ---------------------------------------------------------------------------
# Регистр «Расчёт капитальных затрат»
# ---------------------------------------------------------------------------

class CapitalExpensesRegister(models.Model):
    """Регистр накопления для хранения рассчитанных капитальных затрат."""
    document = models.ForeignKey(
        CapitalExpensesDocument,
        on_delete=models.CASCADE,
        verbose_name='Документ'
    )
    value_proposition = models.ForeignKey(
        ValueProposition,
        on_delete=models.CASCADE,
        verbose_name='Ценностное предложение'
    )
    cost_item = models.ForeignKey(
        CostItem,
        on_delete=models.CASCADE,
        verbose_name='Статья затрат'
    )
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        verbose_name='Вид затрат'
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Контрагент'
    )
    price = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Цена')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Количество')
    total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')

    class Meta:
        verbose_name = 'Запись регистра затрат'
        verbose_name_plural = 'Регистр капитальных затрат'
        ordering = ['cost_item']

    def __str__(self):
        return f"{self.value_proposition} | {self.cost_item} | {self.total} ₽"
