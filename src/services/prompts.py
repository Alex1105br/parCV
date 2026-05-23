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
        "Inclua em 'palavras_chave_faltando' as palavras-chave relevantes extraídas da vaga que estão ausentes no currículo.\n"
        "Inclua em 'certificados_sugeridos' até 4 certificações reconhecidas pelo mercado que agregariam valor ao candidato para esta vaga. "
        "Sugira apenas certificações que o candidato ainda NÃO possui e que complementem lacunas reais identificadas no currículo — não sugira algo que o candidato já demonstra domínio (ex: curso de inglês para quem já declara nível avançado/fluente). "
        "Cada item deve ter 'nome' (nome oficial da certificação), 'plataforma' e 'url'.\n"
        "Para a URL, use APENAS os endpoints abaixo — escolha o mais específico que se aplica, caso contrário use o catálogo da plataforma:\n"
        "  AWS: https://aws.amazon.com/certification/\n"
        "  Google Cloud: https://cloud.google.com/learn/certification\n"
        "  Microsoft/Azure: https://learn.microsoft.com/en-us/credentials/\n"
        "  Kubernetes/CNCF: https://www.cncf.io/training/certification/\n"
        "  CompTIA: https://www.comptia.org/certifications\n"
        "  Cisco: https://www.cisco.com/c/en/us/training-events/training-certifications/certifications.html\n"
        "  DevOps Institute: https://www.devopsinstitute.com/certifications/\n"
        "  Oracle: https://education.oracle.com/certification\n"
        "  PMI: https://www.pmi.org/certifications\n"
        "  Python Institute: https://pythoninstitute.org/certification-tracks/\n"
        "  Scrum.org: https://www.scrum.org/professional-scrum-certifications\n"
        "  HashiCorp: https://www.hashicorp.com/certifications\n"
        "  Linux Foundation: https://training.linuxfoundation.org/certification/\n"
        "  Coursera: https://www.coursera.org/search?query=<nome+da+certificacao>\n"
        "  LinkedIn Learning: https://www.linkedin.com/learning/search?keywords=<nome+da+certificacao>\n"
        "Não invente URLs fora desta lista.\n"
        "\n"
        "Retorne APENAS JSON válido:\n"
        "{\n"
        '    "score_total": int,\n'
        '    "criterios": {"estrutura": int, "clareza": int, "experiencia": int,\n'
        '                   "palavras_chave": int, "skills": int, "compatibilidade": int},\n'
        '    "pontos_fortes": [""],\n'
        '    "pontos_fracos": [""],\n'
        '    "sugestoes": [""],\n'
        '    "palavras_chave_faltando": [""],\n'
        '    "certificados_sugeridos": [{"nome": "", "plataforma": "", "url": ""}]\n'
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
        f"Descrição da vaga: {vaga or 'Não informada'}"
    )
