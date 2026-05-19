OPTIMIZED_STRUCTURE_EXAMPLE = """
NOME COMPLETO
Título Profissional
email@email.com | linkedin.com/in/usuario | github.com/usuario

---SECAO: COMPETÊNCIAS---
Linguagens: Python, JavaScript, Java
Tecnologias & Ferramentas: Docker, Git, AWS

---SECAO: EXPERIÊNCIAS RELEVANTES---
---EMPRESA: Nome da Empresa | Jan 2022 - Dez 2023---
---CARGO: Desenvolvedor Full Stack---
• Desenvolveu sistema X que aumentou a eficiência em 30%
• Implementou pipeline CI/CD reduzindo tempo de deploy

---SECAO: FORMAÇÃO ACADÊMICA---
---EMPRESA: Universidade Federal | 2018 - 2022---
---CARGO: Bacharelado em Ciência da Computação---

---SECAO: EXPERIÊNCIA EM PROJETOS---
• Nome do Projeto (2023): Descrição do projeto e tecnologias usadas.

---SECAO: COMPETÊNCIAS-CHAVE---
• Liderança técnica
• Resolução de problemas

---SECAO: IDIOMAS---
• Português: Nativo
• Inglês: Avançado
"""


def build_prompt_ats(curriculo, vaga=None):
    return f"""Você é um sistema ATS profissional.
Analise o currículo com base nos critérios:
1. Estrutura e formatação (0-15)
2. Clareza e escrita (0-15)
3. Experiência profissional (0-20)
4. Palavras-chave ATS (0-20)
5. Skills técnicas (0-15)
6. Compatibilidade com vaga (0-15)

Retorne APENAS JSON válido:
{{
    "score_total": int,
    "criterios": {{"estrutura": int, "clareza": int, "experiencia": int,
                   "palavras_chave": int, "skills": int, "compatibilidade": int}},
    "pontos_fortes": [""],
    "pontos_fracos": [""],
    "sugestoes": [""]
}}

Currículo: {curriculo}
Descrição da vaga: {vaga if vaga else "Não informada"}"""


def build_prompt_otimizar(curriculo, vaga=None):
    return f"""Você é um especialista em otimização de currículos para ATS.
Reescreva o currículo seguindo EXATAMENTE esta estrutura e marcadores:

{OPTIMIZED_STRUCTURE_EXAMPLE}

REGRAS OBRIGATÓRIAS DE FORMATO:
1. As 3 primeiras linhas DEVEM ser: nome completo, título profissional, contatos (separados por |)
2. Cada seção DEVE começar com ---SECAO: NOME DA SEÇÃO---
3. Cada empresa/instituição DEVE usar ---EMPRESA: nome | período---
4. Cada cargo/curso DEVE usar ---CARGO: título---
5. Bullets DEVEM começar com •
6. Use APENAS as seções do exemplo acima
7. Apenas informações verídicas do currículo original
8. Verbos de ação no passado nos bullets
9. Sem JSON dentro do campo curriculo_otimizado — apenas texto puro com os marcadores

Retorne APENAS JSON válido:
{{
    "curriculo_otimizado": "texto completo aqui com os marcadores ---SECAO:--- etc",
    "melhorias": ["melhoria 1", "melhoria 2"]
}}

Currículo original: {curriculo}
Descrição da vaga: {vaga if vaga else "Não informada"}"""
