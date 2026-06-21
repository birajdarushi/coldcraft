from fastapi import APIRouter, HTTPException, Query
from ..schemas import ContactCreate, ContactUpdate, ContactResponse, serialize_contact


def get_network_router(campaigns_repo) -> APIRouter:
    router = APIRouter(prefix="/network", tags=["network"])

    @router.get("/contacts", response_model=list[ContactResponse])
    def list_contacts(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        contacts = campaigns_repo.list_contacts(limit=limit, offset=offset)
        return [serialize_contact(c) for c in contacts]

    @router.post("/contacts", response_model=ContactResponse)
    def create_contact(body: ContactCreate):
        c = campaigns_repo.create_contact(
            name=body.name,
            current_company=body.current_company,
            role=body.role,
            email=body.email,
            linkedin_url=body.linkedin_url,
            x_handle=body.x_handle,
            relationship=body.relationship,
            notes=body.notes,
        )
        return serialize_contact(c)

    @router.put("/contacts/{contact_id}", response_model=ContactResponse)
    def update_contact(contact_id: str, body: ContactUpdate):
        # Only pass non-None update values to the repo
        update_data = {k: v for k, v in body.model_dump().items() if v is not None}
        c = campaigns_repo.update_contact(contact_id, update_data)
        if not c:
            raise HTTPException(status_code=404, detail="Contact not found")
        return serialize_contact(c)

    @router.delete("/contacts/{contact_id}")
    def delete_contact(contact_id: str):
        success = campaigns_repo.delete_contact(contact_id)
        if not success:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"ok": True, "deleted": contact_id}

    @router.get("/search", response_model=list[ContactResponse])
    def search_contacts(company: str = Query(..., description="Company name to search contacts by")):
        contacts = campaigns_repo.search_contacts_by_company(company)
        return [serialize_contact(c) for c in contacts]

    return router
