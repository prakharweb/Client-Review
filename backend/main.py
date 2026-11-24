
import os
import logging
import html
from datetime import datetime, timezone
from typing import Optional

import requests

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, EmailStr, Field

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("customer-review")


# =====================================================
# DATABASE CONFIGURATION
# =====================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./reviews.db"
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# =====================================================
# GOOGLE REVIEW CONFIGURATION
# =====================================================

GOOGLE_REVIEW_URL = os.getenv(
    "GOOGLE_REVIEW_URL",
    "https://g.page/r/CSLhXGE7iSkSEAE/review"
)


# =====================================================
# FEEDBACK DATABASE MODEL
# =====================================================

class Feedback(Base):

    __tablename__ = "feedback"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(160),
        nullable=False
    )

    organization = Column(
        String(200),
        nullable=True
    )

    email = Column(
        String(254),
        nullable=False
    )

    phone = Column(
        String(40),
        nullable=True
    )

    rating = Column(
        Integer,
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


Base.metadata.create_all(bind=engine)


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="Customer Review & Feedback API",
    version="2.0.0"
)


# =====================================================
# CORS CONFIGURATION
# =====================================================

raw_origins = os.getenv(
    "CORS_ORIGINS",
    "*"
)

origins = [
    origin.strip().rstrip("/")
    for origin in raw_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in origins else origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# FEEDBACK REQUEST MODEL
# =====================================================

class FeedbackIn(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=160
    )

    organization: Optional[str] = Field(
        default=None,
        max_length=200
    )

    email: EmailStr

    phone: Optional[str] = Field(
        default=None,
        max_length=40
    )

    rating: int = Field(
        ge=1,
        le=5
    )

    message: str = Field(
        min_length=3,
        max_length=5000
    )


# =====================================================
# DATABASE SESSION
# =====================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =====================================================
# BREVO EMAIL NOTIFICATION
# =====================================================

def send_brevo_notification(item: Feedback):

    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_name = os.getenv(
        "SENDER_NAME",
        "Customer Reviews"
    )
    admin_email = os.getenv("ADMIN_EMAIL")

    # Check configuration

    missing = []

    if not api_key:
        missing.append("BREVO_API_KEY")

    if not sender_email:
        missing.append("SENDER_EMAIL")

    if not admin_email:
        missing.append("ADMIN_EMAIL")

    if missing:

        logger.error(
            "Brevo configuration missing: %s",
            ", ".join(missing)
        )

        return False, "Missing configuration: " + ", ".join(missing)

    # Rating information

    stars = (
        "★" * item.rating +
        "☆" * (5 - item.rating)
    )

    if item.rating <= 3:

        subject = (
            f"LOW RATING ALERT: "
            f"{item.rating}/5 - Customer Feedback"
        )

        heading = "New Customer Complaint / Feedback"
        heading_color = "#dc2626"

    else:

        subject = (
            f"New Customer Feedback: "
            f"{item.rating}/5 Stars"
        )

        heading = "New Customer Feedback"
        heading_color = "#15803d"

    # Escape customer-provided content

    name = html.escape(item.name)
    organization = html.escape(item.organization or "-")
    email = html.escape(str(item.email))
    phone = html.escape(item.phone or "-")
    message = html.escape(item.message).replace(
        "\n",
        "<br>"
    )

    submitted = item.created_at.isoformat()

    # Email HTML

    email_html = f"""
    <!DOCTYPE html>
    <html>
    <body style="
        font-family:Arial,sans-serif;
        background:#f5f6fa;
        padding:25px;
        color:#222;
    ">

        <div style="
            max-width:650px;
            margin:auto;
            background:#ffffff;
            padding:25px;
            border-radius:12px;
        ">

            <h2 style="color:{heading_color};">
                {heading}
            </h2>

            <div style="
                background:#fff7ed;
                padding:15px;
                border-radius:8px;
                margin:20px 0;
            ">

                <h2 style="
                    color:#e99a15;
                    margin:0;
                ">
                    {stars}
                </h2>

                <p>
                    Rating: <b>{item.rating}/5</b>
                </p>

            </div>

            <h3>Customer Details</h3>

            <table style="
                width:100%;
                border-collapse:collapse;
            ">

                <tr>
                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        <b>Name</b>
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        {name}
                    </td>
                </tr>

                <tr>
                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        <b>Hospital / Company</b>
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        {organization}
                    </td>
                </tr>

                <tr>
                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        <b>Email</b>
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        {email}
                    </td>
                </tr>

                <tr>
                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        <b>Mobile</b>
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        {phone}
                    </td>
                </tr>

                <tr>
                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        <b>Rating</b>
                    </td>

                    <td style="padding:10px;border-bottom:1px solid #eee;">
                        {item.rating}/5
                    </td>
                </tr>

            </table>

            <h3>Customer Feedback</h3>

            <div style="
                background:#f8fafc;
                padding:18px;
                border-radius:8px;
                line-height:1.6;
            ">
                {message}
            </div>

            <p style="color:#777;font-size:12px;margin-top:25px;">
                Feedback ID: {item.id}<br>
                Submitted: {submitted}
            </p>

            <hr style="border:0;border-top:1px solid #eee;">

            <p style="color:#999;font-size:12px;">
                Customer Review Management System
            </p>

        </div>

    </body>
    </html>
    """

    payload = {

        "sender": {
            "name": sender_name,
            "email": sender_email
        },

        "to": [
            {
                "email": admin_email
            }
        ],

        "replyTo": {
            "email": str(item.email),
            "name": item.name
        },

        "subject": subject,

        "htmlContent": email_html

    }

    # Send email through Brevo

    try:

        logger.info(
            "Sending Brevo notification for feedback ID %s, rating %s",
            item.id,
            item.rating
        )

        response = requests.post(

            "https://api.brevo.com/v3/smtp/email",

            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            },

            json=payload,

            timeout=25

        )

        logger.info(
            "Brevo HTTP status: %s",
            response.status_code
        )

        if response.status_code not in (200, 201, 202):

            logger.error(
                "Brevo API error: %s",
                response.text[:2000]
            )

            return False, (
                f"Brevo HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        result = response.json()

        message_id = result.get("messageId")

        logger.info(
            "Brevo accepted email. Message ID: %s",
            message_id
        )

        return True, "Email accepted by Brevo"

    except requests.exceptions.Timeout:

        logger.exception("Brevo request timed out")

        return False, "Brevo request timed out"

    except requests.exceptions.RequestException as exc:

        logger.exception("Brevo network error")

        return False, f"Brevo network error: {str(exc)[:300]}"

    except Exception as exc:

        logger.exception("Unexpected Brevo error")

        return False, f"Email error: {str(exc)[:300]}"


# =====================================================
# ADMIN AUTHENTICATION
# =====================================================

def require_admin(
    authorization: Optional[str] = Header(default=None)
):

    expected = os.getenv("ADMIN_TOKEN")

    if not expected:

        raise HTTPException(
            status_code=503,
            detail="Admin access is not configured"
        )

    if authorization != f"Bearer {expected}":

        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    return True


# =====================================================
# ROOT ROUTE
# =====================================================

@app.get("/")
def root():

    return {
        "message": "Customer Review API is running",
        "version": "2.0.0"
    }


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =====================================================
# EMAIL CONFIGURATION CHECK
# =====================================================

@app.get("/api/config")
def config():

    return {
        "google_review_url": GOOGLE_REVIEW_URL
    }


# =====================================================
# SUBMIT CUSTOMER FEEDBACK
# =====================================================

@app.post("/api/feedback")
def create_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db)
):

    try:

        item = Feedback(
            **payload.model_dump()
        )

        # Save customer feedback first

        db.add(item)

        db.commit()

        db.refresh(item)

        logger.info(
            "Feedback saved successfully. ID: %s",
            item.id
        )

        # Send Brevo notification

        email_sent, email_status = send_brevo_notification(
            item
        )

        return {

            "success": True,

            "id": item.id,

            "rating": item.rating,

            "email_sent": email_sent,

            "email_status": email_status

        }

    except Exception:

        db.rollback()

        logger.exception(
            "Feedback submission failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to save feedback"
        )


