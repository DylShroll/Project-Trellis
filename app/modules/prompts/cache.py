from datetime import date

PROMPT_TTL = 86400  # 24 hours — matches the natural lifespan of a daily prompt


def plot_prompt_key(user_id: str, plot_id: str) -> str:
    # Scoped per-user so one user's cached prompt can never bleed into another's
    return f"prompts:plot:{user_id}:{plot_id}"


def daily_prompt_key(user_id: str) -> str:
    # Date baked into key = natural daily expiry + 24hr safety TTL
    return f"prompts:daily:{user_id}:{date.today().isoformat()}"
