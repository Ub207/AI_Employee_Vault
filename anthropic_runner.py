import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

VAULT = Path(__file__).parent.resolve()
SECRETS = VAULT / "Secrets"

def get_prompt_from_args(argv: list[str]) -> str:
    if "-p" in argv:
        i = argv.index("-p")
        if i + 1 < len(argv):
            return argv[i + 1]
    if "--prompt" in argv:
        i = argv.index("--prompt")
        if i + 1 < len(argv):
            return argv[i + 1]
    return "Process the requested task per SKILL.md"

def main() -> None:
    load_dotenv(SECRETS / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ANTHROPIC_API_KEY missing in Secrets/.env")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    user_prompt = get_prompt_from_args(sys.argv)
    skill_path = VAULT / "SKILL.md"
    system_text = ""
    if skill_path.exists():
        try:
            system_text = skill_path.read_text(encoding="utf-8")
        except Exception:
            system_text = ""

    msg = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1000,
        system=system_text or "Follow the AI Employee Vault operating manual.",
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )
    out = "".join([blk.text for blk in msg.content if getattr(blk, "type", "") == "text"])
    print(out or "(no output)")

if __name__ == "__main__":
    main()
