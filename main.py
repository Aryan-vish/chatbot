import auth
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from database import Base, engine, get_db
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
import llm
import models
import schemas
from sqlalchemy.orm import Session


templates = Jinja2Templates(directory="templates")




# =========================================================
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(title="Employee CRUD API with JWT Authentication")


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {"message": "Employee CRUD API with JWT is running"}


# =========================================================
# REGISTRATION PAGE
# =========================================================

@app.get("/register")
def register_page():
    return FileResponse("templates/register.html")


# =========================================================
# REGISTER USER
# =========================================================

@app.post("/register")
def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()

    existing_user = (
        db.query(models.User).filter(models.User.email == email).first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = models.User(
        name=name,
        email=email,
        hashed_password=auth.hash_password(password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
        },
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form_data.username.strip().lower()

    user = db.query(models.User).filter(models.User.email == email).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    password_is_correct = auth.verify_password(
        form_data.password,
        user.hashed_password,
    )

    if not password_is_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# =========================================================
# CURRENT LOGGED-IN USER
# =========================================================

@app.get("/users/me")
def read_current_user(
    current_user: models.User = Depends(auth.get_current_user),
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }


# =========================================================
# CREATE EMPLOYEE
# =========================================================

@app.post(
    "/employees",
    response_model=schemas.EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    employee: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    new_employee = models.Employee(
        name=employee.name,
        role=employee.role,
        salary=employee.salary,
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return new_employee


# =========================================================
# GET ALL EMPLOYEES
# =========================================================

@app.get(
    "/employees",
    response_model=list[schemas.EmployeeResponse],
)
def get_all_employees(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Employee).all()


# =========================================================
# GET ONE EMPLOYEE
# =========================================================

@app.get(
    "/employees/{employee_id}",
    response_model=schemas.EmployeeResponse,
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == employee_id)
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


# =========================================================
# UPDATE EMPLOYEE
# =========================================================

@app.put(
    "/employees/{employee_id}",
    response_model=schemas.EmployeeResponse,
)
def update_employee(
    employee_id: int,
    updated_employee: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == employee_id)
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    employee.name = updated_employee.name
    employee.role = updated_employee.role
    employee.salary = updated_employee.salary

    db.commit()
    db.refresh(employee)

    return employee


# =========================================================
# DELETE EMPLOYEE
# =========================================================

@app.delete("/employees/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == employee_id)
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    db.delete(employee)
    db.commit()

    return {"message": "Employee deleted successfully"}


# =========================================================
# CHAT WITH GROQ (MULTI-TURN CONVERSATION)
# =========================================================

@app.post("/chat")
def chat(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # 1. CREATE NEW CONVERSATION OR LOAD EXISTING ONE
    if request.conversation_id is None:
        conversation = models.Conversation(
            user_id=current_user.id,
            title=request.message[:50],
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    else:
        conversation = (
            db.query(models.Conversation)
            .filter(
                models.Conversation.id == request.conversation_id,
                models.Conversation.user_id == current_user.id,
            )
            .first()
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

    # 2. SAVE USER MESSAGE
    user_message = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        model="groq",
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # 3. GET PREVIOUS CONVERSATION HISTORY
    previous_messages = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.id.asc())
        .all()
    )

    # 4. PREPARE HISTORY FOR GROQ
    groq_messages = [
        {"role": "system", "content": "You are a helpful AI assistant."}
    ]

    for message in previous_messages:
        if message.role in ["user", "assistant"]:
            groq_messages.append(
                {"role": str(message.role), "content": str(message.content)}
            )

    # 5. CALL GROQ API
    try:
        ai_response = llm.ask_groq(groq_messages)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq API error: {str(e)}",
        )

    # 6. SAVE AI RESPONSE
    assistant_message = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        model="groq",
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # 7. RETURN RESPONSE
    return {
        "conversation_id": conversation.id,
        "user_message": request.message,
        "ai_response": ai_response,
        "model": "groq",
    }


# =========================================================
# GET ALL CONVERSATIONS OF LOGGED-IN USER
# =========================================================

@app.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == current_user.id)
        .order_by(models.Conversation.id.desc())
        .all()
    )


# =========================================================
# GET MESSAGES OF ONE CONVERSATION
# =========================================================

@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    conversation = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.id.asc())
        .all()
    )

@app.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        auth.get_current_user
    ),
):
    conversation = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id,
        )
        .first()
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # First delete all messages
    db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).delete()

    # Then delete conversation
    db.delete(conversation)
    db.commit()

    return {
        "message": "Conversation deleted successfully",
        "conversation_id": conversation_id,
    }

@app.get("/chat-ui")
def chat_ui(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="chat.html"
    )

@app.get("/login-ui")
def login_ui(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )