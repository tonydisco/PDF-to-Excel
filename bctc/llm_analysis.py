# -*- coding: utf-8 -*-
"""
Diễn giải tỉ số BCTC bằng LLM cloud (BYOK — người dùng tự cấp API key).

NGUYÊN TẮC RIÊNG TƯ (bất biến):
  • CHỈ gửi các TỈ SỐ tổng hợp (label/value/unit + Altman + cờ) — KHÔNG PDF,
    KHÔNG bản gốc, KHÔNG số dư tài khoản thô (VND).
  • Payload được serialize ở MỘT chỗ duy nhất (`build_payload`) → UI xem trước
    CHÍNH chuỗi sắp gửi → người dùng đồng ý đúng với bytes thật.
  • Egress (gọi mạng) chỉ xảy ra trong `analyze()`. /convert, /ratios 100% local.
  • Số do máy tính tất định (ratio_engine); LLM CHỈ diễn giải, không tính lại.

NGUỒN KEY (ưu tiên giảm dần):  tham số `key` (request body)
  → biến môi trường (ANTHROPIC_API_KEY / GOOGLE_API_KEY) → OS keychain (keyring).
Tách nguồn key như vậy để tính năng KHÔNG phụ thuộc keyring khi đóng gói:
nếu keychain trong binary đóng băng trục trặc, app vẫn truyền key qua body/env.
"""
import os
import json

KEYCHAIN_SERVICE = "BCTC-PDF-to-Excel"
PROVIDERS = ("anthropic", "google")
ENV_VARS = {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY"}

# Model gợi ý — người dùng đổi được trong Cài đặt. Phần tử [0] là mặc định.
DEFAULT_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-8"],
    "google": ["gemini-3-flash", "gemini-3.5-flash"],
}

SYSTEM = (
    "Bạn là chuyên gia phân tích báo cáo tài chính doanh nghiệp Việt Nam theo "
    "Thông tư 200/2014/TT-BTC. Bạn được cung cấp các TỈ SỐ đã tính sẵn (tất định) "
    "từ BCTC. Nhiệm vụ: DIỄN GIẢI các tỉ số này, đánh giá sức khỏe tài chính và "
    "rủi ro doanh nghiệp. TUYỆT ĐỐI KHÔNG tự tính lại hay bịa thêm con số — chỉ "
    "diễn giải dựa trên dữ liệu được cung cấp. Nếu một tỉ số là '—' (thiếu dữ "
    "liệu) thì nêu rõ là chưa đủ dữ liệu, không suy đoán. Trả lời hoàn toàn bằng "
    "tiếng Việt, súc tích, đúng JSON schema yêu cầu. "
    "risk_rating chỉ nhận: 'thap' (rủi ro thấp), 'trung_binh', hoặc 'cao'."
)


class LLMError(Exception):
    """Lỗi thân thiện (tiếng Việt) để trả thẳng về UI (HTTP 400)."""


# ---------------------------------------------------------------- schema
# Một hình dạng kết quả duy nhất cho CẢ Claude lẫn Gemini → Analysis.tsx render
# đồng nhất. Claude cần `additionalProperties:false` + enum; Gemini không nhận
# `additionalProperties` nên ta dựng 2 biến thể từ cùng một bộ thuộc tính.
_PROPS = {
    "risk_rating": {"type": "string", "description": "Một trong: thap | trung_binh | cao"},
    "risk_label": {"type": "string", "description": "Nhãn rủi ro ngắn bằng tiếng Việt"},
    "summary": {"type": "string", "description": "2-4 câu tổng quan sức khỏe tài chính"},
    "strengths": {"type": "array", "items": {"type": "string"}},
    "weaknesses": {"type": "array", "items": {"type": "string"}},
    "warnings": {"type": "array", "items": {"type": "string"}},
    "recommendations": {"type": "array", "items": {"type": "string"}},
}
_REQUIRED = list(_PROPS.keys())


def _claude_schema():
    props = json.loads(json.dumps(_PROPS))
    props["risk_rating"]["enum"] = ["thap", "trung_binh", "cao"]
    return {"type": "object", "properties": props, "required": _REQUIRED, "additionalProperties": False}


def _gemini_schema():
    return {"type": "object", "properties": json.loads(json.dumps(_PROPS)), "required": _REQUIRED}


# ---------------------------------------------------------------- key store
def _keyring():
    try:
        import keyring
        return keyring
    except Exception:
        return None


def resolve_key(provider, explicit=None):
    """request body → env var → OS keychain. Trả None nếu không tìm thấy."""
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ.get(ENV_VARS.get(provider, ""))
    if env and env.strip():
        return env.strip()
    kr = _keyring()
    if kr:
        try:
            v = kr.get_password(KEYCHAIN_SERVICE, provider)
            if v:
                return v.strip()
        except Exception:
            pass
    return None


