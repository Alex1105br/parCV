/**
 * Simulador de Entrevista - JavaScript
 * Gerencia interações e requisições AJAX
 */

// ===== VARIÁVEIS GLOBAIS =====
let entrevistaId = null;
let perguntaAtual = 1;
let totalPerguntas = 10; // valor inicial — sobrescrito pelo total_perguntas real vindo da API

// ===== UTILIDADES =====

/**
 * Fazer requisição fetch com tratamento de erro
 */
async function fetchApi(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (err) {
        console.error('API Error:', err);
        throw err;
    }
}

/**
 * Mostrar mensagem de erro
 */
function mostrarErro(mensagem) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = mensagem;
        errorDiv.style.display = 'block';
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

/**
 * Limpar mensagens de erro
 */
function limparErro() {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

/**
 * Desabilitar/habilitar botão
 */
function desabilitarBotao(btn, desabilitado = true) {
    if (btn) {
        btn.disabled = desabilitado;
        if (desabilitado) {
            btn.dataset.originalText = btn.textContent;
            btn.textContent = 'Processando...';
        } else {
            btn.textContent = btn.dataset.originalText || btn.textContent;
        }
    }
}

// ===== PLANEJAMENTO =====

/**
 * Inicializa formulário de planejamento
 */
function initPlanejamento() {
    const form = document.getElementById('form-planejamento');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const curriculo = document.getElementById('curriculo').files[0];
        const vagaDescricao = document.getElementById('vaga_descricao').value;
        
        // Validações
        if (!curriculo) {
            mostrarErro('Selecione um currículo');
            return;
        }
        
        if (curriculo.size > 5 * 1024 * 1024) {
            mostrarErro('Arquivo muito grande (máximo 5MB)');
            return;
        }
        
        if (!vagaDescricao.trim() || vagaDescricao.length < 20) {
            mostrarErro('Descrição da vaga muito curta (mínimo 20 caracteres)');
            return;
        }
        
        limparErro();
        
        // Preparar FormData
        const formData = new FormData();
        formData.append('curriculo', curriculo);
        formData.append('vaga_descricao', vagaDescricao);
        
        // Mostrar loading
        document.getElementById('form-planejamento').style.display = 'none';
        document.getElementById('loading').style.display = 'block';
        
        try {
            const response = await fetch('/entrevista/gerar-plano', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erro ao gerar plano');
            }
            
            const data = await response.json();
            
            // Salvar ID
            window.entrevistaId = data.entrevista_id;
            
            // Exibir plano
            exibirPlano(data);
            
        } catch (err) {
            mostrarErro(err.message);
            document.getElementById('loading').style.display = 'none';
            document.getElementById('form-planejamento').style.display = 'block';
        }
    });
}

/**
 * Exibir plano gerado
 */
function exibirPlano(data) {
    document.getElementById('num-perguntas').textContent = data.numero_perguntas;
    document.getElementById('strategy-text').textContent = data.plano.estrategia;
    
    const topicosList = document.getElementById('topicos-list');
    topicosList.innerHTML = data.plano.topicos
        .map(t => `<li>${t}</li>`)
        .join('');
    
    document.getElementById('loading').style.display = 'none';
    document.getElementById('resultado-plano').style.display = 'block';
    
    // Configurar botão iniciar
    const btnIniciar = document.getElementById('btn-iniciar');
    btnIniciar.href = `/entrevista/${data.entrevista_id}/executar`;
}

// ===== EXECUÇÃO =====

/**
 * Inicializa página de execução
 */
function initExecucao() {
    const form = document.getElementById('form-resposta');
    if (!form) return;
    
    // Extrair ID da URL ou do data attribute
    const container = document.querySelector('[data-entrevista-id]');
    if (container) {
        entrevistaId = container.dataset.entrevistaId;
    } else {
        // Fallback: extrair da URL (padrão: /entrevista/<id>/executar)
        const match = window.location.pathname.match(/\/entrevista\/([a-f0-9-]+)\/executar/);
        entrevistaId = match ? match[1] : null;
    }
    
    if (!entrevistaId) {
        mostrarErro('ID da entrevista não encontrado');
        return;
    }
    
    // Carregar primeira pergunta
    carregarPergunta();
    
    // Setup form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const resposta = document.getElementById('resposta-input').value;
        
        if (!resposta.trim()) {
            mostrarErro('Digite uma resposta');
            return;
        }
        
        if (resposta.length > 2000) {
            mostrarErro('Resposta muito longa (máximo 2000 caracteres)');
            return;
        }
        
        limparErro();
        desabilitarBotao(form.querySelector('button'));
        
        try {
            const data = await fetchApi(`/entrevista/${entrevistaId}/responder`, {
                method: 'POST',
                body: JSON.stringify({
                    numero_sequencial: perguntaAtual,
                    resposta: resposta,
                    tipo: 'principal'
                })
            });
            
            // Processar resposta
            processarRespostaIA(data);
            
        } catch (err) {
            mostrarErro(err.message);
        } finally {
            desabilitarBotao(form.querySelector('button'), false);
        }
    });
}