# =====================================================
# ADMIN: VIEW FEEDBACK
# =====================================================

@app.get(
    "/api/admin/feedback",
    dependencies=[Depends(require_admin)]
)
def list_feedback(
    db: Session = Depends(get_db),
    limit: int = 250
):

    limit = max(
        1,
        min(limit, 1000)
    )

    rows = (
        db.query(Feedback)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .all()
    )

    return [

        {
            "id": x.id,

            "name": x.name,

            "organization": x.organization,

            "email": x.email,

            "phone": x.phone,

            "rating": x.rating,

            "message": x.message,

            "created_at": x.created_at.isoformat()

        }

        for x in rows

    ]


# =====================================================
# ADMIN: DASHBOARD STATISTICS
# =====================================================

@app.get(
    "/api/admin/stats",
    dependencies=[Depends(require_admin)]
)
def stats(
    db: Session = Depends(get_db)
):

    rows = db.query(Feedback).all()

    total = len(rows)

    average = (
        round(
            sum(x.rating for x in rows) / total,
            2
        )
        if total
        else 0
    )

    distribution = {

        str(i): sum(
            1 for x in rows
            if x.rating == i
        )

        for i in range(1, 6)

    }

    return {

        "total": total,

        "average_rating": average,

        "distribution": distribution

    }


# =====================================================
# ADMIN: TEST BREVO EMAIL
# =====================================================

@app.post(
    "/api/admin/test-email",
    dependencies=[Depends(require_admin)]
)
def test_email():

    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    admin_email = os.getenv("ADMIN_EMAIL")

    if not all([api_key, sender_email, admin_email]):

        raise HTTPException(
            status_code=500,
            detail="Brevo environment variables are missing"
        )

    payload = {

        "sender": {
            "name": os.getenv(
                "SENDER_NAME",
                "Customer Reviews"
            ),
            "email": sender_email
        },

        "to": [
            {
                "email": admin_email
            }
        ],

        "subject": "Test Email - Customer Review System",

        "htmlContent": """
            <h2>Brevo Email Test Successful</h2>
            <p>Your Customer Review System email integration is working.</p>
        """

    }

    try:

        response = requests.post(

            "https://api.brevo.com/v3/smtp/email",

            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            },

            json=payload,

            timeout=25

        )

        logger.info(
            "Brevo test email status: %s",
            response.status_code
        )

        if response.status_code not in (200, 201, 202):

            logger.error(
                "Brevo test failed: %s",
                response.text[:2000]
            )

            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Brevo rejected test email",
                    "status": response.status_code,
                    "response": response.text[:1000]
                }
            )

        return {

            "success": True,

            "message": "Brevo accepted test email",

            "brevo_response": response.json()

        }

    except requests.exceptions.RequestException as exc:

        logger.exception("Brevo test email network error")

        raise HTTPException(
            status_code=502,
            detail=f"Brevo connection error: {str(exc)[:300]}"
        )
