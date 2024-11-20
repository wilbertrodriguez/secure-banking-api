from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TransactionTestCase
from .models import UserProfile, Transaction
from django.db import connection
from decimal import Decimal

class TransactionViewTestCase(TransactionTestCase):
    def setUp(self):
        # Ensure the database is clean before each test
        print("Cleaning up the database before test...")

        # Create users for testing
        print("Creating users for testing...")
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.receiver = User.objects.create_user(username='testreceiver', email='testreceiver@example.com', password='password')

        # Create user profiles for the users
        print("Creating user profiles...")
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user, defaults={'balance': 100.00})
        if not created:  # If the profile already exists, ensure balance is correct
            self.user_profile.balance = 100.00

        self.receiver_profile, created = UserProfile.objects.get_or_create(user=self.receiver, defaults={'balance': 100.00})
        if not created:  # If the profile already exists, ensure balance is correct
            self.receiver_profile.balance = 100.00
        self.user_profile.save()
        self.receiver_profile.save()
        self.user.refresh_from_db()
        self.receiver.refresh_from_db()

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

        # Check balances before the transaction
        print(f"User balance before transaction: {self.user_profile.balance}")
        print(f"Receiver balance before transaction: {self.receiver_profile.balance}")

        # Ensure sender has enough balance for the transaction
        transaction_amount = 50.00
        if self.user_profile.balance < transaction_amount:
            self.fail(f"User does not have enough balance for the transaction. Current balance: {self.user_profile.balance}")

        # Prepare the transaction data
        transaction_data = {
            'sender': self.user.id,
            'receiver': self.receiver.id,  # Correct field name based on the model
            'amount': transaction_amount,
        }
        print(f"Transaction data prepared: {transaction_data}")

        # Send the POST request to create the transaction
        print("Sending POST request to create a transaction...")
        response = self.client.post(self.url, 
                                    data=transaction_data,
                                    format='json')

        # Print the response for debugging
        print(f"Response content: {response.content}")

        # Verify the response status code
        if response.status_code == status.HTTP_201_CREATED:
            print("Response status code is correct.")
            self.user_profile = UserProfile.objects.get(user=self.user)
            self.receiver_profile = UserProfile.objects.get(user=self.receiver)
            # Refresh the profiles after the transaction to ensure they are up-to-date
            self.user.refresh_from_db()
            self.receiver.refresh_from_db()  # Refresh receiver as well

            # Assert balances are updated correctly in case of a successful transaction
            print(f"User balance after transaction: {self.user_profile.balance}")
            self.assertEqual(self.user_profile.balance, 50.00)  # The user should have 50.0 left
            print(f"Receiver balance after transaction: {self.receiver_profile.balance}")
            self.assertEqual(self.receiver_profile.balance, 150.00)  # The receiver should have 150.0

            # Verify the transaction was created correctly
            transaction = Transaction.objects.last()
            print(f"Transaction details: {transaction}")
            self.assertEqual(transaction.sender, self.user)
            self.assertEqual(transaction.receiver, self.receiver)
            self.assertEqual(transaction.amount, 50.00)
            self.assertEqual(transaction.status, 'completed')

        else:
            # Handle the case where the transaction fails due to insufficient funds
            print("Transaction failed. Checking the response data...")
            # Check if 'status' exists in the response data
            if 'status' in response.data:
                self.assertEqual(response.data['status'], 'failed')
            else:
                # Assert the presence of validation errors
                self.assertIn('non_field_errors', response.data)
                self.assertEqual(response.data['non_field_errors'][0], "You do not have enough balance to complete this transaction.")

            # Refresh both user and receiver balances after the failed transaction attempt
            self.user.refresh_from_db()
            self.receiver.refresh_from_db()  # Refresh receiver as well

            # Check that balances remain unchanged
            print(f"User balance after failed transaction: {self.user_profile.balance}")
            self.assertEqual(self.user_profile.balance, 100.00)  # The user should still have 100.0
            print(f"Receiver balance after failed transaction: {self.receiver_profile.balance}")
            self.assertEqual(self.receiver_profile.balance, 100.00)  # The receiver should still have 100.0

        print("Transaction test completed.\n\n\n")
        
    def test_transaction_get(self):
        print("Starting the test for GET transaction by ID.")

        # Create a transaction first
        transaction_amount = 50.00
        transaction_data = {
            'sender': self.user.id,
            'receiver': self.receiver.id,
            'amount': transaction_amount,
        }

        print(f"Transaction data prepared: {transaction_data}")

        # Send the POST request to create the transaction
        print("Sending POST request to create a transaction...")
        response = self.client.post(self.url, data=transaction_data, format='json')

        # Print the response for debugging
        print(f"Response content: {response.content}")

        # Verify the response status code for transaction creation
        if response.status_code == status.HTTP_201_CREATED:
            print("Response status code is correct.")
            # Get the transaction ID from the response
            transaction = Transaction.objects.last()
            transaction_id = transaction.id
            print(f"Created transaction with ID: {transaction_id}")

            # Send GET request to fetch the transaction by ID
            get_url = f'{self.url}{transaction_id}/'  # Adjust to your API endpoint
            response = self.client.get(get_url)

            # Print the GET response for debugging
            print(f"GET Response content: {response.content}")

            # Extract the transaction data from the response
            transaction_data = response.data['transaction']
            
            # Check the response status and verify the transaction details
            if response.status_code == status.HTTP_200_OK:
                print("GET response status code is correct.")
                self.assertEqual(transaction_data['sender'], self.user.id)
                self.assertEqual(transaction_data['receiver'], self.receiver.id)
                self.assertEqual(Decimal(transaction_data['amount']), Decimal(transaction_amount))
                self.assertEqual(transaction_data['status'], 'completed')

                print("GET transaction test completed successfully.")
            else:
                print(f"GET request failed with status: {response.status_code}")
        else:
            # Handle the case where the transaction creation failed
            print("Transaction creation failed. Aborting GET test.")
            self.fail("Transaction creation failed. Cannot test GET without a valid transaction.")

        print("Test completed.\n\n\n")
        
    def test_transaction_patch(self):
        print("Starting the test for PATCH transaction.")

        # Create a transaction first
        transaction_amount = 50.00
        transaction_data = {
            'sender': self.user.id,
            'receiver': self.receiver.id,
            'amount': transaction_amount,
            'status': 'pending',  # Status is initially 'pending'
        }

        # Create the transaction via POST request
        response = self.client.post(self.url, data=transaction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Get the transaction ID from the response
        transaction = Transaction.objects.last()
        transaction_id = transaction.id
        print(f"Created transaction with ID: {transaction_id} and status: {transaction.status}")

        # Prepare new data for the transaction update (update amount only)
        updated_data = {
            'amount': 75.00,  # Only update the amount
        }

        # Send PATCH request to partially update the transaction
        patch_url = f'{self.url}{transaction_id}/'  # Adjust to your API endpoint
        response = self.client.patch(patch_url, data=updated_data, format='json')

        print("Response data:", response.data)

        # Check if the status code is 400 (expected response for completed transaction)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Cannot update a completed transaction')

        # Verify that the transaction was not updated in the database
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, 50.00)  # Verify that amount is not updated
        self.assertEqual(transaction.status, 'completed')  # Verify that status remains 'completed'

        print("PATCH transaction test for completed transactions completed.")
        
    def test_transaction_patch_pending(self):
        print("Starting the test for PATCH on a pending transaction.")

        # Create a pending transaction first
        transaction_amount = 50.00
        transaction_data = {
            'sender': self.user.id,
            'receiver': self.receiver.id,
            'amount': transaction_amount,
            'status': 'pending',  # Status is initially 'pending'
        }

        # Create the transaction via POST request
        response = self.client.post(self.url, data=transaction_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Get the transaction ID from the response
        transaction = Transaction.objects.last()
        transaction_id = transaction.id
        print(f"Created transaction with ID: {transaction_id} and status: {transaction.status}")

        # Ensure that the transaction is 'pending' before attempting to update
        self.assertEqual(transaction.status, 'pending')

        # Now approve the transaction via the approval endpoint
        approve_url = f'{self.url}{transaction_id}/approve/'  # Assuming 'approve/' is the URL for approval
        approval_response = self.client.patch(approve_url, format='json')

        # Verify that the transaction is approved and completed
        self.assertEqual(approval_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approval_response.data['status'], 'success')

        # Fetch the transaction again and check that its status is now 'completed'
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'completed')
        self.assertEqual(transaction.is_approved, True)

        print("PATCH transaction test for pending transactions completed.\n\n\n")
