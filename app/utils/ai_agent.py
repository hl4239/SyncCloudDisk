from app.core.config import settings


def get_ai_agent(ins: str, tools: [], cls: type = None):
    default_ai_config = settings.ai.config_dict[settings.ai.default]

    return Agent(
        name="Assistant",
        instructions=ins,
        model=LitellmModel(
            model=f'openai/{default_ai_config.model}',
            api_key=default_ai_config.key,
            base_url=default_ai_config.url,
        ),
        tools=tools,
        output_type=cls
    )