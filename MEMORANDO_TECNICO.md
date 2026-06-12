# 📚 Índice de Documentação - Simulador de Entrevistas

## 📖 Documentos Criados

Este projeto foi reformulado para incluir uma nova funcionalidade de **Simulador de Entrevistas**. Consulte os documentos abaixo para entender a arquitetura e implementação:

### 1. **[ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md)** ⭐ *Comece aqui*
   - **O quê:** Especificação completa e oficial do novo sistema
   - **Conteúdo:**
     - Resumo executivo
     - Arquitetura de banco de dados (modelos)
     - Fluxo da aplicação (3 fases)
     - Endpoints da API (7 rotas)
     - Templates e interfaces
     - Prompts de IA (Groq)
     - Implementação checklist
     - Notas de segurança
   - **Público:** Arquitetos, tech leads, QA
   - **Tempo de leitura:** 30-40 min

---

### 2. **[DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md)** 📊 *Para visualizar o fluxo*
   - **O quê:** Diagramas visuais e fluxogramas
   - **Conteúdo:**
     - Fluxo geral da aplicação
     - Fluxo detalhado de execução
     - Estrutura de banco de dados (ER diagram)
     - Estados da entrevista
     - Fluxo de requisição/resposta
     - Hierarquia de componentes frontend
     - Timeline da entrevista
     - Estados do frontend
     - Casos de uso
     - Integração com código existente
   - **Público:** Designers, developers, testers
   - **Tempo de leitura:** 20 min

---

### 3. **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** ⚡ *Para começar rápido*
   - **O quê:** Referência rápida para implementação
   - **Conteúdo:**
     - Arquivos a criar/modificar
     - Estrutura essencial de models
     - Assinatura de endpoints
     - Funções de IA (assinatura)
     - Função PDF (assinatura)
     - Prompts de IA (formato correto)
     - Roadmap de implementação (5 fases)
     - Testes manuais
     - Validações críticas
     - Debugging tips
     - Deployment checklist
   - **Público:** Developers (implementação)
   - **Tempo de leitura:** 15 min

---

### 4. **[EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md)** 💻 *Código pronto para usar*
   - **O quê:** Código de exemplo e snippets prontos
   - **Conteúdo:**
     - Model completo de Entrevista
     - Atualização do User model
     - Funções de IA com implementação
     - Routes blueprint completo (7 endpoints)
     - Atualização de app.py
     - Função de geração de PDF
     - Comando de migração Alembic
   - **Público:** Developers (copy-paste ready)
   - **Tempo de leitura:** 20 min + implementação

---

### 5. **[MEMORANDO_TECNICO.md](./MEMORANDO_TECNICO.md)** 📋 *Este documento*
   - Índice e guia de navegação
   - Resumo executivo
   - Links rápidos

---

## 🎯 Guia de Navegação

### Se você é...

