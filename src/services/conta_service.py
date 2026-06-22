"""Serviço de gerenciamento de conta do usuário.

Responsabilidades:
- Atualizar dados cadastrais (nome, telefone, profissão)
- Alterar senha com verificação da senha atual
- Excluir conta permanentemente, removendo todos os dados relacionados
"""
import os
import re
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from src.models.db import db
from src.models.user import User
from src.logging_config import logger


# ── Validadores ────────────────────────────────────────────────────────────────

def _validar_nome(nome: str) -> str | None:
    """Retorna mensagem de erro ou None se válido."""
    nome = nome.strip()
    if not nome:
        return "O nome não pode ficar em branco."
    if len(nome) < 2:
        return "O nome deve ter ao menos 2 caracteres."
    if len(nome) > 100:
        return "O nome deve ter no máximo 100 caracteres."
    return None


def _validar_senha(senha: str) -> str | None:
    """Retorna mensagem de erro ou None se válida."""
    if len(senha) < 8:
        return "A nova senha deve ter ao menos 8 caracteres."
    if len(senha) > 128:
        return "A nova senha deve ter no máximo 128 caracteres."
    return None


# ── Operações de conta ─────────────────────────────────────────────────────────

def atualizar_dados(user_id: str, nome: str, telefone: str = "", profissao: str = "") -> dict:
    """Atualiza nome e informações extras de perfil.

    Args:
        user_id: ID do usuário autenticado.
        nome: Novo nome (obrigatório).
        telefone: Telefone de contato (opcional, máx 20 chars).
        profissao: Área profissional (opcional, máx 100 chars).

    Returns:
        dict com chave ``ok`` (bool) e ``error`` (str, apenas se falhou),
        ou ``name`` (str) com o nome atualizado quando bem-sucedido.
    """
    erro = _validar_nome(nome)
    if erro:
        return {"ok": False, "error": erro}

    if telefone and len(telefone.strip()) > 20:
        return {"ok": False, "error": "Telefone deve ter no máximo 20 caracteres."}

    if profissao and len(profissao.strip()) > 100:
        return {"ok": False, "error": "Área profissional deve ter no máximo 100 caracteres."}

    user = db.session.get(User, user_id)
    if not user:
        return {"ok": False, "error": "Usuário não encontrado."}

    user.name = nome.strip()

    # Campos extras opcionais — armazenados nos atributos dinâmicos do model
    # se existirem; ignorados silenciosamente caso ainda não haja coluna.
    if hasattr(user, "telefone"):
        user.telefone = telefone.strip() if telefone else None
    if hasattr(user, "profissao"):
        user.profissao = profissao.strip() if profissao else None

    db.session.commit()

    logger.info(
        "conta_dados_atualizados",
        extra={"user_id": user_id},
    )
    return {"ok": True, "name": user.name}


def alterar_senha(user_id: str, senha_atual: str, nova_senha: str, confirmar_senha: str) -> dict:
    """Altera a senha após verificar a senha atual.

    Args:
        user_id: ID do usuário autenticado.
        senha_atual: Senha atual em texto claro (verificada via hash).
        nova_senha: Nova senha desejada.
        confirmar_senha: Confirmação da nova senha.

    Returns:
        dict com ``ok`` (bool) e ``error`` (str se falhou).
    """
    if not senha_atual:
        return {"ok": False, "error": "Informe sua senha atual."}

    erro = _validar_senha(nova_senha)
    if erro:
        return {"ok": False, "error": erro}

    if nova_senha != confirmar_senha:
        return {"ok": False, "error": "A nova senha e a confirmação não coincidem."}

    user = db.session.get(User, user_id)
    if not user:
        return {"ok": False, "error": "Usuário não encontrado."}

    if not check_password_hash(user.password, senha_atual):
        return {"ok": False, "error": "Senha atual incorreta."}

    if check_password_hash(user.password, nova_senha):
        return {"ok": False, "error": "A nova senha deve ser diferente da senha atual."}

    user.password = generate_password_hash(nova_senha)
    # Invalida tokens de reset pendentes ao trocar a senha
    user.reset_token = None
    user.reset_token_expires_at = None

    db.session.commit()

    logger.info(
        "conta_senha_alterada",
        extra={"user_id": user_id},
    )
    return {"ok": True}


def excluir_conta(user_id: str, senha_confirmacao: str) -> dict:
    """Remove permanentemente o usuário e todos os seus dados.

    A exclusão é feita em cascata via ORM: analises, otimizacoes,
    chat_sessions, entrevistas e curriculos são deletados antes do
    próprio User para respeitar as FK constraints.

    A senha de confirmação é exigida como proteção contra cliques
    acidentais ou ações não autorizadas.

    Args:
        user_id: ID do usuário autenticado.
        senha_confirmacao: Senha atual do usuário (confirmação de intenção).

    Returns:
        dict com ``ok`` (bool) e ``error`` (str se falhou).
    """
    if not senha_confirmacao:
        return {"ok": False, "error": "Digite sua senha para confirmar a exclusão."}

    user = db.session.get(User, user_id)
    if not user:
        return {"ok": False, "error": "Usuário não encontrado."}

    if not check_password_hash(user.password, senha_confirmacao):
        return {"ok": False, "error": "Senha incorreta. A conta não foi excluída."}

    # Deleta registros dependentes explicitamente para garantir consistência
    # mesmo em bancos sem ON DELETE CASCADE configurado.
    try:
        _deletar_dados_usuario(user)
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error(
            "conta_excluir_erro",
            extra={"user_id": user_id, "error": str(exc)},
        )
        return {"ok": False, "error": "Erro ao excluir a conta. Tente novamente."}

    logger.info(
        "conta_excluida",
        extra={"user_id": user_id},
    )
    return {"ok": True}


def _deletar_dados_usuario(user: User) -> None:
    """Deleta em ordem todos os registros do usuário antes de deletar o user.

    Importações locais para evitar imports circulares — os models só são
    necessários aqui, não no topo do módulo.
    """
    from src.models.analise import Analise
    from src.models.otimizacao import Otimizacao
    from src.models.chat_session import ChatSession
    from src.models.entrevista import Entrevista
    from src.models.curriculo import Curriculo

    user_id = user.id

    # Otimizacoes dependem de Analise — deleta primeiro
    otimizacoes = Otimizacao.query.filter_by(user_id=user_id).all()
    for o in otimizacoes:
        db.session.delete(o)

    analises = Analise.query.filter_by(user_id=user_id).all()
    for a in analises:
        db.session.delete(a)

    # Entrevistas e suas perguntas (cascade configurado no model)
    entrevistas = Entrevista.query.filter_by(user_id=user_id).all()
    for e in entrevistas:
        db.session.delete(e)

    chat_sessions = ChatSession.query.filter_by(user_id=user_id).all()
    for c in chat_sessions:
        db.session.delete(c)

    curriculos = Curriculo.query.filter_by(user_id=user_id).all()
    for cur in curriculos:
        db.session.delete(cur)

    db.session.flush()
