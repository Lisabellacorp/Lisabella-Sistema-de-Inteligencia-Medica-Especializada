# src/groq.py
class GroqClient:
    def __init__(self):
        pass

    def generate(self, question, domain, special_command=None):
        return "Temporal: GroqClient instalado."

    def generate_stream(self, question, domain, special_command=None):
        yield "Temporal stream desde GroqClient."
        yield "__STREAM_DONE__"

    def generate_chunk(self, prompt, domain, max_tokens=1200):
        return "Temporal chunk."