/**
 * Carregar pergunta atual
 */
async function carregarPergunta() {
    try {
        const data = await fetchApi(`/entrevista/${entrevistaId}/pergunta/${perguntaAtual}`);
        
        totalPerguntas = data.total_perguntas;
        
        // Atualizar UI
        document.getElementById('pergunta-titulo').textContent = data.pergunta_principal;
        document.getElementById('progresso-texto').textContent = 
            `Pergunta ${perguntaAtual} de ${totalPerguntas}`;
        
        const percentual = (perguntaAtual / totalPerguntas) * 100;
        document.getElementById('barra-preenchimento').style.width = `${percentual}%`;
        
        // Resetar formulário
        document.getElementById('form-resposta').style.display = 'block';
        document.getElementById('feedback-box').style.display = 'none';
        document.getElementById('aprofundamento-box').style.display = 'none';
        document.getElementById('proxima-pergunta').style.display = 'none';
        document.getElementById('resposta-input').value = '';
        document.getElementById('resposta-input').focus();
        
    } catch (err) {
        mostrarErro('Erro ao carregar pergunta: ' + err.message);
    }
}

/**
 * Processar feedback da IA
 */
function processarRespostaIA(data) {
    // Esconder formulário
    document.getElementById('form-resposta').style.display = 'none';
    
    // Mostrar feedback
    document.getElementById('feedback-box').style.display = 'block';
    document.getElementById('feedback-texto').textContent = data.feedback_ia;
    document.getElementById('score-valor').textContent = data.score;
    
    // Processar aprofundamentos
    if (data.aprofundamentos && data.aprofundamentos.length > 0) {
        processarAprofundamentos(data.aprofundamentos);
    } else {
        exibirBotaoProxima();
    }
}

/**
 * Processar perguntas de aprofundamento
 */
let aprofundamentosLista = [];
let contadorAprofundamentos = 0;

function processarAprofundamentos(aprofundamentos) {
    aprofundamentosLista = aprofundamentos;
    contadorAprofundamentos = 0;
    exibirProximoAprofundamento();
}

/**
 * Exibir próximo aprofundamento
 */
function exibirProximoAprofundamento() {
    if (contadorAprofundamentos >= aprofundamentosLista.length) {
        exibirBotaoProxima();
        return;
    }
    
    const ap = aprofundamentosLista[contadorAprofundamentos];
    document.getElementById('pergunta-aprofundamento').textContent = ap.pergunta;
    document.getElementById('aprofundamento-box').style.display = 'block';
    document.getElementById('resposta-aprofundamento').value = '';
    document.getElementById('resposta-aprofundamento').focus();
    
    // Setup form
    const form = document.getElementById('form-aprofundamento');
    form.onsubmit = async (e) => {
        e.preventDefault();
        
        const resposta = document.getElementById('resposta-aprofundamento').value;
        if (!resposta.trim()) {
            mostrarErro('Digite uma resposta');
            return;
        }
        
        contadorAprofundamentos++;
        exibirProximoAprofundamento();
    };
}

/**
 * Exibir botão próxima pergunta/finalizar
 */
function exibirBotaoProxima() {
    document.getElementById('aprofundamento-box').style.display = 'none';
    document.getElementById('proxima-pergunta').style.display = 'block';
    
    const btn = document.getElementById('btn-proxima');
    if (perguntaAtual < totalPerguntas) {
        btn.textContent = 'Próxima Pergunta →';
        btn.onclick = proximaPergunta;
    } else {
        btn.textContent = 'Finalizar e Ver Relatório →';
        btn.onclick = finalizarEntrevista;
    }
}

/**
 * Ir para próxima pergunta
 */
async function proximaPergunta() {
    perguntaAtual++;
    await carregarPergunta();
}

/**
 * Finalizar entrevista
 */
async function finalizarEntrevista() {
    if (!confirm('Tem certeza que deseja finalizar a entrevista?')) return;
    
    try {
        await fetchApi(`/entrevista/${entrevistaId}/finalizar`, {
            method: 'POST'
        });
        
        window.location.href = `/entrevista/${entrevistaId}/relatorio`;
    } catch (err) {
        mostrarErro('Erro ao finalizar: ' + err.message);
    }
}

// ===== RELATÓRIO =====

/**
 * Inicializar página de relatório
 */
