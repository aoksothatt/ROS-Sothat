from fastapi import APIRouter, Depends, status
from app.account.schemas import (
    AccountRegister,
    AccountLogin,
    GuestRegister,
    AccountOut,
    TokenResponse,
    OTPRequest,
    OTPResponse,
    OTPVerifyRequest,
)
from app.account.service import AccountService, get_account_service, get_current_account
from app.account.rate_limiter import (
    rate_limit_login,
    rate_limit_register,
    rate_limit_otp_request,
    rate_limit_otp_verify,
)
from app.account.models import Account

router = APIRouter(prefix="/account", tags=["Account & Auth"])

# -------------------------------------------------------------
# Traditional & Guest Auth Endpoints
# -------------------------------------------------------------

@router.post(
    "/register",
    response_model=AccountOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_register)]
)
async def register(
    req: AccountRegister,
    service: AccountService = Depends(get_account_service)
):
    """Register a new private server account using unique credentials."""
    return await service.register(req)

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_login)]
)
async def login(
    req: AccountLogin,
    service: AccountService = Depends(get_account_service)
):
    """Authenticate account credentials and issue a Bearer token."""
    return await service.authenticate(req)

@router.post(
    "/guest",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_register)]
)
async def guest_login(
    req: GuestRegister = GuestRegister(),
    service: AccountService = Depends(get_account_service)
):
    """Instantly register and authenticate as a guest player."""
    _, token = await service.register_guest(req.device_id)
    return token

# -------------------------------------------------------------
# Email OTP Endpoints (Phase P02)
# -------------------------------------------------------------

@router.post(
    "/otp/request",
    response_model=OTPResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_otp_request)]
)
async def request_otp(
    req: OTPRequest,
    service: AccountService = Depends(get_account_service)
):
    """
    Request a 6-digit email OTP for passwordless registration or login.
    Enforces cooldown and generic enumeration-resistant response.
    """
    return await service.request_otp(req)

@router.post(
    "/otp/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_otp_verify)]
)
async def verify_otp(
    req: OTPVerifyRequest,
    service: AccountService = Depends(get_account_service)
):
    """
    Verify 6-digit email OTP and authenticate or register player account.
    """
    return await service.verify_otp(req)

# -------------------------------------------------------------
# Account Profile
# -------------------------------------------------------------

@router.get("/me", response_model=AccountOut)
async def get_my_account(
    current_account: Account = Depends(get_current_account)
):
    """Retrieve account details for the authenticated user."""
    return AccountOut(
        id=current_account.id,
        username=current_account.username,
        email=current_account.email,
        role=current_account.role,
        is_banned=current_account.is_banned,
        created_at=current_account.created_at,
        last_login=current_account.last_login,
        has_character=current_account.character is not None
    )
