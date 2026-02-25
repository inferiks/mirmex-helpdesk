from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Equipment, TicketHistory, Tickets


# ---------------------------------------------------------------------------
# Equipment model
# ---------------------------------------------------------------------------

class EquipmentModelTest(TestCase):
    def setUp(self):
        self.equipment = Equipment.objects.create(
            serial='SN-001',
            model='HP LaserJet Pro M404',
            location='Офис 101',
            status=Equipment.STATUS_IN_USE,
        )

    def test_str_contains_model_and_serial(self):
        """__str__ должен содержать модель и серийный номер"""
        result = str(self.equipment)
        self.assertIn('HP LaserJet Pro M404', result)
        self.assertIn('SN-001', result)

    def test_default_status_is_in_use(self):
        """Статус по умолчанию — «В использовании»"""
        eq = Equipment.objects.create(serial='SN-002', model='Dell Monitor')
        self.assertEqual(eq.status, Equipment.STATUS_IN_USE)


# ---------------------------------------------------------------------------
# Tickets model
# ---------------------------------------------------------------------------

class TicketsModelTest(TestCase):
    def setUp(self):
        self.reporter = User.objects.create_user(
            username='reporter_test', password='pass123'
        )
        self.technician = User.objects.create_user(
            username='tech_test', password='pass123'
        )
        tech_group, _ = Group.objects.get_or_create(name='technician')
        self.technician.groups.add(tech_group)

        self.ticket = Tickets.objects.create(
            title='Не работает принтер',
            description='Принтер не печатает при нажатии кнопки печати',
            reporter=self.reporter,
            priority=Tickets.PRIORITY_HIGH,
            category=Tickets.CATEGORY_PRINTER,
        )

    def test_str_contains_title_and_pk(self):
        """__str__ должен содержать заголовок и номер заявки"""
        result = str(self.ticket)
        self.assertIn('Не работает принтер', result)
        self.assertIn(f'#{self.ticket.pk}', result)

    def test_default_status_is_new(self):
        """Новая заявка имеет статус 'new'"""
        self.assertEqual(self.ticket.status, Tickets.STATUS_NEW)

    def test_is_overdue_returns_true_when_past_due(self):
        """is_overdue() возвращает True, когда срок истёк"""
        self.ticket.due_date = timezone.now() - timedelta(hours=1)
        self.ticket.save()
        self.assertTrue(self.ticket.is_overdue())

    def test_is_overdue_returns_false_for_closed_ticket(self):
        """is_overdue() возвращает False для закрытой заявки, даже если срок истёк"""
        self.ticket.due_date = timezone.now() - timedelta(hours=1)
        self.ticket.status = Tickets.STATUS_CLOSED
        self.ticket.save()
        self.assertFalse(self.ticket.is_overdue())

    def test_is_overdue_returns_false_when_due_date_in_future(self):
        """is_overdue() возвращает False, когда срок ещё не истёк"""
        self.ticket.due_date = timezone.now() + timedelta(hours=24)
        self.ticket.save()
        self.assertFalse(self.ticket.is_overdue())

    def test_resolution_hours_returns_none_for_open_ticket(self):
        """resolution_hours() возвращает None для открытой заявки"""
        self.assertIsNone(self.ticket.resolution_hours())

    def test_resolution_hours_calculates_correctly(self):
        """resolution_hours() правильно вычисляет время решения"""
        self.ticket.closed_at = self.ticket.created_at + timedelta(hours=4)
        self.ticket.save()
        self.assertAlmostEqual(self.ticket.resolution_hours(), 4.0, places=0)

    def test_change_status_valid_transition_new_to_closed(self):
        """Переход new → closed допустим"""
        self.ticket.change_status(Tickets.STATUS_CLOSED, changed_by=self.reporter)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Tickets.STATUS_CLOSED)

    def test_change_status_invalid_transition_raises_validation_error(self):
        """Переход closed → in_progress недопустим и вызывает ValidationError"""
        self.ticket.status = Tickets.STATUS_CLOSED
        self.ticket.save()
        with self.assertRaises(ValidationError):
            self.ticket.change_status(Tickets.STATUS_IN_PROGRESS)

    def test_history_created_on_status_change(self):
        """При изменении статуса создаётся запись в истории"""
        self.ticket.change_status(Tickets.STATUS_CLOSED, changed_by=self.reporter)
        history = TicketHistory.objects.filter(
            ticket=self.ticket,
            action=TicketHistory.ACTION_STATUS_CHANGED,
        )
        self.assertTrue(history.exists())

    def test_assign_sets_technician_and_status(self):
        """assign() назначает техника и переводит в статус 'assigned'"""
        self.ticket.assign(self.technician, changed_by=self.reporter)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Tickets.STATUS_ASSIGNED)
        self.assertEqual(self.ticket.technician, self.technician)

    def test_close_sets_closed_at(self):
        """close() устанавливает closed_at"""
        self.ticket.close(changed_by=self.reporter)
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.closed_at)


