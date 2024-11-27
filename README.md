# Secure Banking Transactions API

A secure REST API designed for managing banking transactions, featuring user authentication, role-based access control, secure transaction management, and multi-factor authentication (MFA). Built using Django REST Framework, the API follows industry-standard best practices to ensure secure and efficient operations.

## Features

- **User Authentication** (Sign-up, Login)
- **Multi-Factor Authentication (MFA)**
- **Role-Based Access Control** (Admin and User roles)
- **Transaction Management** (Fund Transfers, Transaction History)
- **Account Balance Verification**
- Protection against **SQL Injection**, **CSRF**, and **XSS**

## Tech Stack

- **Backend Framework**: Django REST Framework (Python)
- **Database**: PostgreSQL
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: bcrypt
- **Security**: CSRF Protection, HTTPS, Input Validation

## Setup Instructions

1. Clone the repository:
   `git clone https://github.com/yourusername/secure-banking-api.git`

2. Navigate to the project directory:
   `cd secure-banking-api`

3. Create and activate a virtual environment:
   - For Windows:
     `python -m venv venv`
     `venv\Scripts\activate`
   - For macOS/Linux:
     `python3 -m venv venv`
     `source venv/bin/activate`

4. Install dependencies:
   `pip install -r requirements.txt`

5. Apply migrations to set up the database:
   `python manage.py migrate`

6. Create a superuser for accessing the Django admin interface:
   `python manage.py createsuperuser`

7. Run the development server:
   `python manage.py runserver`

Once the server is running, navigate to `http://127.0.0.1:8000` in a web browser to interact with the API.

## Completed Phases

### Phase 1: Project Setup and Initial Configuration

In the initial phase, the foundation for the project was established. Key tasks included:

- **Repository Setup**: Created a new GitHub repository for version control and collaboration.
- **Django Configuration**: Set up Django with REST framework and configured PostgreSQL as the database.
- **Environment Setup**: Installed and configured necessary dependencies, including Django REST Framework, JWT for authentication, and bcrypt for password hashing.
- **Initial Migrations**: Created the initial database structure and applied migrations to set up the models for users and transactions.

### Phase 2: User Authentication and Multi-Factor Authentication (MFA)

This phase involved the development of secure user authentication, along with multi-factor authentication for enhanced security:

- **User Registration**: Implemented secure registration, where users are required to input a unique username, email, and password. Passwords are hashed using bcrypt for security.
- **Login Endpoint**: Developed a login API endpoint that allows users to authenticate using their credentials. Upon successful login, the system issues a JWT for subsequent requests.
- **Multi-Factor Authentication (MFA)**: Integrated MFA to enhance security, requiring a secondary verification step (such as an SMS or email code) when users log in, especially when logging in from a new device.
- **Token Management**: Designed a secure JWT-based token system that handles user sessions. The tokens are used to authorize users for protected routes and expire after a set period to enhance security.

### Phase 3: Role-Based Access Control (RBAC)

Role-based access control (RBAC) was implemented to ensure that users have access to resources based on their role. The system differentiates between regular users and admins:

- **User Roles**: Two primary roles were defined: `admin` and `user`. Admins have access to manage all users and transactions, while regular users can only view and manage their own transactions.
- **Access Control**: Implemented decorators and middleware to ensure that only authorized users can access certain endpoints. Admins can access endpoints for managing users and viewing all transactions, while users can only interact with their own data.

### Phase 4: Transaction Management

The core functionality of the API—managing banking transactions—was built in this phase. Features include:

- **Transaction Creation**: Users can initiate transactions by transferring funds from one account to another. The transaction details (amount, sender, receiver, etc.) are securely processed and stored.
- **Transaction History**: Each user can view a history of their transactions, providing them with transparency and control over their financial activities.
- **Account Balance Verification**: Before initiating a transaction, users can verify their current balance to ensure they have sufficient funds. The balance is updated automatically after each successful transaction.
- **Transaction Limits**: To prevent fraudulent activities, transaction limits were implemented, ensuring that no user can transfer an amount beyond their allowed limit.
- **Input Validation**: All incoming transaction data undergoes validation to prevent common security threats such as SQL injection, Cross-Site Scripting (XSS), and other malicious inputs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
