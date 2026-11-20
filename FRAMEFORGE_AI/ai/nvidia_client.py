"""NVIDIA NIM client (OpenAI-compatible). Retries, rate-limit handling, sanitised errors."""
import time

from ai.response_parser import ParseError, parse_model


class NvidiaError(Exception):
    """User-presentable API failure. `fatal` means retrying other chunks is pointless."""

    def __init__(self, message, fatal=False):
        super().__init__(message)
        self.fatal = fatal


class NvidiaClient:
    def __init__(self, api_key, model, base_url, timeout=120, max_retries=3, disable_thinking=True,
                 max_tokens=6000):
        self.api_key = (api_key or "").strip()
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.disable_thinking = disable_thinking
        self.max_tokens = max_tokens
        self._client = None
        self._thinking_param_ok = True

    # ---- plumbing ----
    def _sanitize(self, msg: str) -> str:
        msg = str(msg)
        return msg.replace(self.api_key, "***") if self.api_key else msg

    def _get(self):
        if not self.api_key:
            raise NvidiaError("No NVIDIA API key configured. Set NVIDIA_API_KEY in .env or Settings.", fatal=True)
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise NvidiaError("The 'openai' package is not installed: pip install openai", fatal=True) from exc
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout, max_retries=0)
        return self._client

    def chat(self, messages, temperature=0.1, max_tokens=None) -> str:
        import openai
        client = self._get()
        last_msg = "unknown error"
        for attempt in range(self.max_retries + 1):
            kwargs = dict(model=self.model, messages=messages, temperature=temperature,
                          max_tokens=max_tokens or self.max_tokens)
            if self.disable_thinking and self._thinking_param_ok:
                kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
            try:
                resp = client.chat.completions.create(**kwargs)
                msg = resp.choices[0].message
                text = (msg.content or "").strip()
                if not text:
                    raise NvidiaError("The model returned an empty response.")
                return text
            except openai.RateLimitError as exc:
                last_msg = "Rate limit reached"
                wait = 5 * (2 ** attempt)
                ra = getattr(getattr(exc, "response", None), "headers", {}).get("retry-after")
                if ra and str(ra).isdigit():
                    wait = max(wait, int(ra))
                time.sleep(min(wait, 60))
            except (openai.APITimeoutError, openai.APIConnectionError):
                last_msg = "Request timed out or the network is unreachable"
                time.sleep(2 * (2 ** attempt))
            except openai.APIStatusError as exc:
                code = exc.status_code
                if code in (401, 403):
                    raise NvidiaError("NVIDIA authentication failed - check NVIDIA_API_KEY.", fatal=True) from None
                if code == 404:
                    raise NvidiaError(f"Model '{self.model}' was not found or is not available to this key.",
                                      fatal=True) from None
                if code == 400 and "extra_body" in kwargs and self._thinking_param_ok:
                    self._thinking_param_ok = False  # model rejects the thinking switch; retry without it
                    continue
                if code >= 500 or code == 429:
                    last_msg = f"NVIDIA service error ({code})"
                    time.sleep(2 * (2 ** attempt))
                else:
                    raise NvidiaError(self._sanitize(f"NVIDIA API rejected the request ({code}): "
                                                     f"{getattr(exc, 'message', exc)}")) from None
        raise NvidiaError(f"{last_msg} after {self.max_retries + 1} attempts. Please retry.")

    def chat_json(self, messages, model_cls, max_repairs=1, max_tokens=None) -> dict:
        """Chat -> JSON extraction -> Pydantic validation, with one corrective re-prompt."""
        msgs = list(messages)
        error = None
        for attempt in range(max_repairs + 1):
            text = self.chat(msgs, max_tokens=max_tokens)
            try:
                return parse_model(text, model_cls)
            except ParseError as exc:
                error = exc
                msgs = msgs + [{"role": "assistant", "content": text[:6000]},
                               {"role": "user", "content": f"Your reply was not usable: {exc}. Reply again with ONLY "
                                                           "the corrected, complete JSON object. No commentary."}]
        raise NvidiaError(f"The model returned invalid structured data: {error}")

    # ---- diagnostics ----
    def test_connection(self) -> dict:
        t0 = time.time()
        result = {"ok": False, "message": "", "model_listed": None, "latency_s": None}
        try:
            client = self._get()
            try:
                ids = [m.id for m in client.models.list().data]
                result["model_listed"] = self.model in ids
            except Exception:
                result["model_listed"] = None  # listing is optional; the real call below decides
            reply = self.chat([{"role": "user", "content": "Reply with the single word: OK"}], max_tokens=64)
            result.update(ok=True, message=f"Model responded: {reply[:60]!r}", latency_s=round(time.time() - t0, 2))
        except NvidiaError as exc:
            result["message"] = self._sanitize(str(exc))
        except Exception as exc:
            result["message"] = self._sanitize(f"Unexpected error: {exc.__class__.__name__}: {exc}")
        return result