# ---------------------------------------------------------------------------
# View access control
# ---------------------------------------------------------------------------

class TicketViewsAccessTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.reporter = User.objects.create_user(
            username='reporter_v', password='pass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin_v', password='pass123'
        )
        self.dispatcher = User.objects.create_user(
            username='disp_v', password='pass123'
        )
        disp_group, _ = Group.objects.get_or_create(name='dispatcher')
        self.dispatcher.groups.add(disp_group)

        self.technician = User.objects.create_user(
            username='tech_v', password='pass123'
        )
        tech_group, _ = Group.objects.get_or_create(name='technician')
        self.technician.groups.add(tech_group)

        self.ticket = Tickets.objects.create(
            title='Test ticket',
            description='Test description',
            reporter=self.reporter,
        )

    # -- Authentication ----------------------------------------------------

    def test_ticket_list_redirects_anonymous_user(self):
        """Неавторизованный пользователь перенаправляется на страницу входа"""
        response = self.client.get(reverse('ticket_list'))
        self.assertIn(response.status_code, [301, 302])
        self.assertIn('/accounts/login/', response['Location'])

    def test_ticket_list_accessible_to_reporter(self):
        """Авторизованный пользователь может открыть список заявок"""
        self.client.login(username='reporter_v', password='pass123')
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 200)

    # -- Role-based access -------------------------------------------------

    def test_reports_returns_403_for_plain_user(self):
        """Страница аналитики недоступна обычному пользователю"""
        self.client.login(username='reporter_v', password='pass123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 403)

    def test_reports_accessible_for_dispatcher(self):
        """Диспетчер может просматривать аналитику"""
        self.client.login(username='disp_v', password='pass123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)

    def test_reports_accessible_for_admin(self):
        """Администратор может просматривать аналитику"""
        self.client.login(username='admin_v', password='pass123')
        response = self.client.get(reverse('reports'))
        self.assertEqual(response.status_code, 200)

    def test_user_list_returns_403_for_reporter(self):
        """Список пользователей недоступен обычному пользователю"""
        self.client.login(username='reporter_v', password='pass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 403)

    def test_user_list_returns_403_for_technician(self):
        """Список пользователей недоступен технику"""
        self.client.login(username='tech_v', password='pass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 403)

    def test_user_list_accessible_for_admin(self):
        """Администратор может управлять пользователями"""
        self.client.login(username='admin_v', password='pass123')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)

    def test_equipment_create_forbidden_for_reporter(self):
        """Создание оборудования недоступно обычному пользователю"""
        self.client.login(username='reporter_v', password='pass123')
        response = self.client.get(reverse('equipment_create'))
        self.assertEqual(response.status_code, 403)

    def test_ticket_detail_returns_404_for_other_user(self):
        """Чужая заявка недоступна (другой reporter видит 404)"""
        other_user = User.objects.create_user(
            username='other_reporter', password='pass123'
        )
        self.client.login(username='other_reporter', password='pass123')
        response = self.client.get(
            reverse('ticket_detail', kwargs={'pk': self.ticket.pk})
        )
        self.assertEqual(response.status_code, 404)
