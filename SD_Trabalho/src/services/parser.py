import re
import json


def extrair_json(texto):
    """Extract the first valid JSON object from LLM output (handles code fences, surrounding text)."""
    cleaned = re.sub(r"```(?:json)?|```", "", texto, flags=re.IGNORECASE).strip()
    decoder = json.JSONDecoder()

    # Fast path: entire string is valid JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Scan for first valid JSON object
    for idx, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(cleaned[idx:])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    return {"error": "Falha ao interpretar resposta da IA", "raw": texto}


def extrair_texto_curriculo(raw):
    """Extract 'curriculo_otimizado' field from LLM response."""
    data = extrair_json(raw)
    if "curriculo_otimizado" in data:
        return data["curriculo_otimizado"], data.get("melhorias", [])

    # Fallback: regex for malformed JSON
    cleaned = re.sub(r"```(?:json)?|```", "", raw, flags=re.IGNORECASE).strip()
    m = re.search(r'"curriculo_otimizado"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned, re.DOTALL)
    if m:
        texto = m.group(1).replace("\\n", "\n").replace('\\"', '"')
        return texto, []

    return raw, []