from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_returns_200_and_json(self):
        """
        Verify /healthz/ executes fast database query & cache check,
        returning HTTP 200 with status ok and connected flags.
        """
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("database"), "connected")
        self.assertEqual(data.get("cache"), "connected")

