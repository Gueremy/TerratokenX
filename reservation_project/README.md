# Reservation Project

This Django project implements a reservation system with a user-friendly interface for making reservations and an admin panel for managing them. 

## Features

- **Reservation Form**: Users can fill out a form with their name, email, phone, address, date, and time for reservations.
- **Validation**: Basic validation is included to ensure all fields are filled out correctly and to prevent double bookings.
- **Payment Processing**: Integrated with Webpay for secure payment processing.
- **Email Notifications**: Optional email notifications can be sent to both clients and administrators upon successful reservation.
- **Admin Panel**: A Django Admin interface for managing reservations.
- **WhatsApp Integration**: A floating WhatsApp button for direct communication with a pre-filled message option.
- **Mobile-Friendly**: The application is designed to be responsive and mobile-friendly.
- **Database**: Utilizes MySQL for data storage.

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd reservation_project
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure your database settings in `reservation_project/settings.py`.

4. Run migrations to set up the database:
   ```
   python manage.py migrate
   ```

5. Create a superuser to access the admin panel:
   ```
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```
   python manage.py runserver
   ```

7. Access the application at `http://127.0.0.1:8000/` and the admin panel at `http://127.0.0.1:8000/admin/`.

## Usage

- Users can navigate to the reservation form, fill in their details, and submit the form.
- Upon successful submission, users will receive a confirmation message.
- Admins can manage reservations through the admin dashboard.

## Deployment

This project can be deployed on hosting services like Hostinger. Ensure that the server supports Django and MySQL.

## Contributing

Feel free to submit issues or pull requests for improvements and bug fixes. 

## License

This project is licensed under the MIT License.