def save_key(provider, key):
    if provider not in PROVIDERS:
        raise LLMError(f"Nhà cung cấp không hỗ trợ: {provider}")
    kr = _keyring()
    if not kr:
        raise LLMError("Máy chưa hỗ trợ lưu khoá an toàn (keyring). "
                       f"Có thể đặt biến môi trường {ENV_VARS[provider]} thay thế.")
    if not key or not key.strip():
        try:
            kr.delete_password(KEYCHAIN_SERVICE, provider)
        except Exception:
            pass
        return
    try:
        kr.set_password(KEYCHAIN_SERVICE, provider, key.strip())
    except Exception as e:
        raise LLMError(f"Không lưu được khoá vào keychain: {e}")


def _sdk_available(provider):
    try:
        if provider == "anthropic":
            import anthropic  # noqa: F401
        else:
            from google import genai  # noqa: F401
        return True
    except Exception:
        return False


def status():
    """Trạng thái cho UI: provider nào có key (qua bất kỳ nguồn nào) + SDK sẵn sàng."""
    out = {}
    for p in PROVIDERS:
        # phân biệt key trong keychain với key qua env (để UI hiển thị đúng)
        kr = _keyring()
        in_keychain = False
        if kr:
            try:
                in_keychain = bool(kr.get_password(KEYCHAIN_SERVICE, p))
            except Exception:
                in_keychain = False
        out[p] = {
            "hasKey": resolve_key(p) is not None,
            "inKeychain": in_keychain,
            "envVar": ENV_VARS[p],
            "sdk": _sdk_available(p),
            "models": DEFAULT_MODELS[p],
        }
    return out


# ---------------------------------------------------------------- payload
def build_payload(ratios_result):
    """Serialize tỉ số → chuỗi text. ĐÂY CHÍNH là dữ liệu sẽ gửi lên cloud.
    Chỉ lấy từ kết quả ratio_engine.compute() (KHÔNG dùng statements/số liệu thô)."""
    groups = ratios_result.get("groups", []) or []
    altman = ratios_result.get("altman")
    flags = ratios_result.get("flags", []) or []

    lines = ["CÁC TỈ SỐ TÀI CHÍNH (máy tính tất định, Thông tư 200):"]
    for g in groups:
        lines.append("")
        lines.append(f"# {g.get('label', g.get('key', ''))}")
        for it in g.get("items", []):
            v = it.get("value")
            unit = it.get("unit")
            if v is None:
                val = "—"
            elif unit == "%":
                val = f"{v}%"
            elif unit == "x":
                val = f"{v}×"
            else:
                val = str(v)
            lines.append(f"- {it.get('label')}: {val}   ({it.get('formula', '')})")

    if altman:
        lines.append("")
        lines.append("# Điểm rủi ro Altman Z''")
        lines.append(f"- Z'' = {altman.get('value')} → {altman.get('label')}")

    if flags:
        lines.append("")
        lines.append("# Cờ cảnh báo (theo ngưỡng máy)")
        for f in flags:
            lines.append(f"- {f}")

    return "\n".join(lines)


# ---------------------------------------------------------------- compare
COMPARE_SYSTEM = (
    "Bạn là chuyên gia phân tích tài chính. Bạn được cung cấp TỈ SỐ (đã tính tất "
    "định) của NHIỀU báo cáo — mỗi mục là một file (có thể là các năm khác nhau của "
    "cùng doanh nghiệp, hoặc các doanh nghiệp khác nhau). Hãy ĐỐI CHIẾU và SO SÁNH: "
    "nêu xu hướng, khác biệt, điểm mạnh/yếu tương đối và xếp hạng rủi ro giữa các mục. "
    "TUYỆT ĐỐI KHÔNG tự tính lại số. Trả lời hoàn toàn bằng tiếng Việt, đúng JSON schema."
)
_COMPARE_PROPS = {
    "summary": {"type": "string", "description": "Tổng quan so sánh các báo cáo"},
    "ranking": {"type": "array", "items": {"type": "string"},
                "description": "Xếp hạng: mỗi dòng 'Tên mục — mức rủi ro — lý do ngắn'"},
    "highlights": {"type": "array", "items": {"type": "string"}, "description": "Điểm nổi bật khi đối chiếu"},
    "recommendations": {"type": "array", "items": {"type": "string"}},
}
_COMPARE_REQUIRED = list(_COMPARE_PROPS.keys())


def _compare_schema(provider):
    base = {"type": "object", "properties": json.loads(json.dumps(_COMPARE_PROPS)), "required": _COMPARE_REQUIRED}
    if provider == "anthropic":
        base["additionalProperties"] = False
    return base


def build_compare_payload(parts):
    """parts = [(label, payload_text)] -> chuỗi gộp (CHỈ tỉ số, gắn nhãn từng mục)."""
    out = ["SO SÁNH NHIỀU BÁO CÁO TÀI CHÍNH (mỗi mục là 1 file đã tính tỉ số tất định):"]
    for label, text in parts:
        out.append("")
        out.append(f"========== {label} ==========")
        out.append(text)
    return "\n".join(out)


