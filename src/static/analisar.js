async function enviarAnalise() {
    const fileInput = document.getElementById('ats-file');
    const vaga = document.getElementById('ats-vaga').value;

    if (!fileInput.files.length) {
        alert("Selecione um arquivo");
        return;
    }

    const formData = new FormData();
    formData.append('arquivo', fileInput.files[0]);
    if (vaga) formData.append('vaga', vaga);

    document.getElementById('loader').classList.remove('hidden');
    document.getElementById('resultado').innerHTML = '';

    try {
        const response = await fetch('/analisar', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        document.getElementById('loader').classList.add('hidden');
        mostrarResultadoATS(data);

    } catch (err) {
        document.getElementById('loader').classList.add('hidden');
        alert("Erro: " + err.message);
    }
}


function mostrarResultadoATS(data) {
    const container = document.getElementById('resultado');

    if (data.error) {
        container.innerHTML = `<p class="error">❌ ${data.error}</p>`;
        return;
    }

    const score = data.score_total;

    let cor = 'red';
    if (score > 75) cor = 'green';
    else if (score > 50) cor = 'orange';

    container.innerHTML = `
        <div class="score-box" style="border-color:${cor}">
            <h2 style="color:${cor}">Score ATS: ${score}/100</h2>
        </div>

        <h3>📊 Critérios</h3>
        <ul>
            <li>Estrutura: ${data.criterios.estrutura}</li>
            <li>Clareza: ${data.criterios.clareza}</li>
            <li>Experiência: ${data.criterios.experiencia}</li>
            <li>Palavras-chave: ${data.criterios.palavras_chave}</li>
            <li>Skills: ${data.criterios.skills}</li>
            <li>Compatibilidade: ${data.criterios.compatibilidade}</li>
        </ul>

        <h3>✅ Pontos fortes</h3>
        <ul>${data.pontos_fortes.map(p => `<li>${p}</li>`).join('')}</ul>

        <h3>⚠ Pontos fracos</h3>
        <ul>${data.pontos_fracos.map(p => `<li>${p}</li>`).join('')}</ul>

        <h3>💡 Sugestões</h3>
        <ul>${data.sugestoes.map(s => `<li>${s}</li>`).join('')}</ul>

        <div style="margin-top: 20px;">
            <button id="btn-otimizar" onclick="otimizarCurriculo()">
                ✨ Otimizar Currículo
            </button>
        </div>

        <div id="loader-otimizar" class="hidden" style="margin-top:12px;">⏳ Otimizando currículo... (pode levar alguns minutos)</div>
        <div id="resultado-otimizado"></div>
    `;
}


async function otimizarCurriculo() {
    const fileInput = document.getElementById('ats-file');
    if (!fileInput.files.length) {
        alert("Selecione um arquivo de currículo primeiro e clique em Analisar.");
        return;
    }

    document.getElementById('loader-otimizar').classList.remove('hidden');
    document.getElementById('resultado-otimizado').innerHTML = '';
    document.getElementById('btn-otimizar').disabled = true;

    const formData = new FormData();
    formData.append('arquivo', fileInput.files[0]);
    const vaga = document.getElementById('ats-vaga').value;
    if (vaga) formData.append('vaga', vaga);

    try {
        const response = await fetch('/otimizar', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        document.getElementById('loader-otimizar').classList.add('hidden');
        document.getElementById('btn-otimizar').disabled = false;

        if (data.error) {
            document.getElementById('resultado-otimizado').innerHTML =
                `<p class="error">❌ ${data.error}</p>`;
            return;
        }

        mostrarCurriculoOtimizado(data.curriculo_otimizado, data.melhorias);

    } catch (err) {
        document.getElementById('loader-otimizar').classList.add('hidden');
        document.getElementById('btn-otimizar').disabled = false;
        alert("Erro ao otimizar: " + err.message);
    }
}


function mostrarCurriculoOtimizado(curriculo, melhorias) {
    const div = document.getElementById('resultado-otimizado');
    div.innerHTML = `
        <hr style="margin: 24px 0; border-color:#333;">
        <h2 style="color:#4CAF50;">📄 Currículo Otimizado</h2>

        ${melhorias && melhorias.length ? `
        <div style="background:#1e1e1e; border-left:3px solid #e53935; padding:12px;
                    margin-bottom:16px; border-radius:6px;">
            <strong>🔧 Melhorias aplicadas:</strong>
            <ul style="margin-top:8px;">${melhorias.map(m => `<li>${m}</li>`).join('')}</ul>
        </div>` : ''}

        <div id="curriculo-text" style="
            background:#1a1a2e;
            border:1px solid #333;
            border-radius:10px;
            padding:24px;
            white-space:pre-wrap;
            font-family:'Courier New', monospace;
            font-size:0.88em;
            line-height:1.7;
            color:#e0e0e0;
            margin-bottom:16px;
        ">${curriculo}</div>

        <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <a href="/otimizar/pdf" target="_blank">
                <button style="background:#1976D2; padding:12px 20px; font-size:1em; border:none;
                               border-radius:8px; color:white; cursor:pointer;">
                    📥 Baixar PDF
                </button>
            </a>
            <button onclick="copiarCurriculo()"
                    style="background:#555; padding:12px 20px; font-size:1em; border:none;
                           border-radius:8px; color:white; cursor:pointer;">
                📋 Copiar texto
            </button>
        </div>
    `;
}


function copiarCurriculo() {
    const texto = document.getElementById('curriculo-text').innerText;
    navigator.clipboard.writeText(texto).then(() => {
        alert("Currículo copiado para a área de transferência!");
    });
}