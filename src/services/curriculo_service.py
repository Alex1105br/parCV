"""
Serviços relacionados à gestão centralizada de currículos.

Fluxo principal (usado em /analisar e /entrevista/gerar-plano):
    curriculo = obter_ou_criar_curriculo(user_id, texto, finalidade)

Também expõe helpers para a rota /curriculos:
    renomear_label(curriculo, novo_label, user_id) → (ok, erro)
"""
from __future__ import annotations

import re
from datetime import datetime

from src.logging_config import logger
from src.models.curriculo import Curriculo
from src.models.db import db
from src.services.model import call_model
from src.utils import sanitize_text


# ---------------------------------------------------------------------------
# Geração automática de label
# ---------------------------------------------------------------------------

def gerar_label(texto_curriculo: str, finalidade: str | None = None) -> str:
    """Gera uma label curta (máx 50 chars) para o currículo usando a LLM.

    `finalidade` é a descrição breve que o usuário forneceu ao enviar o
    arquivo (ex: "Vaga de backend no Nubank", "Processo seletivo UFAM").
    Quando presente é o principal sinal para a label; o texto do currículo
    serve de suporte para inferir cargo/área se a finalidade for vaga.

    Nunca retorna vazio — há dois fallbacks determinísticos antes de desistir.
    """
    finalidade = (finalidade or "").strip()
    primeira_linha = (texto_curriculo or "").split("\n")[0].strip()

    partes: list[str] = []
    if finalidade:
        partes.append(f"Finalidade informada pelo usuário: {finalidade}")
    if primeira_linha:
        partes.append(f"Primeira linha do currículo: {primeira_linha}")
    contexto = "\n".join(partes)

    label: str | None = None
    if contexto:
        prompt = (
            "Crie uma label curta (máximo 50 caracteres) para identificar este currículo. "
            "A label deve ser descritiva e única — baseie-se na finalidade do envio (se informada) "
            "e no cargo/perfil do candidato. Exemplos: 'Estágio Backend', 'Vaga Amazon', "
            "'Processo Seletivo UFAM', 'Currículo DevOps'. "
            "Responda APENAS com a label, sem aspas, sem explicações.\n\n"
            + contexto
        )
        try:
            raw, error = call_model(prompt, num_predict=40, timeout=12)
            if not error and raw and raw.strip():
                label = sanitize_text(raw.strip().strip("\"'"))[:50]
        except Exception:
            pass

    if not label:
        if finalidade:
            label = sanitize_text(finalidade[:50])
        elif primeira_linha:
            label = sanitize_text(primeira_linha[:50])

    if not label:
        label = datetime.now().strftime("Currículo %d/%m %H:%M")

    return label


# ---------------------------------------------------------------------------
# Unicidade de label
# ---------------------------------------------------------------------------

def _label_unica(user_id: str, label_base: str, excluir_id: str | None = None) -> str:
    """Garante que `label_base` seja única para o usuário.

    Se já existir, acrescenta sufixo numérico crescente:
        'Estágio Backend' → 'Estágio Backend 2' → 'Estágio Backend 3' …
    `excluir_id` permite ignorar o próprio registro ao editar uma label.
    """
    label = label_base[:50]
    query = Curriculo.query.filter_by(user_id=user_id)
    if excluir_id:
        query = query.filter(Curriculo.id != excluir_id)
    existentes = {c.label for c in query.with_entities(Curriculo.label).all()}

    if label not in existentes:
        return label

    # Tenta extrair sufixo numérico existente para incrementar
    match = re.match(r"^(.*?)(\s+(\d+))?$", label)
    base = match.group(1) if match else label
    contador = 2
    while True:
        candidato = f"{base} {contador}"[:50]
        if candidato not in existentes:
            return candidato
        contador += 1


# ---------------------------------------------------------------------------
# Cor automática (round-robin pela paleta fixa)
# ---------------------------------------------------------------------------

def proxima_cor_automatica(user_id: str) -> str:
    """Devolve a próxima cor da paleta para um novo currículo do usuário,
    avançando em sequência (round-robin) e reiniciando do começo após a
    última cor.

    O contador (`User.proximo_indice_cor`) só cresce — nunca decresce, nem
    mesmo se currículos forem apagados — então a sequência de cores vista
    pelo usuário ao longo do tempo nunca "recua" ou repete antes de
    completar um ciclo inteiro pela paleta.

    Implementado como UPDATE...RETURNING atômico (uma única ida ao banco)
    para evitar que duas criações simultâneas peguem o mesmo índice. Se o
    `user_id` não existir como esperado, devolve a cor padrão do model
    (mesmo comportamento de antes desta feature).
    """
    paleta = Curriculo.CORES_PERMITIDAS
    try:
        resultado = db.session.execute(
            db.text(
                """
                UPDATE users
                SET proximo_indice_cor = proximo_indice_cor + 1
                WHERE id = :user_id
                RETURNING proximo_indice_cor
                """
            ),
            {"user_id": user_id},
        ).first()
        if resultado is None:
            return Curriculo.COR_PADRAO
        indice_usado = (resultado[0] - 1) % len(paleta)
        return paleta[indice_usado]
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "proxima_cor_automatica", "erro": str(e)})
        return Curriculo.COR_PADRAO


