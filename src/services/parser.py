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

    # Fallback: JSON truncado — tenta recuperar dados parciais fechando as
    # estruturas abertas no ultimo ponto valido (fora de string, sem listas
    # abertas). Util quando o LLM atinge o limite de tokens no meio da resposta.
    start = cleaned.find("{")
    if start != -1:
        fragment = cleaned[start:]
        depth_brace = 0
        depth_bracket = 0
        in_string = False
        escape_next = False
        safe_cuts = []  # posicoes onde fechar produziria JSON valido

        for i, ch in enumerate(fragment):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == "\"":
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth_brace += 1
            elif ch == "}":
                depth_brace -= 1
                if depth_brace >= 1 and depth_bracket == 0:
                    safe_cuts.append(i + 1)
            elif ch == "[":
                depth_bracket += 1
            elif ch == "]":
                depth_bracket -= 1
                if depth_brace >= 1 and depth_bracket == 0:
                    safe_cuts.append(i + 1)

        for cut in reversed(safe_cuts):
            frag = fragment[:cut]
            db, dbr, ins, esc = 0, 0, False, False
            for ch in frag:
                if esc:
                    esc = False
                    continue
                if ch == "\\" and ins:
                    esc = True
                    continue
                if ch == "\"":
                    ins = not ins
                    continue
                if ins:
                    continue
                if ch == "{": db += 1
                elif ch == "}": db -= 1
                elif ch == "[": dbr += 1
                elif ch == "]": dbr -= 1
            closing = "]" * max(0, dbr) + "}" * max(0, db)
            try:
                data = json.loads(frag + closing)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue

        # Última tentativa: os "safe_cuts" acima só existem depois de um
        # ']'/'}'  completo. Se o corte aconteceu no meio de uma string ou
        # de um valor (ex.: `"pontos_fracos": ["algo trunc`), não existe
        # nenhum safe_cut após esse ponto e as tentativas acima falham
        # todas. Aqui descartamos esse último elemento incompleto cortando
        # na última vírgula em nível seguro (fora de string, com pelo
        # menos um objeto aberto) e fechamos o que sobrou.
        depth_brace = depth_bracket = 0
        in_string = False
        escape_next = False
        last_comma_safe = None
        for i, ch in enumerate(fragment):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == "\"":
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth_brace += 1
            elif ch == "}":
                depth_brace -= 1
            elif ch == "[":
                depth_bracket += 1
            elif ch == "]":
                depth_bracket -= 1
            elif ch == "," and depth_brace >= 1:
                last_comma_safe = i

        if last_comma_safe is not None:
            frag = fragment[:last_comma_safe]
            db_, dbr_, ins_, esc_ = 0, 0, False, False
            for ch in frag:
                if esc_:
                    esc_ = False
                    continue
                if ch == "\\" and ins_:
                    esc_ = True
                    continue
                if ch == "\"":
                    ins_ = not ins_
                    continue
                if ins_:
                    continue
                if ch == "{": db_ += 1
                elif ch == "}": db_ -= 1
                elif ch == "[": dbr_ += 1
                elif ch == "]": dbr_ -= 1
            closing = ("]" * max(0, dbr_)) + ("}" * max(0, db_))
            try:
                data = json.loads(frag + closing)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

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