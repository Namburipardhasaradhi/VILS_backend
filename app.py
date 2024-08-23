from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import aiomysql
from fastapi.middleware.cors import CORSMiddleware
from email.message import EmailMessage
import smtplib
import ssl

email_sender = 'namburipardhu2103@gmail.com'
email_password = 'vzpo lggc nkeo wmvq'

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Email-sending function
def send_email_via_smtp(body: str, recipient: str):
    subject = 'Mail from video'
    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = recipient
    em['Subject'] = subject
    em.set_content(body, subtype="html")
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, recipient, em.as_string())

# Pydantic model for user
class User(BaseModel):
    first_name: str
    last_name: str
    email: str
    state: str
    country: str
    password: str
    id: Optional[int] = None

# Pydantic model for contacts
class Contact(BaseModel):
    user_id: int
    name: str
    contact_no: str
    email: str
    id: Optional[int] = None

class EmailSchema(BaseModel):
    recipient: str
    body: str

# Create a global variable for the connection pool
pool: Optional[aiomysql.Pool] = None

# Startup event to initialize the connection pool
@app.on_event("startup")
async def startup_event():
    global pool
    pool = await aiomysql.create_pool(
        host="bt3q16i8dgq1qu9ljnbr-mysql.services.clever-cloud.com",
        user="ulbtkvh95jjci6qb",
        password="9CGsx7OFUtzWCbqPUfAV",
        db="bt3q16i8dgq1qu9ljnbr",
        minsize=1,
        maxsize=10
    )

# Shutdown event to close the connection pool
@app.on_event("shutdown")
async def shutdown_event():
    global pool
    pool.close()
    await pool.wait_closed()

# Dependency for getting a database connection from the pool
async def get_db():
    async with pool.acquire() as conn:
        try:
            yield conn
        finally:
            conn.close()

# Create operation for user
@app.post("/users/", response_model=User)
async def create_user(user: User, db: aiomysql.Connection = Depends(get_db)):
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO user_data (
                first_name, last_name, email, state, country, password
            ) VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                user.first_name,
                user.last_name,
                user.email,
                user.state,
                user.country,
                user.password
            )
        )
        await db.commit()
        user.id = cur.lastrowid
    return user

# Read operation for user
@app.get("/users/", response_model=User)
async def read_user(email: str, password: str, db: aiomysql.Connection = Depends(get_db)):
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT * FROM user_data WHERE email=%s AND password=%s", 
            (email, password)
        )
        result = await cursor.fetchone()
        if result is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = User(
            id=result[0],
            first_name=result[1],
            last_name=result[2],
            email=result[3],
            state=result[4],
            country=result[5],
            password=result[6],
        )
        return user

# Create a contact
@app.post("/contacts/", response_model=Contact)
async def create_contact(contact: Contact, db: aiomysql.Connection = Depends(get_db)):
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO contacts (user_id, name, contact_no, email) 
               VALUES (%s, %s, %s, %s)""",
            (
                contact.user_id,
                contact.name,
                contact_no,
                contact.email
            )
        )
        await db.commit()
        contact.id = cur.lastrowid
    return contact

# Retrieve contacts for a specific user
@app.get("/contacts/{user_id}", response_model=List[Contact])
async def get_contacts(user_id: int, db: aiomysql.Connection = Depends(get_db)):
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT * FROM contacts WHERE user_id=%s",
            (user_id,)
        )
        results = await cur.fetchall()
        if not results:
            return []
        
        contacts = [Contact(
            id=row[0],
            user_id=row[1],
            name=row[2],
            contact_no=row[3],
            email=row[4]
        ) for row in results]
        
        return contacts

# Update a contact
@app.post("/contacts/{contact_id}", response_model=Contact)
async def update_contact(contact_id: int, updated_contact: Contact, db: aiomysql.Connection = Depends(get_db)):
    async with db.cursor() as cur:
        await cur.execute(
            """UPDATE contacts SET name=%s, contact_no=%s, email=%s 
               WHERE id=%s AND user_id=%s""",
            (
                updated_contact.name,
                updated_contact.contact_no,
                updated_contact.email,
                contact_id,
                updated_contact.user_id
            )
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found or not authorized")
        
        return updated_contact

# Delete a contact
@app.delete("/contacts/{contact_id}", response_model=dict)
async def delete_contact(contact_id: int, user_id: int, db: aiomysql.Connection = Depends(get_db)):
    async with db.cursor() as cur:
        await cur.execute(
            "DELETE FROM contacts WHERE id=%s AND user_id=%s",
            (contact_id, user_id)
        )
        await db.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found or not authorized")
        
        return {"message": "Contact deleted successfully"}

# Email sending endpoint
@app.post("/send-email/")
async def send_email(email_data: EmailSchema):
    send_email_via_smtp(email_data.body, email_data.recipient)
    return {"message": "Email sent successfully"}

