import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except:
    MISTRAL_AVAILABLE = False
    print("❌ Mistral SDK no disponible")

from src.config import MISTRAL_KEY, MISTRAL_MODEL, MISTRAL_TEMP


class MistralClient:
    def __init__(self):
        if not MISTRAL_AVAILABLE:
            raise Exception("Mistral SDK faltante")

        if not MISTRAL_KEY:
            raise Exception("API key no configurada")

        self.client = Mistral(api_key=MISTRAL_KEY)
        self.model = MISTRAL_MODEL
        self.temp = MISTRAL_TEMP
        self.api_timeout = 180  # ✅ tiempo para respuestas médicas largas
        self.max_tokens = 32000  # ✅ ventana 32K tokens reales

    # ======================================================
    # ✅ LOG DE TOKENS
    # ======================================================
    def _log_token_usage(self, p, c, domain):
        total = p + c
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"📊 {ts} | Tokens: {total} | Dominio: {domain}")

        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/token_usage.log", "a", encoding="utf-8") as f:
                f.write(f"{ts}|{domain}|{p}|{c}|{total}\n")
        except:
            pass

    # ======================================================
    # ✅ PROMPTS
    # ======================================================
    def _sys(self, domain, mode):
        base = (
            "Eres un asistente médico experto basado en evidencia "
            "con precisión clínica, estilo académico y respaldo en guías vigentes."
        )

        if mode == "no_filter":
            base += " Responde directo sin suavizar lenguaje."

        return base

    def _user(self, q, d):
        return f"[{d}] {q}"

    # ======================================================
    # ✅ STREAMING ESTABLE
    # ======================================================
    def generate_stream(self, question, domain="medical", special=None):
        sys = self._sys(domain, special)
        usr = self._user(question, domain)

        stream = self.client.chat.stream(
            model=self.model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": usr}
            ],
            temperature=self.temp,
            max_tokens=self.max_tokens
        )

        full = ""

        for chunk in stream:
            try:
                delta = chunk.data.choices[0].delta.content
            except:
                continue

            if not delta:
                continue

            full += delta
            yield delta  # 🔥 mantiene la conexión viva (Render no corta)

        # token estimation
        p = len(sys + usr) // 4
        c = len(full) // 4
        self._log_token_usage(p, c, domain)

        yield "__STREAM_DONE__"

    # ======================================================
    # ✅ MODO NO-STREAM
    # ======================================================
    def generate(self, question, domain="medical", special=None):
        with ThreadPoolExecutor(max_workers=1) as executor:
            fut = executor.submit(self._call, question, domain, special)

            try:
                return fut.result(timeout=self.api_timeout)
            except TimeoutError:
                return "⏱️ Tiempo agotado — respuesta extremadamente larga."

    def _call(self, q, d, special):
        sys = self._sys(d, special)
        usr = self._user(q, d)

        r = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": usr}
            ],
            temperature=self.temp,
            max_tokens=self.max_tokens
        )

        try:
            self._log_token_usage(r.usage.prompt_tokens, r.usage.completion_tokens, d)
        except:
            pass

        return r.choices[0].message.content
