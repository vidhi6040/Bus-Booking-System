import os
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from mysql.connector import IntegrityError
from app.database import get_connection
from app.auth import hash_password, check_password

load_dotenv()
app = FastAPI(title="GreenRide Bus Booking")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "dev-key-change-me"))
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def user_of(request):
    return request.session.get("user")

def render(request: Request, name: str, **data):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "user": user_of(request),
            **data
        }
    )
    
def go(path):
    return RedirectResponse(path, status_code=303)

def audit(cur, uid, action, details):
    cur.execute("INSERT INTO audit_logs(user_id,action,details) VALUES(%s,%s,%s)", (uid, action, details))

@app.get("/")
def home(request: Request):
    return render(request, "home.html")

@app.get("/register")
def register_page(request: Request):
    return render(request, "register.html", error=None)

@app.post("/register")
def register(request: Request, name: str=Form(...), email: str=Form(...), phone: str=Form(""), password: str=Form(...)):
    if not name.strip() or "@" not in email or len(password) < 8:
        return render(request, "register.html", error="Enter valid details and a password of at least 8 characters.")
    conn = get_connection()
    if not conn:
        return render(request, "register.html", error="MySQL connection failed.")
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users(name,email,phone,password_hash) VALUES(%s,%s,%s,%s)",
                    (name.strip(), email.strip().lower(), phone.strip(), hash_password(password)))
        conn.commit()
        return go("/login?registered=1")
    except IntegrityError:
        conn.rollback()
        return render(request, "register.html", error="This email is already registered.")
    finally:
        cur.close(); conn.close()

@app.get("/login")
def login_page(request: Request):
    msg = "Registration successful. Please log in." if request.query_params.get("registered") else None
    return render(request, "login.html", error=None, message=msg)

@app.post("/login")
def login(request: Request, email: str=Form(...), password: str=Form(...)):
    conn = get_connection()
    if not conn:
        return render(request, "login.html", error="MySQL connection failed.", message=None)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id,name,email,role,password_hash FROM users WHERE email=%s", (email.strip().lower(),))
        row = cur.fetchone()
        if not row or not check_password(password, row["password_hash"]):
            return render(request, "login.html", error="Incorrect email or password.", message=None)
        request.session.clear()
        request.session["user"] = {k: row[k] for k in ("id","name","email","role")}
        return go("/dashboard")
    finally:
        cur.close(); conn.close()

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return go("/")

@app.get("/search")
def search(request: Request, origin: str="", destination: str="", travel_date: str=""):
    trips=[]; error=None
    if origin and destination and travel_date:
        conn=get_connection()
        if not conn: error="MySQL connection failed."
        else:
            cur=conn.cursor(dictionary=True)
            try:
                cur.execute("""
                SELECT t.id,t.departure,t.arrival,t.fare,b.bus_name,b.bus_number,b.bus_type,b.total_seats,
                       s1.city origin,s2.city destination,
                       (SELECT COUNT(*) FROM bookings bk WHERE bk.trip_id=t.id AND bk.status='CONFIRMED') booked
                FROM trips t JOIN buses b ON b.id=t.bus_id
                JOIN stops s1 ON s1.id=t.origin_id JOIN stops s2 ON s2.id=t.destination_id
                WHERE LOWER(s1.city)=LOWER(%s) AND LOWER(s2.city)=LOWER(%s)
                AND DATE(t.departure)=%s AND t.status='Scheduled' AND t.departure>NOW()
                ORDER BY t.departure
                """,(origin.strip(),destination.strip(),travel_date))
                trips=cur.fetchall()
                for t in trips: t["available"]=t["total_seats"]-t["booked"]
            finally: cur.close(); conn.close()
    return render(request,"search.html",trips=trips,error=error,origin=origin,destination=destination,travel_date=travel_date)

@app.get("/book/{trip_id}")
def booking_page(request: Request, trip_id: int):
    if not user_of(request): return go("/login")
    conn=get_connection()
    if not conn: return go("/search")
    cur=conn.cursor(dictionary=True)
    try:
        cur.execute("""SELECT t.*,b.bus_name,b.total_seats,s1.city origin,s2.city destination
        FROM trips t JOIN buses b ON b.id=t.bus_id JOIN stops s1 ON s1.id=t.origin_id
        JOIN stops s2 ON s2.id=t.destination_id WHERE t.id=%s AND t.status='Scheduled'""",(trip_id,))
        trip=cur.fetchone()
        if not trip: return go("/search")
        cur.execute("SELECT seat_number FROM bookings WHERE trip_id=%s AND status='CONFIRMED'",(trip_id,))
        booked=[r["seat_number"] for r in cur.fetchall()]
        seats=[f"S{i:02d}" for i in range(1,trip["total_seats"]+1)]
        return render(request,"booking.html",trip=trip,booked=booked,seats=seats,error=request.query_params.get("error"))
    finally: cur.close(); conn.close()

