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
    `;
}