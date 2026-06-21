from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

class ContactCreate(BaseModel):
    name: str
    current_company: str | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    x_handle: str | None = None
    relationship: str = "cold"
    notes: str | None = None

class ContactResponse(BaseModel):
    id: str
    name: str
    current_company: str | None = None
    role: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    x_handle: str | None = None
    relationship: str
    notes: str | None = None
    created_at: str

def get_contacts_router() -> APIRouter:
    router = APIRouter(prefix="/contacts", tags=["contacts"])

    @router.get("", response_model=list[ContactResponse])
    def list_contacts(
        company: str | None = Query(None),
        q: str | None = Query(None),
    ):
        from ...db.session import get_session
        from ...db.models import Contact
        with get_session() as db:
            query = db.query(Contact)
            if company:
                query = query.filter(Contact.current_company.ilike(f"%{company}%"))
            if q:
                query = query.filter(
                    (Contact.name.ilike(f"%{q}%")) |
                    (Contact.current_company.ilike(f"%{q}%")) |
                    (Contact.role.ilike(f"%{q}%"))
                )
            contacts = query.order_by(Contact.created_at.desc()).all()
            return [
                ContactResponse(
                    id=c.id,
                    name=c.name,
                    current_company=c.current_company,
                    role=c.role,
                    email=c.email,
                    linkedin_url=c.linkedin_url,
                    x_handle=c.x_handle,
                    relationship=c.relationship,
                    notes=c.notes,
                    created_at=c.created_at.isoformat()
                )
                for c in contacts
            ]

    @router.post("", response_model=ContactResponse)
    def create_contact(body: ContactCreate):
        from ...db.session import get_session
        from ...db.models import Contact
        with get_session() as db:
            contact = Contact(
                id=str(uuid.uuid4()),
                name=body.name,
                current_company=body.current_company,
                role=body.role,
                email=body.email,
                linkedin_url=body.linkedin_url,
                x_handle=body.x_handle,
                relationship=body.relationship,
                notes=body.notes,
                created_at=datetime.now(timezone.utc)
            )
            db.add(contact)
            db.commit()
            return ContactResponse(
                id=contact.id,
                name=contact.name,
                current_company=contact.current_company,
                role=contact.role,
                email=contact.email,
                linkedin_url=contact.linkedin_url,
                x_handle=contact.x_handle,
                relationship=contact.relationship,
                notes=contact.notes,
                created_at=contact.created_at.isoformat()
            )

    @router.put("/{contact_id}", response_model=ContactResponse)
    def update_contact(contact_id: str, body: ContactCreate):
        from ...db.session import get_session
        from ...db.models import Contact
        with get_session() as db:
            contact = db.query(Contact).filter_by(id=contact_id).first()
            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")
            contact.name = body.name
            contact.current_company = body.current_company
            contact.role = body.role
            contact.email = body.email
            contact.linkedin_url = body.linkedin_url
            contact.x_handle = body.x_handle
            contact.relationship = body.relationship
            contact.notes = body.notes
            db.commit()
            return ContactResponse(
                id=contact.id,
                name=contact.name,
                current_company=contact.current_company,
                role=contact.role,
                email=contact.email,
                linkedin_url=contact.linkedin_url,
                x_handle=contact.x_handle,
                relationship=contact.relationship,
                notes=contact.notes,
                created_at=contact.created_at.isoformat()
            )

    @router.delete("/{contact_id}")
    def delete_contact(contact_id: str):
        from ...db.session import get_session
        from ...db.models import Contact
        with get_session() as db:
            contact = db.query(Contact).filter_by(id=contact_id).first()
            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")
            db.delete(contact)
            db.commit()
            return {"deleted": 1}

    return router