@app.post("/book/{trip_id}")
def create_booking(request: Request, trip_id: int, passenger_name: str=Form(...),
                   passenger_age: int=Form(...), passenger_gender: str=Form(...),
                   passenger_phone: str=Form(...), seat_number: str=Form(...)):
    user=user_of(request)
    if not user: return go("/login")
    if not passenger_name.strip() or not 1 <= passenger_age <= 120 or passenger_gender not in ("Male","Female","Other"):
        return go(f"/book/{trip_id}?error=Please%20enter%20valid%20passenger%20details.")
    conn=get_connection()
    if not conn: return go("/search")
    cur=conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cur.execute("SELECT * FROM trips WHERE id=%s FOR UPDATE",(trip_id,))
        trip=cur.fetchone()
        if not trip or trip["status"]!="Scheduled" or trip["departure"]<=datetime.now():
            conn.rollback(); return go("/search")
        cur.execute("SELECT total_seats FROM buses WHERE id=%s",(trip["bus_id"],))
        bus=cur.fetchone()
        if seat_number not in {f"S{i:02d}" for i in range(1,bus["total_seats"]+1)}:
            conn.rollback(); return go(f"/book/{trip_id}?error=Invalid%20seat.")
        pnr="GR"+uuid4().hex[:10].upper()
        cur.execute("""INSERT INTO bookings
        (pnr,user_id,trip_id,passenger_name,passenger_age,passenger_gender,passenger_phone,seat_number,amount)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (pnr,user["id"],trip_id,passenger_name.strip(),passenger_age,passenger_gender,passenger_phone.strip(),seat_number,trip["fare"]))
        audit(cur,user["id"],"BOOKING_CREATED",f"PNR {pnr}; seat {seat_number}")
        conn.commit()
        return go(f"/dashboard?pnr={pnr}")
    except IntegrityError:
        conn.rollback()
        return go(f"/book/{trip_id}?error=That%20seat%20is%20already%20booked.")
    except Exception as exc:
        conn.rollback(); print("Booking error:",exc)
        return go(f"/book/{trip_id}?error=Booking%20failed.")
    finally: cur.close(); conn.close()

@app.get("/dashboard")
def dashboard(request: Request):
    user=user_of(request)
    if not user: return go("/login")
    conn=get_connection()
    if not conn: return render(request,"dashboard.html",bookings=[],error="MySQL connection failed.",success_pnr=None)
    cur=conn.cursor(dictionary=True)
    try:
        cur.execute("""SELECT bk.*,t.departure,t.arrival,s1.city origin,s2.city destination,b.bus_name
        FROM bookings bk JOIN trips t ON t.id=bk.trip_id JOIN buses b ON b.id=t.bus_id
        JOIN stops s1 ON s1.id=t.origin_id JOIN stops s2 ON s2.id=t.destination_id
        WHERE bk.user_id=%s ORDER BY bk.booked_at DESC""",(user["id"],))
        bookings=cur.fetchall()
        return render(request,"dashboard.html",bookings=bookings,error=None,success_pnr=request.query_params.get("pnr"))
    finally: cur.close(); conn.close()

@app.post("/cancel/{booking_id}")
def cancel_booking(request: Request, booking_id: int):
    user=user_of(request)
    if not user: return go("/login")
    conn=get_connection()
    if not conn: return go("/dashboard")
    cur=conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cur.execute("""SELECT bk.*,t.departure,t.cancellation_hours,t.refund_percent
        FROM bookings bk JOIN trips t ON t.id=bk.trip_id
        WHERE bk.id=%s AND bk.user_id=%s FOR UPDATE""",(booking_id,user["id"]))
        bk=cur.fetchone()
        if not bk or bk["status"]!="CONFIRMED":
            conn.rollback(); return go("/dashboard")
        deadline=bk["departure"]-timedelta(hours=bk["cancellation_hours"])
        refund=(Decimal(str(bk["amount"]))*Decimal(str(bk["refund_percent"]))/Decimal("100")).quantize(Decimal("0.01")) if datetime.now()<=deadline else Decimal("0.00")
        status="PROCESSED" if refund>0 else "NOT_APPLICABLE"
        cur.execute("UPDATE bookings SET status='CANCELLED',refund_status=%s,refund_amount=%s,cancelled_at=NOW() WHERE id=%s",(status,refund,booking_id))
        audit(cur,user["id"],"BOOKING_CANCELLED",f"Booking {booking_id}; simulated refund {refund}")
        conn.commit()
        return go("/dashboard")
    except Exception as exc:
        conn.rollback(); print("Cancellation error:",exc); return go("/dashboard")
    finally: cur.close(); conn.close()

@app.get("/operator")
def operator_page(request: Request):
    user=user_of(request)
    if not user or user["role"] not in ("operator","admin"): return go("/login")
    conn=get_connection()
    if not conn: return render(request,"operator.html",trips=[],manifest=[],error="MySQL connection failed.")
    cur=conn.cursor(dictionary=True)
    try:
        cur.execute("""SELECT t.id,t.departure,b.bus_name,b.bus_number,b.total_seats,
        s1.city origin,s2.city destination,
        SUM(CASE WHEN bk.status='CONFIRMED' THEN 1 ELSE 0 END) booked
        FROM trips t JOIN buses b ON b.id=t.bus_id
        JOIN stops s1 ON s1.id=t.origin_id JOIN stops s2 ON s2.id=t.destination_id
        LEFT JOIN bookings bk ON bk.trip_id=t.id
        GROUP BY t.id,b.id,s1.id,s2.id ORDER BY t.departure""")
        trips=cur.fetchall()
        for t in trips: t["booked"]=t["booked"] or 0; t["available"]=t["total_seats"]-t["booked"]
        cur.execute("""SELECT bk.pnr,bk.passenger_name,bk.passenger_phone,bk.seat_number,bk.status,
        t.departure,s1.city origin,s2.city destination FROM bookings bk JOIN trips t ON t.id=bk.trip_id
        JOIN stops s1 ON s1.id=t.origin_id JOIN stops s2 ON s2.id=t.destination_id
        ORDER BY bk.booked_at DESC LIMIT 100""")
        manifest=cur.fetchall()
        return render(request,"operator.html",trips=trips,manifest=manifest,error=None)
    finally: cur.close(); conn.close()

@app.get("/health")
def health():
    conn=get_connection()
    if not conn: return {"status":"error","message":"MySQL connection failed"}
    conn.close()
    return {"status":"ok","message":"Application and database are running"}
