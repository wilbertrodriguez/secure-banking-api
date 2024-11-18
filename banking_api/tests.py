from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TransactionTestCase
from .models import UserProfile, Transaction
from django.db import connection

class TransactionViewTestCase(TransactionTestCase):
    def setUp(self):
        # Ensure database is clean before each test
        print("Cleaning up the database before test...")
        self.clean_database()

        # Create users for testing
        print("Creating users for testing...")
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.receiver = User.objects.create_user(username='testreceiver', email='testreceiver@example.com', password='password')

        # Create user profiles for the users
        print("Creating user profiles...")
        #self.user_profile = UserProfile.objects.create(user=self.user, balance=100.00)
        #self.receiver_profile = UserProfile.objects.create(user=self.receiver, balance=100.00)
        UserProfile.objects.create(user=self.user, balance=100.00)
        UserProfile.objects.create(user=self.receiver, balance=100.00)

        # Generate JWT token for the user
        print("Creating JWT token for the user...")
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)  # Get the access token

        # Initialize APIClient
        print("Initializing API client...")
        self.client = APIClient()

        # Set authorization header for the user with the JWT token
        print("Setting authorization header for the user...")
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Define the URL for transaction creation
        self.url = '/api/transactions/'  # Ensure this is the correct URL
        print(f"Transaction creation URL set to: {self.url}")

    def tearDown(self):
        # Clean up after each test
        print("Cleaning up after test...")
        self.clean_database()

        # Reset the database and make sure auto-increment fields are reset
        print("Closing database connection...")
        connection.close()

    def clean_database(self):
        # Explicitly delete the users and related profiles to ensure no conflicts in the test
        print("Deleting all user profiles, users, and tokens...")
        UserProfile.objects.all().delete()
        User.objects.all().delete()

    def test_transaction_creation(self):
        print("Starting the test for transaction creation.")

        # Prepare the transaction data (use 'receiver' instead of 'receiver_id')
        transaction_data = {
            'receiver_id': self.receiver.id,  # Correct field name based on the model
            'amount': 50.00,
        }
        print(f"Transaction data prepared: {transaction_data}")

        # Send the POST request to create a transaction
        print("Sending POST request to create a transaction...")
        response = self.client.post(self.url, 
                                    data=transaction_data,
                                    format='json')

        # Print the response for debugging
        print(f"Response content: {response.content}")

        # Verify the response status code
        print(f"Checking if response status code is {status.HTTP_201_CREATED}...")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        print("Response status code is correct.")

        # Check balances after the transaction
        print("Refreshing user profile to check updated balance...")
        self.user_profile.refresh_from_db()
        print(f"User balance after transaction: {self.user_profile.balance}")
        self.assertEqual(self.user_profile.balance, 50.00)

        print("Refreshing receiver profile to check updated balance...")
        self.receiver_profile.refresh_from_db()
        print(f"Receiver balance after transaction: {self.receiver_profile.balance}")
        self.assertEqual(self.receiver_profile.balance, 150.00)

        # Verify the transaction was created correctly
        print("Verifying if the transaction was created in the database...")
        transaction = Transaction.objects.last()
        print(f"Transaction details: {transaction}")

        print("Checking that transaction sender is correct...")
        self.assertEqual(transaction.sender, self.user)

        print("Checking that transaction receiver is correct...")
        self.assertEqual(transaction.receiver, self.receiver)

        print("Checking that transaction amount is correct...")
        self.assertEqual(transaction.amount, 50.00)

        print("Checking that transaction status is 'completed'...")
        self.assertEqual(transaction.status, 'completed')

        print("Transaction test completed.")
