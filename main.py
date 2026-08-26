import csv
import hashlib
import io
import os
import secrets
import sqlite3
import time
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Advanced Web Portal & Management System")

# CORS এনাবল করা
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "app_database.db"

# --- ডাটাবেস ইনিশিয়ালাইজেশন ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # ১. ইউজার টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            username TEXT UNIQUE,
            email TEXT,
            mobile TEXT,
            district TEXT,
            upazila TEXT,
            password_hash TEXT,
            balance REAL DEFAULT 0.0,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ২. রিচার্জ টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS recharges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            amount REAL,
            method TEXT,
            transaction_id TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ৩. সার্চ ও ট্রানজ্যাকশন লগ টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS search_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            district TEXT,
            upazila TEXT,
            fee_charged REAL,
            balance_before REAL,
            balance_after REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ৪. নমুনা সার্চ ডাটাবেস (জেনেরিক ক্যাটালগ)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sample_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT,
            upazila TEXT,
            voter_no TEXT,
            name TEXT,
            father_name TEXT,
            mother_name TEXT,
            dob TEXT
        )
    ''')

    # ডিফল্ট অ্যাডমিন একাউন্ট (admin / admin123)
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute('''
            INSERT INTO users (uid, username, email, password_hash, balance, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("UID-ADMIN-001", "admin", "admin@portal.com", admin_pass, 5000.0, "admin"))

    # ডামি ডাটা ইনসার্ট (টেস্টিংয়ের জন্য)
    c.execute("SELECT COUNT(*) FROM sample_records")
    if c.fetchone()[0] == 0:
        sample_data = [
            ("ঢাকা", "ধানমন্ডি", "10293847", "আব্দুর রহিম", "করিম উদ্দিন", "আমেনা বেগম", "1992-05-10"),
            ("ঢাকা", "গুলশান", "58493021", "সাকিব হাসান", "রফিকুল ইসলাম", "সালমা খাতুন", "1995-11-20"),
            ("চট্টগ্রাম", "পটিয়া", "39482019", "মোহাম্মদ আলী", "হাসান আলী", "নুরজাহান বেগম", "1988-02-15"),
            ("টাঙ্গাইল", "মধুপুর", "84920194", "মোঃ রাসেল আহমেদ", "আব্দুল খালেক", "মোছাঃ ফাতেমা", "1990-08-14"),
            ("পটুয়াখালী", "বাউফল", "67482910", "কামরুল ইসলাম", "মোস্তফা কামাল", "রাহেলা বেগম", "1996-03-25"),
            ("নওগাঁ", "পত্নীতলা", "48392019", "আরিফুল হক", "মজিবুর রহমান", "জাহানারা বেগম", "1994-12-05")
        ]
        c.executemany('''
            INSERT INTO sample_records (district, upazila, voter_no, name, father_name, mother_name, dob)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_data)

    conn.commit()
    conn.close()

init_db()

# --- স্ট্যাটিক ফাইল ও পেজ রাউটিং ---
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_home():
    return FileResponse("static/index.html") if os.path.exists("static/index.html") else {"msg": "index.html not found"}

@app.get("/login")
def serve_login():
    return FileResponse("static/login_tab_login.html") if os.path.exists("static/login_tab_login.html") else {"msg": "login.html not found"}

@app.get("/register")
def serve_register():
    return FileResponse("static/login_tab_login.html") if os.path.exists("static/login_tab_login.html") else {"msg": "register.html not found"}

@app.get("/admin")
def serve_admin():
    return FileResponse("static/admin.html") if os.path.exists("static/admin.html") else {"msg": "admin.html not found"}


# --- Pydantic Data Models ---
class RegisterModel(BaseModel):
    username: str
    password: str
    email: Optional[str] = ""
    mobile: Optional[str] = ""
    district: Optional[str] = ""
    upazila: Optional[str] = ""

class LoginModel(BaseModel):
    username: str
    password: str

class SearchModel(BaseModel):
    district: Optional[str] = ""
    upazila: Optional[str] = ""
    name: Optional[str] = ""
    fatherName: Optional[str] = ""
    motherName: Optional[str] = ""
    dob: Optional[str] = ""

class RechargeModel(BaseModel):
    amount: float
    method: str
    transaction_id: str

class BalanceUpdateModel(BaseModel):
    amount: float

class EditUserModel(BaseModel):
    username: str
    email: Optional[str] = ""
    password: Optional[str] = None
    balance: Optional[float] = None
    role: Optional[str] = "user"
    is_active: Optional[bool] = True


# --- ইউজার অথেনটিকেশন হেল্পার ---
def get_user_from_token(token: str):
    if not token or not token.startswith("Bearer "):
        return None
    raw_token = token.replace("Bearer ", "").strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, uid, username, email, balance, role, is_active FROM users WHERE uid=?", (raw_token,))
    user = c.fetchone()
    conn.close()
    if user and user[6] == 1:
        return {"id": user[0], "uid": user[1], "username": user[2], "email": user[3], "balance": user[4], "role": user[5]}
    return None


# ==========================================
# ১. ইউজার অথেনটিকেশন ও প্রোফাইল APIs
# ==========================================

@app.post("/api/auth/register")
def register_user(data: RegisterModel):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (data.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="এই ইউজারনেম ইতোমধ্যে ব্যবহৃত হয়েছে!")

    uid = f"UID-{secrets.token_hex(4).upper()}"
    p_hash = hashlib.sha256(data.password.encode()).hexdigest()

    # ১৫ টাকা ফ্রি বোনাস ব্যালেন্স
    c.execute('''
        INSERT INTO users (uid, username, email, mobile, district, upazila, password_hash, balance, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user')
    ''', (uid, data.username, data.email, data.mobile, data.district, data.upazila, p_hash, 15.0))
    conn.commit()
    conn.close()
    return {"message": "রেজিস্ট্রেশন সফল হয়েছে!", "token": uid}

@app.post("/api/auth/login")
def login_user(data: LoginModel):
    p_hash = hashlib.sha256(data.password.encode()).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT uid, role, is_active FROM users WHERE username=? AND password_hash=?", (data.username, p_hash))
    res = c.fetchone()
    conn.close()
    if not res:
        raise HTTPException(status_code=401, detail="ভুল ইউজারনেম অথবা পাসওয়ার্ড!")
    if res[2] == 0:
        raise HTTPException(status_code=403, detail="আপনার অ্যাকাউন্টটি সাময়িকভাবে বন্ধ করা হয়েছে!")
    return {"message": "লগইন সফল!", "token": res[0], "role": res[1]}

@app.get("/api/user/me")
def get_current_user(authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="অননুমোদিত অ্যাক্সেস!")
    return user

@app.get("/api/user/history")
def get_user_history(authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="লগইন করুন!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT district, upazila, fee_charged, balance_after, created_at
        FROM search_logs WHERE user_id=? ORDER BY id DESC LIMIT 20
    ''', (user["id"],))
    logs = c.fetchall()
    conn.close()

    return [{"district": l[0], "upazila": l[1], "fee": l[2], "balance": l[3], "time": l[4]} for l in logs]


# ==========================================
# ২. ব্যালেন্স রিচার্জ ও সার্চ ইঞ্জিন APIs
# ==========================================

@app.post("/api/recharge/request")
def request_recharge(data: RechargeModel, authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="লগইন করুন!")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="সঠিক পরিমাণ দিন!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO recharges (user_id, username, amount, method, transaction_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user["id"], user["username"], data.amount, data.method, data.transaction_id))
    conn.commit()
    conn.close()
    return {"message": "রিচার্জ রিকোয়েস্ট জমা হয়েছে। অ্যাডমিন ভেরিফাই করলে ব্যালেন্স যোগ হবে।"}

@app.post("/api/search")
def search_records(data: SearchModel, authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="অনুসন্ধান করতে প্রথমে লগইন করুন!")

    SEARCH_FEE = 3.0
    if user["balance"] < SEARCH_FEE:
        raise HTTPException(status_code=402, detail="পর্যাপ্ত ব্যালেন্স নেই! রিচার্জ করুন।")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # ব্যালেন্স কাটা
    new_bal = round(user["balance"] - SEARCH_FEE, 2)
    c.execute("UPDATE users SET balance=? WHERE id=?", (new_bal, user["id"]))

    # লগ রেকর্ড তৈরি
    c.execute('''
        INSERT INTO search_logs (user_id, username, district, upazila, fee_charged, balance_before, balance_after)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user["id"], user["username"], data.district or "-", data.upazila or "-", SEARCH_FEE, user["balance"], new_bal))

    # সার্চ কুয়েরি চালানো
    query = "SELECT voter_no, name, father_name, mother_name, dob, district, upazila FROM sample_records WHERE 1=1"
    params = []
    if data.district:
        query += " AND district LIKE ?"
        params.append(f"%{data.district}%")
    if data.upazila:
        query += " AND upazila LIKE ?"
        params.append(f"%{data.upazila}%")
    if data.name:
        query += " AND name LIKE ?"
        params.append(f"%{data.name}%")
    if data.fatherName:
        query += " AND father_name LIKE ?"
        params.append(f"%{data.fatherName}%")

    c.execute(query, params)
    rows = c.fetchall()
    conn.commit()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "voter_no": r[0],
            "name": r[1],
            "father_name": r[2],
            "mother_name": r[3],
            "dob": r[4],
            "district": r[5],
            "upazila": r[6]
        })

    return {"results": results, "new_balance": new_bal}


# ==========================================
# ৩. অ্যাডমিন প্যানেল কন্ট্রোল APIs (`admin.html`)
# ==========================================

@app.get("/api/admin/stats")
def get_admin_stats(authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="অ্যাডমিন অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM recharges WHERE status='PENDING'")
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*), COALESCE(SUM(fee_charged), 0) FROM search_logs")
    searches, income = c.fetchone()
    conn.close()

    return {
        "pending_recharges": pending,
        "total_users": total_users,
        "searches": searches,
        "income": round(income, 2),
        "label": "আজকের"
    }

@app.get("/api/admin/pending-recharges")
def get_pending_recharges(authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, amount, method, transaction_id, created_at FROM recharges WHERE status='PENDING'")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "amount": r[2], "method": r[3], "transaction_id": r[4], "created_at": r[5]} for r in rows]

@app.post("/api/admin/approve/{id}")
def approve_recharge(id: int, authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, amount FROM recharges WHERE id=? AND status='PENDING'", (id,))
    req = c.fetchone()
    if not req:
        conn.close()
        raise HTTPException(status_code=404, detail="রিকোয়েস্ট পাওয়া যায়নি!")

    u_id, amount = req
    c.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, u_id))
    c.execute("UPDATE recharges SET status='COMPLETED' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"message": f"রিচার্জ সফলভাবে অ্যাপ্রুভ হয়েছে এবং {amount} ৳ ব্যালেন্স যোগ হয়েছে!"}

@app.post("/api/admin/reject/{id}")
def reject_recharge(id: int, authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE recharges SET status='REJECTED' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return {"message": "রিচার্জ রিকোয়েস্ট বাতিল করা হয়েছে!"}

@app.get("/api/admin/users")
def get_all_users(search: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = "SELECT id, uid, username, email, mobile, district, upazila, balance, role, is_active, created_at FROM users"
    params = []
    if search:
        query += " WHERE uid LIKE ? OR username LIKE ? OR mobile LIKE ?"
        s_term = f"%{search}%"
        params = [s_term, s_term, s_term]

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0], "uid": r[1], "username": r[2], "email": r[3], "mobile": r[4],
        "district": r[5], "upazila": r[6], "balance": r[7], "role": r[8], "is_active": bool(r[9]), "created_at": r[10]
    } for r in rows]

# অ্যাডমিন কর্তৃক ইউজারের ব্যালেন্স যোগ/পরিবর্তন API
@app.post("/api/admin/users/{user_id}/add-balance")
def admin_add_balance(user_id: int, data: BalanceUpdateModel, authorization: Optional[str] = Header(None)):
    admin = get_user_from_token(authorization)
    if not admin or admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="অ্যাডমিন অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE id=?", (data.amount, user_id))
    conn.commit()
    conn.close()
    return {"message": f"ইউজারের অ্যাকাউন্টে {data.amount} ৳ সফলভাবে যোগ করা হয়েছে!"}

# অ্যাডমিন কর্তৃক ইউজার এডিট API
@app.put("/api/admin/users/{user_id}")
def admin_edit_user(user_id: int, data: EditUserModel, authorization: Optional[str] = Header(None)):
    admin = get_user_from_token(authorization)
    if not admin or admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    if data.password:
        p_hash = hashlib.sha256(data.password.encode()).hexdigest()
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (p_hash, user_id))

    if data.balance is not None:
        c.execute("UPDATE users SET balance=? WHERE id=?", (data.balance, user_id))

    c.execute('''
        UPDATE users SET username=?, email=?, role=?, is_active=? WHERE id=?
    ''', (data.username, data.email, data.role, 1 if data.is_active else 0, user_id))

    conn.commit()
    conn.close()
    return {"message": "ইউজারের তথ্য সফলভাবে আপডেট হয়েছে!"}

# অ্যাডমিন কর্তৃক ইউজার ডিলিট API
@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, authorization: Optional[str] = Header(None)):
    admin = get_user_from_token(authorization)
    if not admin or admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"message": "ইউজার অ্যাকাউন্ট সফলভাবে ডিলিট করা হয়েছে!"}

# অ্যাডমিন সার্চ লগ API
@app.get("/api/admin/search-logs")
def get_admin_search_logs(authorization: Optional[str] = Header(None)):
    admin = get_user_from_token(authorization)
    if not admin or admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT username, district, upazila, fee_charged, balance_before, balance_after, created_at
        FROM search_logs ORDER BY id DESC LIMIT 50
    ''')
    rows = c.fetchall()
    conn.close()
    return [{
        "username": r[0], "district": r[1], "upazila": r[2], "fee_charged": r[3],
        "balance_before": r[4], "balance_after": r[5], "created_at": r[6]
    } for r in rows]

# অ্যাডমিন CSV এক্সপোর্ট API (ইউজার ডেটা ডাউনলোড)
@app.get("/api/admin/export/users-csv")
def export_users_csv(authorization: Optional[str] = Header(None)):
    admin = get_user_from_token(authorization)
    if not admin or admin["role"] != "admin":
        raise HTTPException(status_code=403, detail="অনুমতি নেই!")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, uid, username, email, mobile, district, upazila, balance, role, created_at FROM users")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "UID", "Username", "Email", "Mobile", "District", "Upazila", "Balance", "Role", "Created At"])
    for r in rows:
        writer.writerow(r)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_report.csv"}
    )