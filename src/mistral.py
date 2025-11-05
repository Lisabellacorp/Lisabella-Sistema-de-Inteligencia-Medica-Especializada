import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from mistralai import Mistral

# ================================
# Load config / env vars
# ================================
try:
    from src.config import MISTRAL_KEY, MISTRAL_MODEL, MISTRAL_TEMP
except ImportError:
    MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
    MISTRAL_TEMP = float(os.environ.get("MISTRAL_TEMP", "0.3"))

if not MISTRAL_KEY:
    raise Exception("❌ Falta MISTRAL_API_KEY")

# ================================
# Mistral Client
# ================================
class MistralClient:
    def __init__(self):
        self.client = Mistral(api_key=MISTRAL_KEY)
        self.model = MISTRAL_MODEL
        self.temp = MISTRAL_TEMP
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 180

        print(f"✅ Mistral listo | Modelo: {self.model}")

    # --- Logging tokens ---
    def _log(self, p, c, domain):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        total = p + c
        print(f"📊 {ts} | {domain} | Prompt={p} | Completion={c} | Total={total}")
        try:
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{ts}|{domain}|{p}|{c}|{total}\n")
        except:
            pass

    # ================================
    # STREAM MODE
    # ================================
    def generate_stream(self, question, domain, special=None):
        system = self._system(domain, special)
        user = question

        stream = self.client.chat.stream(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=self.temp,
            max_tokens=32000
        )

        full_text = ""
        prompt_tokens = 0
        completion_tokens = 0

        for event in stream:
            # Token event
            if event.type == "token":
                completion_tokens += 1
                token = event.token
                full_text += token
                yield token
            
            # Completed event
            elif event.type == "response.completed":
                prompt_tokens = event.response.usage.prompt_tokens
                completion_tokens = event.response.usage.completion_tokens
                self._log(prompt_tokens, completion_tokens, domain)
                yield "__STREAM_DONE__"
                break

    # ================================
    # SYNC MODE
    # ================================
    def generate(self, question, domain, special=None):
        for _ in range(self.max_retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as exe:
                    fut = exe.submit(self._call, question, domain, special)
                    return fut.result(timeout=self.timeout)
            except TimeoutError:
                time.sleep(self.retry_delay)
        return "⏱️ Timeout, intenta de nuevo."

    def _call(self, question, domain, special):
        system = self._system(domain, special)

        r = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question}
            ],
            temperature=self.temp,
            max_tokens=32000
        )

        u = r.usage
        self._log(u.prompt_tokens, u.completion_tokens, domain)
        return r.choices[0].message.content

    # ================================
    # System prompt builder
    # ================================
    def _system(self, domain, special):
        base = f"Eres Lisabella, asistente médico experto. Dominio: {domain}."
        if special:
            base += f"\nComando: {special}"
        return base
