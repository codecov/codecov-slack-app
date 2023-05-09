from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

class TestHealth(APITestCase):
    def test_health(self):
        url = reverse("health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"Codecov Slack App is live!")