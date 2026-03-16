import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.api_interface = os.getenv("API_INTERFACE", "openai_compatible")
        self.api_base_url = os.getenv(
            "API_BASE_URL",
            "https://open.bigmodel.cn/api/paas/v4/",
        )
        self.api_key = (
            os.getenv("API_KEY")
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or "EMPTY"
        )
        self.default_model = os.getenv("DEFAULT_MODEL")
        self.request_timeout = float(os.getenv("API_TIMEOUT", "60"))

        if not self.default_model:
            raise ValueError("Missing required environment variable: DEFAULT_MODEL")

    @property
    def supports_openai_compatible(self) -> bool:
        return self.api_interface == "openai_compatible"


settings = Settings()
