from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse


class CustomAdminSecurityTestCase(TestCase):
    def setUp(self):
        self.regular_user = User.objects.create_user(
            username='regularfan',
            password='regularpassword123',
            is_staff=False
        )
        self.staff_user = User.objects.create_user(
            username='staffadmin',
            password='adminpassword123',
            is_staff=True
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse('customadmin:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('customadmin:login'), response.url)

    def test_non_staff_user_redirected_from_dashboard(self):
        self.client.login(username='regularfan', password='regularpassword123')
        response = self.client.get(reverse('customadmin:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('customadmin:login'), response.url)

    def test_staff_user_can_access_dashboard(self):
        self.client.login(username='staffadmin', password='adminpassword123')
        response = self.client.get(reverse('customadmin:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff Dashboard')
        self.assertContains(response, 'staffadmin')

    def test_staff_login_post_success(self):
        response = self.client.post(reverse('customadmin:login'), {
            'username': 'staffadmin',
            'password': 'adminpassword123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff Dashboard')

    def test_non_staff_login_post_denied(self):
        response = self.client.post(reverse('customadmin:login'), {
            'username': 'regularfan',
            'password': 'regularpassword123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff privileges required')