#### 👔 **Gerente de Projeto / Product Owner**
1. Leia: [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (sessão "Resumo Executivo")
2. Veja: [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) (seção "Fluxo Geral")
3. Consulte: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (seção "Roadmap")

#### 🏗️ **Arquiteto / Tech Lead**
1. Leia: [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (completo)
2. Estude: [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) (estrutura BD + fluxos)
3. Valide: [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md) (patterns e estrutura)

#### 💻 **Developer Backend**
1. Consulte: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (checklist)
2. Implemente: [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md) (models + routes + services)
3. Refira: [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (regras de negócio)

#### 🎨 **Developer Frontend**
1. Estude: [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) (componentes)
2. Leia: [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (templates, endpoints)
3. Use: [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md) (estrutura HTML/CSS/JS)

#### 🧪 **QA / Tester**
1. Entenda: [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) (fluxos)
2. Teste: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (testes manuais)
3. Valide: [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (casos de uso + segurança)

---

## 📊 Resumo Executivo

### O que é o Simulador de Entrevistas?

Uma reformulação do módulo de entrevistas que transforma o chat anterior em uma **jornada estruturada de 3 fases**:

**Fase 1: Planejamento**
- Usuário carrega currículo + descrição de vaga
- IA analisa e gera plano com número de perguntas

**Fase 2: Execução**
- IA faz perguntas uma por vez
- Usuário responde
- IA faz até 2 aprofundamentos por pergunta
- Ciclo repete

**Fase 3: Relatório**
- Sistema gera análise completa
- Exportável em PDF

### Estrutura de Dados

```
users
 └─ entrevista (novo)
     └─ pergunta_entrevista (novo, múltiplas)
```

### Tecnologias Utilizadas

- **Backend:** Flask, SQLAlchemy, Alembic
- **IA:** Groq API (LLM)
- **PDF:** ReportLab
- **Parser:** Existing PDF/DOC parser
- **Frontend:** HTML5, CSS, JavaScript vanilla

### Mudanças no Projeto

#### ✅ Arquivos Criados
- `src/models/entrevista.py` (2 models)
- `src/routes/entrevista.py` (blueprint com 7 endpoints)
- `src/templates/entrevista_*.html` (3 templates)
- `src/static/entrevista.css` + `.js`
- `migrations/versions/XXXX_add_entrevista_tables.py`

#### ✏️ Arquivos Modificados
- `src/app.py` (registrar blueprint + import model)
- `src/models/user.py` (adicionar relationship)
- `src/services/model.py` (3 funções IA)
- `src/services/pdf.py` (1 função PDF)

#### ✨ Chat Existente
- **Preservado** — pode ser renomeado (ex: "Assistente Geral")
- **Não substituído** — convive com nova funcionalidade

### Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/entrevista/gerar-plano` | Upload CV + vaga → Plano |
| GET | `/entrevista/<id>` | Dados da entrevista |
| GET | `/entrevista/<id>/pergunta/<n>` | Próxima pergunta |
| POST | `/entrevista/<id>/responder` | Salva resposta + avalia |
| POST | `/entrevista/<id>/finalizar` | Marca concluída + relatório |
| GET | `/entrevista/<id>/relatorio` | Página do relatório |
| GET | `/entrevista/<id>/exportar-pdf` | Download PDF |

### Tempo Estimado de Implementação

| Fase | Horas | Atividades |
|------|-------|-----------|
| 1: Backend Base | 1-2 | Models + Migrations |
| 2: Endpoints | 2-3 | Routes + Validações |
| 3: IA | 2-3 | Integração Groq |
| 4: Frontend | 3-4 | Templates + CSS/JS |
| 5: PDF + Polish | 1-2 | Export + Testes |
| **TOTAL** | **9-14h** | |

---

## 🔗 Links Rápidos

### Documentação
- [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) — Especificação oficial
- [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) — Diagramas e fluxos
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — Guia rápido
- [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md) — Código pronto

### Código Existente (Reutilizar)
- `src/services/model.py` — Chamar IA (já existe)
- `src/services/parser.py` — Extrair currículo
- `src/services/pdf.py` — Geração PDF base
- `src/utils.py` — Validações, upload, sanitização
- `src/app.py` — App factory pattern

### Banco de Dados
- `src/models/user.py` — User model base
- `src/models/chat_session.py` — Exemplo de model com JSON
- `migrations/` — Ver padrão de migration

### Testes
- Criar em `tests/test_entrevista.py` (não mencionado na spec original)
- Pattern: ver testes existentes

---

## ⚠️ Notas Importantes

1. **Chat Existente:** Será preservado, não substituído. Pode ser renomeado.

2. **PDF Export:** Reutiliza gerador existente (`services/pdf.py`). Estender com função específica.

3. **IA/Groq:** Usar função `call_model()` existente em `services/model.py`. Criar funções wrapper para cada prompt.

4. **Rate Limiting:** Aplicar em todos endpoints. Pattern: `@limiter.limit("X per minute")`

5. **Autenticação:** Usar `@login_required` existente em utils.

6. **Máximo Aprofundamentos:** 2 por pergunta (como solicitado).

7. **Número de Perguntas:** 5-8 (determinado pela IA durante planejamento).

8. **Migração BD:** Usar Alembic (`alembic revision --autogenerate`).

---

## 🚀 Próximos Passos

1. **✅ Revisar especificação** com time
2. **✅ Validar arquitetura** com tech lead
3. **✅ Criar models** e migração
4. **✅ Implementar routes** (backend)
5. **✅ Integrar IA** (funções em model.py)
6. **✅ Criar templates** (frontend)
7. **✅ Estender PDF** (export)
8. **✅ Testes manuais**
9. **✅ Deploy**

---

## 📞 Dúvidas Frequentes

**P: O chat existente será deletado?**  
R: Não. Chat é preservado. Pode ser renomeado para "Assistente Geral" ou similar.

**P: Quantas perguntas de aprofundamento?**  
R: Máximo 2 por pergunta principal (total máximo: 16 interações em 8 perguntas).

**P: PDF pode ser customizado?**  
R: Sim. Estender `gerar_pdf_relatorio_entrevista()` em `services/pdf.py`.

**P: Como interromper uma entrevista no meio?**  
R: Status fica `em_andamento`. User pode voltar para continuar (implementar recuperação).

**P: Quantas entrevistas por usuário?**  
R: Ilimitadas (sem limite no model).

**P: Rate limiting é necessário?**  
R: Sim. `@limiter.limit("20 per minute")` mínimo.

---

## 📝 Checklist de Implementação

- [ ] Revisar todos os 5 documentos
- [ ] Criar modelos (Entrevista, PerguntaEntrevista)
- [ ] Gerar e aplicar migração Alembic
- [ ] Implementar 7 endpoints
- [ ] Integrar 3 funções IA com Groq
- [ ] Criar 3 templates HTML
- [ ] Criar CSS e JavaScript
- [ ] Estender função PDF
- [ ] Testes manuais (fluxo completo)
- [ ] Testar aprofundamentos
- [ ] Testar PDF export
- [ ] Validar segurança (prompt injection, etc)
- [ ] Deploy em produção

---

## 📄 Licença e Proprietário

- **Disciplina:** Sistemas Distribuídos (11º Período)
- **Projeto:** SD_Trabalho
- **Funcionalidade:** Simulador de Entrevistas (Reformulação)
- **Data de Criação:** Junho 2026

---

**Última atualização:** 12 de junho de 2026

Para dúvidas ou atualizações, consulte os documentos originais.