# ---------------------------------------------------------------------------
# Salvar / deduplicar
# ---------------------------------------------------------------------------

def obter_ou_criar_curriculo(
    user_id: str,
    texto: str,
    finalidade: str | None = None,
    arquivo_pdf: bytes | None = None,
    arquivo_nome: str | None = None,
    arquivo_mimetype: str | None = None,
) -> Curriculo | None:
    """Salva o currículo se ainda não existir (dedup por hash SHA-256 do
    conteúdo normalizado), ou devolve o existente.

    `arquivo_pdf` é o binário do PDF a ser preservado exatamente como
    enviado pelo usuário (sem conversão/reprocessamento) — ver Task 1.
    Quando informado, é gravado junto ao novo currículo ou usado para
    preencher um currículo existente que ainda não tenha arquivo salvo
    (ex.: registros criados antes desta feature existir).

    Retorna None em caso de erro de banco (erro já logado pelo chamador).
    """
    if not texto or not texto.strip():
        return None

    hash_cv = Curriculo.calcular_hash(texto)

    # Dedup: já existe exatamente esse conteúdo para este usuário?
    existente = Curriculo.query.filter_by(
        user_id=user_id,
        hash_conteudo=hash_cv,
    ).first()
    if existente:
        if arquivo_pdf and not existente.arquivo_pdf:
            existente.arquivo_pdf = arquivo_pdf
            existente.arquivo_nome = arquivo_nome
            existente.arquivo_mimetype = arquivo_mimetype or "application/pdf"
        return existente

    # Novo currículo
    label_base = gerar_label(texto, finalidade)
    label = _label_unica(user_id, label_base)
    cor = proxima_cor_automatica(user_id)

    curriculo = Curriculo(
        user_id=user_id,
        label=label,
        cor=cor,
        hash_conteudo=hash_cv,
        texto=texto,
        arquivo_pdf=arquivo_pdf,
        arquivo_nome=arquivo_nome,
        arquivo_mimetype=arquivo_mimetype or ("application/pdf" if arquivo_pdf else None),
    )
    try:
        db.session.add(curriculo)
        db.session.flush()   # obtém o id sem commit — o commit fica a cargo da rota
        return curriculo
    except Exception as e:
        db.session.rollback()
        logger.error("db_error", extra={"op": "obter_ou_criar_curriculo", "erro": str(e)})
        return None


# ---------------------------------------------------------------------------
# Edição de label
# ---------------------------------------------------------------------------

def renomear_label(
    curriculo: Curriculo,
    novo_label: str,
    user_id: str,
) -> tuple[bool, str | None]:
    """Renomeia a label de um currículo garantindo unicidade.

    Retorna (True, None) em caso de sucesso ou (False, mensagem_de_erro).
    O commit fica a cargo do chamador.
    """
    novo_label = sanitize_text(novo_label.strip())[:50]
    if not novo_label:
        return False, "Label vazia"

    label_final = _label_unica(user_id, novo_label, excluir_id=curriculo.id)
    curriculo.label = label_final
    return True, None


# ---------------------------------------------------------------------------
# Edição de cor
# ---------------------------------------------------------------------------

def alterar_cor(curriculo: Curriculo, nova_cor: str) -> tuple[bool, str | None]:
    """Altera a cor da label de um currículo.

    `nova_cor` deve ser exatamente um dos valores em
    `Curriculo.CORES_PERMITIDAS` (paleta fixa de 30 cores) — qualquer outro
    valor é rejeitado para impedir cores arbitrárias/inválidas no banco.

    Retorna (True, None) em caso de sucesso ou (False, mensagem_de_erro).
    O commit fica a cargo do chamador.
    """
    nova_cor = (nova_cor or "").strip().lower()
    permitidas = {c.lower() for c in Curriculo.CORES_PERMITIDAS}
    if nova_cor not in permitidas:
        return False, "Cor inválida"

    curriculo.cor = nova_cor
    return True, None