import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from mistralai import Mistral

try:
    from src.config import MISTRAL_KEY, MISTRAL_MODEL, MISTRAL_TEMP
except ImportError:
    MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")
    MISTRAL_TEMP = float(os.environ.get("MISTRAL_TEMP", "0.3"))

if not MISTRAL_KEY:
    raise Exception("❌ ERROR: Falta variable de entorno MISTRAL_API_KEY")

class MistralClient:
    def __init__(self):
        self.client = Mistral(api_key=MISTRAL_KEY)
        self.model = MISTRAL_MODEL
        self.temp = MISTRAL_TEMP
        self.max_retries = 3
        self.base_retry_delay = 2
        self.api_timeout = 180  # 3 minutos

        print(f"✅ MistralClient listo | Modelo: {self.model}")

    def _log(self, prompt, completion, domain):
        total = prompt + completion
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"📊 {ts} Tokens: P={prompt} C={completion} T={total} | {domain}")
        try:
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{ts}|{domain}|{prompt}|{completion}|{total}\n")
        except:
            pass

    def generate_stream(self, question, domain, special=None):
        system = self._build_system(domain, special)
        user = self._build_user(question, domain, special)

        stream = self.client.chat.stream(
            model=self.model,
            messages=[{"role": "system","content": system},{"role":"user","content": user}],
            temperature=self.temp,
            max_tokens=32000
        )

        acc = ""
        count = 0

        for chunk in stream:
            if hasattr(chunk, "data") and chunk.data and hasattr(chunk.data, "choices"):
                delta = chunk.data.choices[0].delta.content
                if delta:
                    count += 1
                    acc += delta
                    yield delta

        # estimación de tokens
        p = len(system + user) // 4
        c = len(acc) // 4
        self._log(p, c, domain)

        yield "__STREAM_DONE__"

    def generate(self, question, domain, special=None):
        for _ in range(self.max_retries):
            try:
                with ThreadPoolExecutor(max_workers=1) as exe:
                    fut = exe.submit(
                        self._call,
                        question,
                        domain,
                        special,
                        32000
                    )
                    return fut.result(timeout=self.api_timeout)
            except TimeoutError:
                time.sleep(self.base_retry_delay)
        return "⏱️ Timeout — intenta de nuevo."

    def _call(self, question, domain, special, max_tokens):
        system = self._build_system(domain, special)
        user = self._build_user(question, domain, special)

        r = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "system","content": system},{"role":"user","content": user}],
            temperature=self.temp,
            max_tokens=max_tokens
        )

        u = r.usage
        self._log(u.prompt_tokens, u.completion_tokens, domain)

        return r.choices[0].message.content

    def _build_system(self, domain, special):
        base = f"Eres Lisabella, asistente médico experto. Dominio: {domain}"
        if special:
            base += f"\nComando especial: {special}"
        return base

    def _build_user(self, q, domain, special):
        return q
