from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.test import TransactionTestCase
from .models import UserProfile
from django.db import connection
from decimal import Decimal
from unittest.mock import patch
from unittest import mock
import ssl
from django.test import override_settings

ssl._create_default_https_context = ssl._create_unverified_context

class TransactionViewTestCase(TransactionTestCase):
    def setUp(self):
        """
        This method will be run before each test.
        Clean up the database, create users and profiles, and initialize API client.
        """
        # Create users for testing
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.receiver = User.objects.create_user(username='testreceiver', email='testreceiver@example.com', password='password')

        # Create user profiles for the users
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user, defaults={'balance': 100.00})
        if not created:  # If the profile already exists, ensure balance is correct
            self.user_profile.balance = 100.00

        self.receiver_profile, created = UserProfile.objects.get_or_create(user=self.receiver, defaults={'balance': 100.00})
        if not created:  # If the profile already exists, ensure balance is correct
            self.receiver_profile.balance = 100.00
        self.user_profile.save()
        self.receiver_profile.save()

        # Generate JWT token for the user
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)  # Get the access token

        # Initialize APIClient
        self.client = APIClient()

        # Set authorization header for the user with the JWT token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Define the URL for transaction creation
        self.url = '/api/transactions/'  # Ensure this is the correct URL

        # Set the registration URL
        self.register_url = '/api/register/'  # Adjust the URL as per your app
        self.verify_otp_url = '/api/verify-otp/'  # Adjust the URL as per your app
        self.login_url = '/api/login/'
        self.verify_login_url = '/api/verify-login/'
        self.change_password_url = '/api/change-password/'

        # Mocking the email sending function to avoid actually sending emails
        self.patcher = patch('banking_api.utils.send_mail')
        self.mock_send_mail = self.patcher.start()

    def tearDown(self):
        """
        Clean up after each test.
        Ensure the database is reset and auto-increment fields are reset.
        """
        self.clean_database()

        # Reset the database and make sure auto-increment fields are reset
        connection.close()

    def clean_database(self):
        """
        Explicitly delete the users, related profiles, and tokens to ensure no conflicts in the test.
        """
        UserProfile.objects.all().delete()
        User.objects.all().delete()

    #@override_settings(EMAIL_BACKEND='django.core.mail.backends.dummy.EmailBackend')
    @patch('banking_api.utils.send_mail')  # Mocking send_mail
    def test_register_user_and_send_otp(self, mock_send_email):
        """
        Test that a new user can register, receive an OTP, and then create a transaction.
        """
        # User registration data
        print(mock_send_email.call_count)
        registration_data = {
            'username' : 'new_testuser',
            'password' : 'securepassword123',
            'email' : 'new_testuser@example.com'
        }

        # Send the registration request
        print("truaso Sending registration request...")
        response = self.client.post(self.register_url, registration_data, format='json', follow=True)
        print(self.register_url)
        print(response)
        print(response.content)
        print(mock_send_email.call_count)

        # Print response content for debugging
        print("Response content:", response.data)

        # Assert that registration is successful
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'User registered successfully. Check your email for the OTP to verify your account.')

        # Check if send_mail was called (ensure it's called with correct arguments)
        print("Checking send_mail calls...")
        mock_send_email.assert_any_call(
            'Your OTP Code',
            mock.ANY,  # The exact OTP content will vary; you could refine this with regex if needed
            'webmaster@localhost',
            ['new_testuser@example.com']
        )

        # Fetch the created user from the database
        new_user = User.objects.get(username=registration_data['username'])
        new_profile = new_user.profile
        otp = new_profile.otp  # OTP generated during registration
        print("Generated OTP:", otp)

        # Initialize the balance for the new user
        new_profile.balance = Decimal('100.00')  # Give the new user an initial balance
        new_profile.save()

        # Create a new receiver for the transaction
        receiver_data = {
            'username': 'new_receiver',
            'email': 'new_receiver@example.com',
            'password': 'securepassword123'
        }
        receiver_response = self.client.post(self.register_url, receiver_data, format='json')
        self.assertEqual(receiver_response.status_code, status.HTTP_201_CREATED)

        # Check if send_mail was called for the receiver
        mock_send_email.assert_any_call(
            'Your OTP Code',
            mock.ANY,
            'webmaster@localhost',
            ['new_receiver@example.com']
        )
        self.assertEqual(mock_send_email.call_count, 2)  # Assert that send_mail was called twice

        new_receiver = User.objects.get(username=receiver_data['username'])
        new_receiver_profile = new_receiver.profile

        # Now authenticate the new user
        refresh = RefreshToken.for_user(new_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Verify the OTP
        print("Verifying OTP...")
        otp_response = self.client.post(self.verify_otp_url, {'otp': otp}, format='json')
        print("OTP Response Content:", otp_response.data)

        # Assert OTP verification is successful
        self.assertEqual(otp_response.status_code, status.HTTP_200_OK)
        self.assertEqual(otp_response.data['message'], 'OTP verified successfully!')

        # Assert that the OTP is cleared after successful verification
        new_profile.refresh_from_db()  # Fetch the latest data from the DB
        self.assertIsNone(new_profile.otp)  # Ensure OTP is cleared
        self.assertIsNone(new_profile.otp_expiration)  # Ensure expiration is cleared

        # Now proceed to create a transaction
        print("Creating a transaction...")
        transaction_data = {
            'sender': new_user.id,  # Correct field name
            'receiver': new_receiver.id,
            'amount': 50.00
        }
        transaction_response = self.client.post(self.url, transaction_data, format='json')

        # Assert that the transaction is successful
        print("Transaction Response Content:", transaction_response.data)
        self.assertEqual(transaction_response.status_code, status.HTTP_201_CREATED)
        self.assertIn('transaction', transaction_response.data['data'])  # Check 'transaction' key inside 'data'
        self.assertEqual(Decimal(transaction_response.data['data']['transaction']['amount']), Decimal(transaction_data['amount']))

        # Assert that the sender's balance is updated
        new_profile.refresh_from_db()
        self.assertEqual(new_profile.balance, Decimal('50.00'))

        # Assert that the receiver's balance is updated
        new_receiver_profile.refresh_from_db()
        self.assertEqual(new_receiver_profile.balance, Decimal('50.00'))



    def test_verify_otp_invalid(self):
        """
        Test that the user cannot verify an invalid OTP.
        """
        # Use an invalid OTP
        invalid_otp = '123456'

        # Send the OTP verification request with the invalid OTP
        response = self.client.post(self.verify_otp_url, {'otp': invalid_otp}, format='json')

        # Assert invalid OTP response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid OTP.')


    @patch('banking_api.utils.send_mail')  # Mocking send_mail to avoid sending real emails
    def test_login_with_mfa_and_verify_otp(self, mock_send_email):
        """
        Test that an existing user can log in, receive an OTP, and then verify the OTP to complete login.
        """
        # User registration data
        registration_data = {
            'username': 'testtommy',
            'email': 'testtommy@example.com',
            'password': 'securepassword123'
        }

        # Create the user
        response = self.client.post(self.register_url, registration_data, format='json',follow=True)
        print(response)
        print(response.data)
        print("Registration Response content:", response.data)
        print(response.status_code)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Fetch the created user from the database
        user = User.objects.get(username=registration_data['username'])
        user_profile = user.profile
        user_profile.mfa_enabled = True  # Simulate MFA being enabled for the user
        user_profile.save()

        # Now, attempt to log in (this triggers MFA if enabled)
        login_data = {
            'email': user.email,
            'password': registration_data['password']
        }
        print("Login data:", login_data)
        response = self.client.post(self.login_url, login_data, format='json')
        print("Login Response content:", response.data)
        

        # Assert that login is unsuccessful but MFA is required
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['mfa_required'])
        self.assertIn('Check your email for the OTP', response.data['message'])

        # Check if send_mail was called to send OTP to the user's email
        mock_send_email.assert_any_call(
            'Your OTP Code',
            mock.ANY,  # The exact OTP content will vary; you could refine this with regex if needed
            'webmaster@localhost',  # Replace with your app's sender email
            [user.email]
        )

        # Simulate the user receiving the OTP from their email
        otp = user_profile.otp  # This should be generated and stored in the user's profile
        print("Generated OTP:", otp)
        
        # Now authenticate the new user
        refresh = RefreshToken.for_user(user_profile)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Now verify the OTP for login
        otp_data = {'otp': otp}
        otp_response = self.client.post(self.verify_login_url, otp_data, format='json')
        print("OTP Response Content:", otp_response.data)

        # Assert OTP verification is successful
        self.assertEqual(otp_response.status_code, status.HTTP_200_OK)
        self.assertEqual(otp_response.data['message'], 'OTP verified successfully!')

        # Assert that the OTP is cleared after successful verification
        user_profile.refresh_from_db()  # Fetch the latest data from the DB
        self.assertIsNone(user_profile.otp)  # Ensure OTP is cleared
        self.assertIsNone(user_profile.otp_expiration)  # Ensure expiration is cleared

        # Now the user should be fully logged in and can proceed to perform actions
        print("Logged in successfully. User is authenticated.")
       
    @patch('banking_api.utils.send_mail')   
    def test_change_password(self, mock_send_email):
        """
        Test that a user can change their password successfully.
        """
        # Define the endpoint for changing password
        change_password_url = '/api/change-password/'  # Adjust to match your app's endpoint
        
        registration_data = {
            'username': 'testtest',
            'email': 'testtest@example.com',
            'password': 'securepassword123'
        }

        response = self.client.post(self.register_url, registration_data, format='json',follow=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        mock_send_email.assert_any_call(
            'Your OTP Code',
            mock.ANY,  # The exact OTP content will vary; you could refine this with regex if needed
            'webmaster@localhost',
            ['testtest@example.com']
        )
        
        # Fetch the created user from the database
        news_user = User.objects.get(username=registration_data['username'])
        news_profile = news_user.profile
        otp = news_profile.otp  # OTP generated during registration
        print("Generated OTP:", otp)
        
        # Now authenticate the new user
        refresh = RefreshToken.for_user(news_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Verify the OTP
        print("Verifying OTP...")
        otp_response = self.client.post(self.verify_otp_url, {'otp': otp}, format='json')
        print("OTP Response Content:", otp_response.data)

        # Assert OTP verification is successful
        self.assertEqual(otp_response.status_code, status.HTTP_200_OK)
        self.assertEqual(otp_response.data['message'], 'OTP verified successfully!')
        
        # Assert that the OTP is cleared after successful verification
        news_profile.refresh_from_db()  # Fetch the latest data from the DB
        self.assertIsNone(news_profile.otp)  # Ensure OTP is cleared
        self.assertIsNone(news_profile.otp_expiration)  # Ensure expiration is cleared

        # Data for changing password
        change_password_data = {
            'old_password': 'securepassword123',  # The current password
            'new_password': 'newsecurepassword123'  # The new password
        }

        # Send request to change password
        response = self.client.post(change_password_url, change_password_data, format='json')
        response_json = response.json()
        print('response')
        print(response_json)

        # Assert that the response is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_json['message'], 'Password changed successfully.')

        # Attempt login with the old password (should fail)
        print(news_user.email)
        old_login_data = {
            'email': news_user.email,
            'password': 'securepassword123'  # Old password
        }
        old_login_response = self.client.post(self.login_url, old_login_data, format='json')
        old_login_response_json = old_login_response.json()
        print(old_login_response_json)
        self.assertEqual(old_login_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Invalid email or password.', old_login_response_json['error'])

        # Attempt login with the new password (should succeed)
        new_login_data = {
            'email': news_user.email,
            'password': 'newsecurepassword123'  # New password
        }
        new_login_response = self.client.post(self.login_url, new_login_data, format='json')
        new_login_response_json = new_login_response.json()
        print(new_login_response_json)
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', new_login_response_json)  # Verify the access token is returned