# ---------------------------------------------------------------- providers
def _call_claude(model, payload, key, system, schema):
    import anthropic
    client = anthropic.Anthropic(api_key=key)
    try:
        resp = client.messages.create(
            model=model or DEFAULT_MODELS["anthropic"][0],
            max_tokens=4000,  # tiếng Việt tokenize nặng -> để rộng tránh cắt
            system=system,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": payload}],
        )
    except anthropic.AuthenticationError:
        raise LLMError("Khoá Anthropic không hợp lệ. Kiểm tra lại API key trong Cài đặt.")
    except anthropic.PermissionDeniedError:
        raise LLMError("Khoá Anthropic không có quyền dùng model này.")
    except anthropic.NotFoundError:
        raise LLMError(f"Model '{model}' không tồn tại. Chọn model khác trong Cài đặt.")
    except anthropic.RateLimitError:
        raise LLMError("Anthropic đang giới hạn tần suất. Thử lại sau ít phút.")
    except anthropic.APIConnectionError:
        raise LLMError("Không kết nối được tới Anthropic (kiểm tra mạng).")
    except anthropic.APIStatusError as e:
        raise LLMError(f"Anthropic lỗi {e.status_code}: {getattr(e, 'message', '')}")
    if getattr(resp, "stop_reason", None) == "refusal":
        raise LLMError("Model từ chối phản hồi nội dung này.")
    if getattr(resp, "stop_reason", None) == "max_tokens":
        raise LLMError("Kết quả bị cắt do giới hạn token. Thử lại hoặc chọn model khác.")
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if not text:
        raise LLMError("Không nhận được nội dung phản hồi từ Anthropic.")
    return text


def _call_gemini(model, payload, key, system, schema):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    try:
        resp = client.models.generate_content(
            model=model or DEFAULT_MODELS["google"][0],
            contents=payload,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                max_output_tokens=4000,
            ),
        )
    except Exception as e:
        raise LLMError(_gemini_err(e))
    try:
        fr = str(getattr(resp.candidates[0], "finish_reason", "") or "")
        if "MAX_TOKENS" in fr.upper():
            raise LLMError("Kết quả bị cắt do giới hạn token. Thử lại hoặc chọn model khác.")
    except (AttributeError, IndexError, TypeError):
        pass
    text = getattr(resp, "text", None)
    if not text:
        raise LLMError("Gemini không trả về nội dung (có thể bị bộ lọc an toàn hoặc giới hạn token chặn).")
    return text


def _gemini_err(e):
    msg = str(e)
    low = msg.lower()
    if "api key" in low or "api_key" in low or "permission" in low or "401" in low or "403" in low:
        return "Khoá Google/Gemini không hợp lệ hoặc thiếu quyền. Kiểm tra lại API key."
    if "not found" in low or "404" in low:
        return "Model Gemini không tồn tại. Chọn model khác trong Cài đặt."
    if "quota" in low or "rate" in low or "429" in low:
        return "Gemini đã hết hạn mức/đang giới hạn tần suất. Thử lại sau."
    if "deadline" in low or "connect" in low or "network" in low or "unavailable" in low:
        return "Không kết nối được tới Gemini (kiểm tra mạng)."
    return f"Gemini lỗi: {msg}"


def _loads(text):
    try:
        return json.loads(text)
    except Exception:
        raise LLMError("Phản hồi không phải JSON hợp lệ.")


def _arrays(data, keys):
    for k in keys:
        if not isinstance(data.get(k), list):
            data[k] = []
        else:
            data[k] = [str(x) for x in data[k]]
    return data


def _normalize_single(data):
    rr = str(data.get("risk_rating", "")).strip().lower()
    data["risk_rating"] = rr if rr in ("thap", "trung_binh", "cao") else "trung_binh"
    for k in ("risk_label", "summary"):
        if not isinstance(data.get(k), str):
            data[k] = ""
    return _arrays(data, ("strengths", "weaknesses", "warnings", "recommendations"))


def _normalize_compare(data):
    if not isinstance(data.get("summary"), str):
        data["summary"] = ""
    return _arrays(data, ("ranking", "highlights", "recommendations"))


def _guard(provider, key):
    if provider not in PROVIDERS:
        raise LLMError(f"Nhà cung cấp không hỗ trợ: {provider}")
    if not key:
        raise LLMError("Chưa có API key. Vào Cài đặt để thêm khoá cho nhà cung cấp này.")
    if not _sdk_available(provider):
        raise LLMError(f"Thiếu SDK cho {provider} trong bản cài. Cần cài đặt lại ứng dụng.")


def analyze(provider, model, payload, key):
    """Diễn giải MỘT báo cáo. RAISE LLMError (thông điệp tiếng Việt) khi lỗi."""
    _guard(provider, key)
    if provider == "anthropic":
        text = _call_claude(model, payload, key, SYSTEM, _claude_schema())
    else:
        text = _call_gemini(model, payload, key, SYSTEM, _gemini_schema())
    return _normalize_single(_loads(text))


def analyze_compare(provider, model, payload, key):
    """So sánh NHIỀU báo cáo (payload đã gộp). RAISE LLMError khi lỗi."""
    _guard(provider, key)
    if provider == "anthropic":
        text = _call_claude(model, payload, key, COMPARE_SYSTEM, _compare_schema("anthropic"))
    else:
        text = _call_gemini(model, payload, key, COMPARE_SYSTEM, _compare_schema("google"))
    return _normalize_compare(_loads(text))
