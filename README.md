# Secure Banking Transactions API

This project is a secure REST API for managing banking transactions. It supports user authentication, role-based access control, secure transaction management, and multi-factor authentication (MFA). The API is built using Django REST Framework and integrates best practices in web security.

## Features

- **User Authentication** (Sign-up, Login)
- **Multi-Factor Authentication** (MFA)
- **Role-Based Access Control** (Admin and User roles)
- **Secure Transactions Management** (Fund Transfers, Transaction History)
- **Account Balance Check**
- Security measures against **SQL Injection**, **CSRF**, and **XSS**

## Tech Stack

- **Backend Framework**: Django REST Framework (Python)
- **Database**: PostgreSQL
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: bcrypt
- **Security**: CSRF Protection, HTTPS, Input Validation

## Setup Instructions

Follow these steps to set up the project locally.

1. Clone the repository  
   `git clone https://github.com/yourusername/secure-banking-api.git`

2. Create a Virtual Environment  
   `python -m venv venv`

3. Activate the Virtual Environment  
   For Windows:  
   `venv\Scripts\activate`  
   For macOS/Linux:  
   `source venv/bin/activate`

4. Install Dependencies  
   `pip install -r requirements.txt`

5. Apply Migrations  
   `python manage.py migrate`

6. Create a Superuser  
   `python manage.py createsuperuser`

## Running the Project Locally

To run the development server locally, use the following command:

`python manage.py runserver`

Visit `http://127.0.0.1:8000` in your browser to interact with the API.

## Completed Phases

### Phase 1: Project Setup

In this phase, we set up the project repository and initialized the basic structure:

- Created a GitHub repository for version control.
- Set up Django REST Framework and PostgreSQL for database management.
- Installed necessary dependencies and configured the environment.

### Phase 2: User Authentication

We implemented basic user authentication with JWT for session management:

- **User Registration**: Implemented registration endpoint with hashed passwords using `create_user`.
- **Login**: Developed a login endpoint to generate JWT tokens upon successful authentication.
- **Multi-Factor Authentication (MFA)**: Integrated MFA for extra security during login.

### Phase 3: Role-Based Access Control (RBAC)

This phase focused on defining user roles and restricting access to certain API endpoints based on those roles:

- **User Roles**: Defined roles (admin, user).
- **Access Control**: Implemented middleware or decorators to enforce role-based permissions on specific endpoints.

## API Documentation

For testing and exploring the API endpoints, you can use [Postman](https://www.postman.com/) or [Swagger](https://swagger.io/).

## Security Considerations

- Ensure **HTTPS** is used in production environments.
- Use **JWTs** for secure token-based authentication.
- Protect against **CSRF** attacks by enabling CSRF protection.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
