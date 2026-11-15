# GreenRide Bus Booking System

A simple student-level bus booking project using HTML, CSS, JavaScript, FastAPI and MySQL.

## Features
- Passenger registration and login with bcrypt password hashing
- Session-based login
- Search trips by origin, destination and date
- Seat selection and PNR ticket booking
- Database constraint and transaction to prevent duplicate confirmed seats
- Booking history and cancellation
- Simulated refund based on the trip cancellation policy
- Operator dashboard with trip occupancy and passenger manifest
- Audit log for booking/cancellation actions
- FastAPI API documentation at `/docs`

## Setup (Windows PowerShell)

1. Install Python 3.10+ and MySQL 8.0+.
2. Open MySQL Workbench and execute `database/schema.sql`.
3. Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

4. Install packages:

```powershell
pip install -r requirements.txt
```

5. Copy `.env.example` to `.env` and set your MySQL password and a long random `SECRET_KEY`.

6. Start the app from the project root:

```powershell
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

API docs: http://127.0.0.1:8000/docs

## Demo flow
1. Register a passenger.
2. Log in.
3. Search Delhi to Jaipur using tomorrow's date.
4. Select a trip and seat.
5. Enter passenger details and confirm.
6. View the PNR in My Bookings.
7. Cancel the booking and check refund status.
8. Log in as the demo operator to view occupancy and manifest.

## Notes
- Refunds are simulated; no real payment is processed.
- The operator dashboard is read-only. Sample operators, buses and trips are inserted by `seed.py`; a full admin CRUD interface is not included.
- The booking route locks the trip row in a transaction and the database unique key prevents duplicate active trip-seat bookings.
- For public deployment, use HTTPS, a strong secret key, CSRF protection, rate limiting and production cookie settings.
- Change demo credentials before deployment. Do not upload `.env` to GitHub.
- Test the app with your local MySQL configuration before submitting.
