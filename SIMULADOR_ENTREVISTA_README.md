# 🎯 Simulador de Entrevistas - Reformulação 2026

> Jornada estruturada para simulação de entrevistas técnicas com IA

---

## 📋 O que foi criado?

Uma reformulação completa do módulo de entrevistas original, transformando-o em uma **jornada estruturada em 3 fases**:

### Fase 1️⃣: Planejamento
- Upload de currículo (PDF/DOC)
- Descrição da vaga
- IA analisa e gera plano com número de perguntas

### Fase 2️⃣: Execução  
- IA faz perguntas uma por vez
- Usuário responde por escrito
- IA faz até 2 aprofundamentos por pergunta
- Ciclo repete para todas perguntas

### Fase 3️⃣: Relatório
- Análise completa gerada pela IA
- Exportável em PDF
- Pontos fortes, fracos e recomendações

---

## 📚 Documentação

### Principais Documentos

| Documento | Descrição | Público |
|-----------|-----------|---------|
| [**ESPECIFICACAO_SIMULADOR_ENTREVISTA.md**](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) | Especificação técnica completa **[LEIA PRIMEIRO]** | Todos |
| [**DIAGRAMAS_SIMULADOR_ENTREVISTA.md**](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) | Fluxogramas, diagramas e arquitetura | Developers, Testers |
| [**QUICK_REFERENCE.md**](./QUICK_REFERENCE.md) | Guia rápido de implementação | Developers |
| [**EXEMPLOS_CODIGO.md**](./EXEMPLOS_CODIGO.md) | Código pronto para usar (copy-paste) | Developers |
| [**MEMORANDO_TECNICO.md**](./MEMORANDO_TECNICO.md) | Índice geral e guia de navegação | Todos |

---

## 🚀 Como Começar

