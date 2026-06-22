/**
 * conta.js — Gerenciamento da página de configurações de conta.
 *
 * Responsabilidades:
 *  - Submissão via fetch() dos 3 formulários (dados, senha, excluir conta)
 *  - Indicador de força de senha
 *  - Toggle de visibilidade de campos de senha
 *  - Modal de confirmação de exclusão
 *  - Toast de feedback (sucesso / erro)
 */

"use strict";

// ── Utilitários ──────────────────────────────────────────────────────────────

/**
 * Exibe um toast de feedback temporário.
 * @param {string} mensagem
 * @param {"success"|"error"} tipo
 */
function mostrarToast(mensagem, tipo = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = mensagem;
  toast.className = `toast toast--${tipo} show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.className = "toast";
  }, 4000);
}

/**
 * Mostra ou limpa uma mensagem de erro inline abaixo de um formulário.
 * @param {HTMLElement} el  Elemento <p> de erro.
 * @param {string|null} msg Mensagem ou null para limpar.
 */
function setErro(el, msg) {
  if (msg) {
    el.textContent = msg;
    el.hidden = false;
  } else {
    el.textContent = "";
    el.hidden = true;
  }
}

/**
 * Faz POST JSON e devolve { ok, data } onde data é o objeto JSON retornado.
 * @param {string} url
 * @param {object} body
 */
async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  return { ok: resp.ok, data };
}

// ── Toggle de visibilidade de senha ─────────────────────────────────────────

document.querySelectorAll(".account-toggle-password").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetId = btn.dataset.target;
    const input = document.getElementById(targetId);
    const eyeShow = btn.querySelector(".eye-show");
    const eyeHide = btn.querySelector(".eye-hide");

    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    eyeShow.style.display = isPassword ? "none" : "";
    eyeHide.style.display = isPassword ? "" : "none";
  });
});

// ── Indicador de força de senha ──────────────────────────────────────────────

const novaSenhaInput = document.getElementById("nova-senha");
const strengthWrap = document.getElementById("password-strength");
const strengthFill = document.getElementById("strength-fill");
const strengthLabel = document.getElementById("strength-label");

const NIVEIS = [
  { min: 0,  label: "Muito fraca", color: "#ef4444", pct: 15 },
  { min: 1,  label: "Fraca",       color: "#f97316", pct: 35 },
  { min: 2,  label: "Média",       color: "#eab308", pct: 60 },
  { min: 3,  label: "Forte",       color: "#22c55e", pct: 85 },
  { min: 4,  label: "Muito forte", color: "#6366f1", pct: 100 },
];

function avaliarForca(senha) {
  let score = 0;
  if (senha.length >= 8)  score++;
  if (senha.length >= 12) score++;
  if (/[A-Z]/.test(senha)) score++;
  if (/[0-9]/.test(senha)) score++;
  if (/[^A-Za-z0-9]/.test(senha)) score++;
  return Math.min(score, 4);
}

novaSenhaInput?.addEventListener("input", () => {
  const senha = novaSenhaInput.value;
  if (!senha) {
    strengthWrap.hidden = true;
    return;
  }
  strengthWrap.hidden = false;
  const nivel = NIVEIS[avaliarForca(senha)];
  strengthFill.style.width = nivel.pct + "%";
  strengthFill.style.background = nivel.color;
  strengthLabel.textContent = nivel.label;
  strengthLabel.style.color = nivel.color;
});

// ── Formulário: dados cadastrais ─────────────────────────────────────────────

const formDados = document.getElementById("form-dados");
const erroDados = document.getElementById("erro-dados");
const btnDados  = document.getElementById("btn-dados");

formDados?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setErro(erroDados, null);

  const nome     = document.getElementById("nome").value.trim();
  const telefone = document.getElementById("telefone").value.trim();
  const profissao = document.getElementById("profissao").value.trim();

  if (!nome) {
    setErro(erroDados, "O nome não pode ficar em branco.");
    document.getElementById("nome").focus();
    return;
  }

  btnDados.disabled = true;
  btnDados.textContent = "Salvando…";

  try {
    const { ok, data } = await postJSON("/conta/dados", { nome, telefone, profissao });
    if (ok) {
      mostrarToast("Dados atualizados com sucesso.");
    } else {
      setErro(erroDados, data.error || "Erro ao salvar. Tente novamente.");
    }
  } catch {
    setErro(erroDados, "Erro de conexão. Verifique sua internet e tente novamente.");
  } finally {
    btnDados.disabled = false;
    btnDados.textContent = "Salvar alterações";
  }
});

// ── Formulário: alterar senha ────────────────────────────────────────────────

const formSenha = document.getElementById("form-senha");
const erroSenha = document.getElementById("erro-senha");
const btnSenha  = document.getElementById("btn-senha");

formSenha?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setErro(erroSenha, null);

  const senhaAtual      = document.getElementById("senha-atual").value;
  const novaSenha       = document.getElementById("nova-senha").value;
  const confirmarSenha  = document.getElementById("confirmar-senha").value;

  if (!senhaAtual) {
    setErro(erroSenha, "Informe sua senha atual.");
    document.getElementById("senha-atual").focus();
    return;
  }
  if (novaSenha.length < 8) {
    setErro(erroSenha, "A nova senha deve ter ao menos 8 caracteres.");
    document.getElementById("nova-senha").focus();
    return;
  }
  if (novaSenha !== confirmarSenha) {
    setErro(erroSenha, "A nova senha e a confirmação não coincidem.");
    document.getElementById("confirmar-senha").focus();
    return;
  }

  btnSenha.disabled = true;
  btnSenha.textContent = "Alterando…";

  try {
    const { ok, data } = await postJSON("/conta/senha", {
      senha_atual: senhaAtual,
      nova_senha: novaSenha,
      confirmar_senha: confirmarSenha,
    });
    if (ok) {
      formSenha.reset();
      strengthWrap.hidden = true;
      mostrarToast("Senha alterada com sucesso.");
    } else {
      setErro(erroSenha, data.error || "Erro ao alterar senha. Tente novamente.");
    }
  } catch {
    setErro(erroSenha, "Erro de conexão. Verifique sua internet e tente novamente.");
  } finally {
    btnSenha.disabled = false;
    btnSenha.textContent = "Alterar senha";
  }
});

// ── Modal de exclusão de conta ───────────────────────────────────────────────

const modal            = document.getElementById("modal-excluir");
const btnAbrirModal    = document.getElementById("btn-abrir-modal-excluir");
const btnCancelarModal = document.getElementById("btn-cancelar-modal");
const btnConfirmar     = document.getElementById("btn-confirmar-excluir");
const senhaExcluirInput = document.getElementById("senha-excluir");
const erroExcluir      = document.getElementById("erro-excluir");

function abrirModal() {
  modal.hidden = false;
  senhaExcluirInput.value = "";
  setErro(erroExcluir, null);
  // Foco no input para facilitar preenchimento por teclado
  setTimeout(() => senhaExcluirInput.focus(), 50);
}

function fecharModal() {
  modal.hidden = true;
  btnConfirmar.disabled = false;
  btnConfirmar.textContent = "Sim, excluir minha conta";
  setErro(erroExcluir, null);
}

btnAbrirModal?.addEventListener("click", abrirModal);
btnCancelarModal?.addEventListener("click", fecharModal);

// Fecha ao clicar fora do modal
modal?.addEventListener("click", (e) => {
  if (e.target === modal) fecharModal();
});

// Fecha com Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) fecharModal();
});

btnConfirmar?.addEventListener("click", async () => {
  const senha = senhaExcluirInput.value;
  setErro(erroExcluir, null);

  if (!senha) {
    setErro(erroExcluir, "Digite sua senha para confirmar.");
    senhaExcluirInput.focus();
    return;
  }

  btnConfirmar.disabled = true;
  btnConfirmar.textContent = "Excluindo…";

  try {
    const { ok, data } = await postJSON("/conta/excluir", { senha });
    if (ok) {
      // Redireciona para login após excluir com sucesso
      window.location.href = "/login?conta_excluida=1";
    } else {
      setErro(erroExcluir, data.error || "Erro ao excluir conta. Tente novamente.");
      btnConfirmar.disabled = false;
      btnConfirmar.textContent = "Sim, excluir minha conta";
    }
  } catch {
    setErro(erroExcluir, "Erro de conexão. Verifique sua internet e tente novamente.");
    btnConfirmar.disabled = false;
    btnConfirmar.textContent = "Sim, excluir minha conta";
  }
});