function initRelatorio() {
    // Extrair ID da URL (padrão: /entrevista/<id>/relatorio)
    const match = window.location.pathname.match(/\/entrevista\/([a-f0-9-]+)\/relatorio/);
    entrevistaId = match ? match[1] : null;
    
    if (!entrevistaId) {
        mostrarErro('ID da entrevista não encontrado');
        return;
    }
    
    carregarRelatorio();
}

/**
 * Carregar e exibir relatório
 */
async function carregarRelatorio() {
    try {
        const data = await fetchApi(`/entrevista/${entrevistaId}`);
        
        if (!data.relatorio_final) {
            mostrarErro('Relatório não disponível');
            return;
        }
        
        const relatorio = data.relatorio_final;
        
        // Score geral
        const scoreElement = document.querySelector('.score-geral .numero');
        if (scoreElement) {
            scoreElement.textContent = relatorio.score_geral.toFixed(1);
            
            // Cor baseada no score
            const scoreGeral = relatorio.score_geral;
            let cor = '#dc3545'; // vermelho
            if (scoreGeral >= 7) cor = '#28a745'; // verde
            else if (scoreGeral >= 4) cor = '#ffc107'; // amarelo
            
            document.querySelector('.score-geral').style.color = cor;
        }
        
        // Resumo
        populaLista('pontos-fortes', relatorio.pontos_fortes);
        populaLista('pontos-fracos', relatorio.pontos_fracos);
        populaLista('recomendacoes', relatorio.recomendacoes);
        
        // Parecer
        const parecer = document.getElementById('parecer-final');
        if (parecer) {
            parecer.textContent = relatorio.parecer_final;
        }
        
        // Perguntas em acordeão
        exibirPerguntasAcordeao(data.perguntas);
        
    } catch (err) {
        mostrarErro('Erro ao carregar relatório: ' + err.message);
    }
}

/**
 * Popular lista com dados
 */
function populaLista(elementId, items) {
    const el = document.getElementById(elementId);
    if (el && Array.isArray(items)) {
        el.innerHTML = items.map(item => `<li>• ${item}</li>`).join('');
    }
}

/**
 * Exibir perguntas em acordeão
 */
function exibirPerguntasAcordeao(perguntas) {
    const container = document.getElementById('perguntas-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    perguntas.forEach((p, i) => {
        const score = p.avaliacao_resposta?.score || 5;
        let scoreCor = '#dc3545';
        if (score >= 7) scoreCor = '#28a745';
        else if (score >= 4) scoreCor = '#ffc107';
        
        const div = document.createElement('div');
        div.className = 'pergunta-acordeao';
        
        let aprofundamentosHtml = '';
        if (p.perguntas_aprofundamento && p.perguntas_aprofundamento.length > 0) {
            aprofundamentosHtml = '<div class="aprofundamentos"><h4>🔍 Aprofundamentos:</h4>';
            p.perguntas_aprofundamento.forEach((ap, j) => {
                aprofundamentosHtml += `
                    <div class="aprofundamento-item">
                        <h5>Aprofundamento ${j + 1}:</h5>
                        <p><strong>P:</strong> ${ap.pergunta}</p>
                        <p><strong>R:</strong> ${ap.resposta || '[Não respondida]'}</p>
                        ${ap.feedback ? `<p><strong>Feedback:</strong> ${ap.feedback}</p>` : ''}
                    </div>
                `;
            });
            aprofundamentosHtml += '</div>';
        }
        
        div.innerHTML = `
            <div class="pergunta-header">
                <span class="pergunta-numero">
                    <strong>Pergunta ${i + 1}:</strong> ${p.pergunta_principal.substring(0, 70)}...
                </span>
                <span class="pergunta-score" style="background: ${scoreCor}">
                    ${score}/10
                </span>
            </div>
            <div class="pergunta-conteudo">
                <h4>Pergunta Principal</h4>
                <p>${p.pergunta_principal}</p>
                
                <h4>Sua Resposta</h4>
                <p>${p.resposta_usuario || '[Não respondida]'}</p>
                
                <h4>Feedback</h4>
                <p>${p.avaliacao_resposta?.feedback || 'Sem feedback'}</p>
                
                ${aprofundamentosHtml}
            </div>
        `;
        
        // Toggle acordeão
        const header = div.querySelector('.pergunta-header');
        const conteudo = div.querySelector('.pergunta-conteudo');
        
        header.addEventListener('click', () => {
            header.classList.toggle('active');
            conteudo.classList.toggle('active');
        });
        
        container.appendChild(div);
    });
}

// ===== INICIALIZAÇÃO =====

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('form-planejamento')) {
        initPlanejamento();
    } else if (document.getElementById('form-resposta')) {
        initExecucao();
    } else if (document.getElementById('perguntas-container') !== null) {
        initRelatorio();
    }
});