from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from .models import UserProfile, Transaction
from rest_framework.authtoken.models import Token

class TransactionViewTestCase(APITestCase):
    def setUp(self):
        # Clean up any existing UserProfile data to avoid unique constraint violations
        UserProfile.objects.all().delete()

        # Create the user for the test (if it doesn't exist already)
        self.user = User.objects.create_user(username='testuser', password='password')
        self.receiver = User.objects.create_user(username='testreceiver', password='password')

        # Create UserProfile objects for both the sender and receiver users
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user, defaults={'balance': 100.00})
        self.receiver_profile, created = UserProfile.objects.get_or_create(user=self.receiver, defaults={'balance': 100.00})

        # Generate a token for authentication
        self.token = Token.objects.create(user=self.user)

        # Define the transaction creation URL (ensure this matches your actual URL path)
        self.url = '/transactions/create/'  # Update with your actual URL path

    def test_transaction_creation(self):
        # Example test for creating a transaction
        # Create transaction data
        transaction_data = {
            'receiver_id': self.receiver.id,  # Pass the receiver's ID (not username)
            'amount': 50.00,  # Amount to be transferred
        }

        # Make the API request to create a transaction
        response = self.client.post(
            self.url,
            data=transaction_data,
            HTTP_AUTHORIZATION=f'Token {self.token.key}'  # Attach token for authentication
        )

        # Assert that the status code is 201 (created)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the sender's balance has been updated correctly
        self.user_profile.refresh_from_db()  # Reload the user's profile from the database
        self.assertEqual(self.user_profile.balance, 50.00)  # 100 - 50 = 50

        # Check that the receiver's balance has been updated correctly
        self.receiver_profile.refresh_from_db()
        self.assertEqual(self.receiver_profile.balance, 150.00)  # 100 + 50 = 150

        # Check that a transaction record was created
        transaction = Transaction.objects.last()
        self.assertEqual(transaction.sender, self.user)
        self.assertEqual(transaction.receiver, self.receiver)
        self.assertEqual(transaction.amount, 50.00)
        self.assertEqual(transaction.status, 'completed')  # Assuming 'completed' is the default status

        # Optionally: Check if response data includes the transaction information
        self.assertIn('amount', response.data)
        self.assertEqual(response.data['amount'], 50.00)
