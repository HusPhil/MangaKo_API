from fastapi import APIRouter, Depends, HTTPException, Form
# from app.core.security import create_access_token

router = APIRouter()

@router.get("/")
def test_auth():
    return {'message': 'auth route is working!'}