### Para Tech Leads / Arquitetos
1. Ler [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (seção "Resumo Executivo")
2. Estudar [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md) (arquitetura e fluxos)
3. Revisar [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md) (patterns)

### Para Developers
1. Seguir [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (checklist)
2. Implementar com [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md) (código pronto)
3. Consultar [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md) (regras)

### Para QA / Testers
1. Entender fluxos em [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md)
2. Executar testes em [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (testes manuais)
3. Validar requisitos em [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md)

---

## 🏗️ Estrutura de Implementação

### Novos Arquivos
```
src/
  models/
    └─ entrevista.py                   # 2 models: Entrevista, PerguntaEntrevista
  routes/
    └─ entrevista.py                   # Blueprint com 7 endpoints
  templates/
    ├─ entrevista_planejamento.html
    ├─ entrevista_execucao.html
    └─ entrevista_relatorio.html
  static/
    ├─ entrevista.css
    └─ entrevista.js
migrations/versions/
  └─ XXXX_add_entrevista_tables.py     # Migração Alembic
```

### Arquivos Modificados
```
src/
  app.py                               # Registrar blueprint + import model
  models/user.py                       # Adicionar relationship
  services/model.py                    # 3 funções IA
  services/pdf.py                      # 1 função PDF export
```

---

## 🤖 Tecnologias

- **Backend:** Flask, SQLAlchemy, Alembic
- **IA:** Groq API (LLM Mixtral)
- **PDF:** ReportLab
- **Frontend:** HTML5, CSS3, JavaScript
- **Banco:** Mesmo da aplicação (PostgreSQL/SQLite)

---

## 📊 Principais Features

✅ **3 Fases Estruturadas:** Planejamento → Execução → Relatório  
✅ **IA Inteligente:** Gera perguntas e avalia respostas com Groq  
✅ **Aprofundamentos:** Até 2 por pergunta (configurable)  
✅ **PDF Export:** Relatório completo em PDF  
✅ **Multiusuário:** Cada usuário tem suas entrevistas  
✅ **Rate Limiting:** Proteção contra abuso  
✅ **Security:** Prompt injection detection, sanitização  
✅ **Chat Preservado:** Novo módulo não substitui chat existente  

---

## ⚡ Quick Stats

| Métrica | Valor |
|---------|-------|
| Arquivos a Criar | 7 |
| Arquivos a Modificar | 4 |
| Endpoints | 7 |
| Models | 2 |
| Templates | 3 |
| Funções IA | 3 |
| Tempo Estimado | 9-14 horas |

---

## 🔌 Endpoints da API

```
POST   /entrevista/gerar-plano              Gera plano (CV + vaga)
GET    /entrevista/<id>                     Dados da entrevista
GET    /entrevista/<id>/pergunta/<n>        Próxima pergunta
POST   /entrevista/<id>/responder           Salva resposta + avalia
POST   /entrevista/<id>/finalizar           Marca concluída + relatório
GET    /entrevista/<id>/relatorio           Página do relatório
GET    /entrevista/<id>/exportar-pdf        Download PDF
```

---

## 📦 Banco de Dados

### Novas Tabelas

**`entrevista`**
- id, user_id, curriculo_arquivo, vaga_descricao
- numero_perguntas, plano_entrevista, status
- criado_em, atualizado_em, finalizado_em
- relatorio_final

**`pergunta_entrevista`**
- id, entrevista_id, numero_sequencial
- pergunta_principal, resposta_usuario
- avaliacao_resposta, perguntas_aprofundamento
- criado_em, respondido_em

---

## 🎯 Roadmap de Implementação

### Sprint 1: Backend Base (1-2 horas)
- Criar models e migração
- Registrar blueprint

### Sprint 2: Endpoints (2-3 horas)
- Implementar 7 rotas
- Validações básicas

### Sprint 3: IA Integration (2-3 horas)
- 3 funções de IA com Groq
- Testes de prompt

### Sprint 4: Frontend (3-4 horas)
- 3 templates HTML
- CSS + JavaScript

### Sprint 5: Polish (1-2 horas)
- PDF export
- Testes finais
- Deployment

---

## ✅ Checklist

- [ ] Ler ESPECIFICACAO_SIMULADOR_ENTREVISTA.md
- [ ] Ler EXEMPLOS_CODIGO.md
- [ ] Criar models + migração
- [ ] Criar routes (7 endpoints)
- [ ] Integrar IA (3 funções)
- [ ] Criar templates (3 arquivos)
- [ ] CSS + JavaScript
- [ ] PDF export
- [ ] Testes manuais
- [ ] Deploy

---

## 🔐 Segurança

✅ Autenticação obrigatória (@login_required)  
✅ Validação de permissões (usuário)  
✅ Detecção de prompt injection  
✅ Sanitização de inputs  
✅ Validação de tipos de arquivo  
✅ Rate limiting em endpoints críticos  
✅ Limite de tamanho de arquivo (5MB)  

---

## 📞 FAQ

**P: O chat existente será deletado?**  
R: Não. Chat é preservado. Pode ser renomeado para "Assistente Geral".

**P: Quantas perguntas de aprofundamento?**  
R: Máximo 2 por pergunta principal.

**P: Posso customizar o PDF?**  
R: Sim. Estender função `gerar_pdf_relatorio_entrevista()`.

**P: Como usar o chat e entrevista juntos?**  
R: São dois módulos separados. Menu na sidebar permite escolher.

**P: Quantas entrevistas por usuário?**  
R: Ilimitadas (sem cap no model).

---

## 📁 Documentação Auxiliar

```
SD_Trabalho/
├── README.md (este arquivo)
├── ESPECIFICACAO_SIMULADOR_ENTREVISTA.md    ⭐ [LEIA PRIMEIRO]
├── DIAGRAMAS_SIMULADOR_ENTREVISTA.md
├── QUICK_REFERENCE.md
├── EXEMPLOS_CODIGO.md
├── MEMORANDO_TECNICO.md
└── ...resto do projeto
```

---

## 🚀 Próximos Passos

1. **Leia** [ESPECIFICACAO_SIMULADOR_ENTREVISTA.md](./ESPECIFICACAO_SIMULADOR_ENTREVISTA.md)
2. **Implemente** com [EXEMPLOS_CODIGO.md](./EXEMPLOS_CODIGO.md)
3. **Consulte** [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) durante dev
4. **Visualize** [DIAGRAMAS_SIMULADOR_ENTREVISTA.md](./DIAGRAMAS_SIMULADOR_ENTREVISTA.md)
5. **Teste** tudo conforme [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

---

## 📌 Notas Importantes

- ⚠️ Chat existente é **preservado**, não substituído
- ⚠️ Máximo **2 aprofundamentos** por pergunta
- ⚠️ Número de perguntas: **5-8** (determinado pela IA)
- ⚠️ Usar Groq API para chamadas de IA
- ⚠️ Reutilizar `services/pdf.py` existente
- ⚠️ Aplicar rate limiting em todos endpoints críticos

---

## 📞 Contato & Suporte

Para dúvidas sobre:
- **Arquitetura:** Consulte ESPECIFICACAO_SIMULADOR_ENTREVISTA.md
- **Implementação:** Consulte EXEMPLOS_CODIGO.md
- **Fluxos:** Consulte DIAGRAMAS_SIMULADOR_ENTREVISTA.md
- **Referência Rápida:** Consulte QUICK_REFERENCE.md
- **Geral:** Consulte MEMORANDO_TECNICO.md

---

**Criado em:** Junho 2026  
**Disciplina:** Sistemas Distribuídos (11º Período)  
**Projeto:** SD_Trabalho

