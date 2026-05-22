OPTIMIZED_STRUCTURE_EXAMPLE = (
    "NOME COMPLETO\n"
    "Título Profissional\n"
    "email@email.com | linkedin.com/in/usuario | github.com/usuario\n"
    "\n"
    "---SECAO: COMPETÊNCIAS---\n"
    "Linguagens: Python, JavaScript, Java\n"
    "Tecnologias & Ferramentas: Docker, Git, AWS\n"
    "\n"
    "---SECAO: EXPERIÊNCIAS RELEVANTES---\n"
    "---EMPRESA: Nome da Empresa | Jan 2022 - Dez 2023---\n"
    "---CARGO: Desenvolvedor Full Stack---\n"
    "• Desenvolveu sistema X que aumentou a eficiência em 30%\n"
    "• Implementou pipeline CI/CD reduzindo tempo de deploy\n"
    "\n"
    "---SECAO: FORMAÇÃO ACADÊMICA---\n"
    "---EMPRESA: Universidade Federal | 2018 - 2022---\n"
    "---CARGO: Bacharelado em Ciência da Computação---\n"
    "\n"
    "---SECAO: EXPERIÊNCIA EM PROJETOS---\n"
    "• Nome do Projeto (2023): Descrição do projeto e tecnologias usadas.\n"
    "\n"
    "---SECAO: COMPETÊNCIAS-CHAVE---\n"
    "• Liderança técnica\n"
    "• Resolução de problemas\n"
    "\n"
    "---SECAO: IDIOMAS---\n"
    "• Português: Nativo\n"
    "• Inglês: Avançado\n"
)


def build_prompt_ats(curriculo, vaga=None):
    return (
        "Você é um sistema ATS profissional.\n"
        "Analise o currículo com base nos critérios:\n"
        "1. Estrutura e formatação (0-15)\n"
        "2. Clareza e escrita (0-15)\n"
        "3. Experiência profissional (0-20)\n"
        "4. Palavras-chave ATS (0-20)\n"
        "5. Skills técnicas (0-15)\n"
        "6. Compatibilidade com vaga (0-15)\n"
        "\n"
        "Retorne APENAS JSON válido:\n"
        "{\n"
        '    "score_total": int,\n'
        '    "criterios": {"estrutura": int, "clareza": int, "experiencia": int,\n'
        '                   "palavras_chave": int, "skills": int, "compatibilidade": int},\n'
        '    "pontos_fortes": [""],\n'
        '    "pontos_fracos": [""],\n'
        '    "sugestoes": [""]\n'
        "}\n"
        "\n"
        f"Currículo: {curriculo}\n"
        f"Descrição da vaga: {vaga or 'Não informada'}"
    )


def build_prompt_otimizar(curriculo, vaga=None):
    return (
        "Você é um especialista em otimização de currículos para ATS.\n"
        "Reescreva o currículo seguindo EXATAMENTE esta estrutura e marcadores:\n"
        "\n"
        f"{OPTIMIZED_STRUCTURE_EXAMPLE}"
        "\n"
        "REGRAS OBRIGATÓRIAS DE FORMATO:\n"
        "1. As 3 primeiras linhas DEVEM ser: nome completo, título profissional, contatos (separados por |)\n"
        "2. Cada seção DEVE começar com ---SECAO: NOME DA SEÇÃO---\n"
        "3. Cada empresa/instituição DEVE usar ---EMPRESA: nome | período---\n"
        "4. Cada cargo/curso DEVE usar ---CARGO: título---\n"
        "5. Bullets DEVEM começar com •\n"
        "6. Use APENAS as seções do exemplo acima\n"
        "7. Apenas informações verídicas do currículo original\n"
        "8. Verbos de ação no passado nos bullets\n"
        "9. Sem JSON dentro do campo curriculo_otimizado — apenas texto puro com os marcadores\n"
        "\n"
        "Retorne APENAS JSON válido:\n"
        "{\n"
        '    "curriculo_otimizado": "texto completo aqui com os marcadores ---SECAO:--- etc",\n'
        '    "melhorias": ["melhoria 1", "melhoria 2"]\n'
        "}\n"
        "\n"
        f"Currículo original: {curriculo}\n"
        f"Descrição da vaga: {vaga if vaga else 'Não informada'}"
    )
