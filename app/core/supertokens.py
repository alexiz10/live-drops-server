from supertokens_python import init, InputAppInfo, SupertokensConfig
from supertokens_python.recipe import emailpassword, session

from app.core.config import settings

def init_supertokens():
    """
    Initializes the SuperTokens SDK.
    This must be called before the FastAPI app is created.
    """
    init(
        app_info=InputAppInfo(
            app_name=settings.PROJECT_NAME,
            api_domain="http://localhost:8000",
            website_domain="http://localhost:5173",
            api_base_path="/auth",
            website_base_path="/auth"
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=settings.SUPERTOKENS_CONNECTION_URI,
        ),
        framework="fastapi",
        recipe_list=[
            session.init(),
            emailpassword.init()
        ],
        mode="asgi"
    )
