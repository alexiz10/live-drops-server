from supertokens_python import init, InputAppInfo, SupertokensConfig
from supertokens_python.recipe import emailpassword, session
from supertokens_python.recipe.emailpassword.interfaces import APIInterface, APIOptions, SignUpPostOkResult
from supertokens_python.recipe.session.interfaces import SessionContainer
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import User

def override_email_password_apis(original_implementation: APIInterface):
    original_sign_up_post = original_implementation.sign_up_post

    async def sign_up_post(
            form_fields: List[Any],
            tenant_id: str,
            session: Optional[SessionContainer],
            should_try_linking_with_session_user: Optional[bool],
            api_options: APIOptions,
            user_context: Dict[str, Any]
    ):
        # let SuperTokens handle the complex cryptography and validation first
        response = await original_sign_up_post(
            form_fields,
            tenant_id,
            session,
            should_try_linking_with_session_user,
            api_options,
            user_context
        )

        if getattr(response, "is_ok", False) or isinstance(response, SignUpPostOkResult):
            st_user_id = response.user.id

            email = next((field.value for field in form_fields if field.id == "email"), None)

            if email:
                async with AsyncSessionLocal() as db:
                    new_user = User(supertokens_id=st_user_id, email=email)
                    db.add(new_user)
                    await db.commit()
                    print(f"SUCCESS: Synchronized new user {email} to PostgreSQL.")

        return response

    original_implementation.sign_up_post = sign_up_post
    return original_implementation

def init_supertokens():
    """
    Initializes the SuperTokens SDK.
    This must be called before the FastAPI app is created.
    """
    init(
        app_info=InputAppInfo(
            app_name=settings.PROJECT_NAME,
            api_domain=settings.API_DOMAIN,
            website_domain=settings.FRONTEND_URL,
            api_base_path="/auth",
            website_base_path="/auth"
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=settings.SUPERTOKENS_CONNECTION_URI,
            api_key=settings.SUPERTOKENS_API_KEY,
        ),
        framework="fastapi",
        recipe_list=[
            session.init(),
            emailpassword.init(
                override=emailpassword.InputOverrideConfig(
                    apis=override_email_password_apis
                )
            )
        ],
        mode="asgi"
    )
