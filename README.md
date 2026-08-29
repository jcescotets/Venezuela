# Family Office — Sistema Agentico

Sistema multi-agente de IA para operaciones de inversión de family office. 20 agentes especializados organizados en 5 capas toman decisiones de inversión colaborativas con debate estructurado, poder de veto y memoria persistente.

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│              CAPA 1: DIRECCIÓN                  │
│  CIO  ·  Head of Tax Strategy  ·  Comité       │
├─────────────────────────────────────────────────┤
│              CAPA 2: ANÁLISIS                   │
│  Macro  ·  Fundamental  ·  Técnico/Quant       │
│  Crédito/Bonos  ·  Activos Reales              │
├─────────────────────────────────────────────────┤
│           CAPA 3: FISCAL & LEGAL                │
│  España · Portugal · Panamá · Barbados          │
│  EE.UU. · Venezuela · Cross-Border              │
├─────────────────────────────────────────────────┤
│          CAPA 4: RIESGO & CONTROL               │
│  Risk Manager (VETO)  ·  Tax Risk & Audit       │
├─────────────────────────────────────────────────┤
│           CAPA 5: OPERACIONES                   │
│  Portfolio Ops  ·  Opportunity Scanner          │
└─────────────────────────────────────────────────┘
```

## Pipeline de Decisión (7 fases)

1. **Análisis Paralelo** — 5 agentes producen vistas independientes (sin ver las de otros)
2. **Evaluación Fiscal** — 7 agentes jurisdiccionales evalúan impacto tributario
3. **Debate del Comité** — Comité de Inversión sintetiza todas las vistas y contradicciones
4. **Veto Gate** — Risk Manager y Head of Tax pueden bloquear la operación
5. **Síntesis CIO** — El Chief Investment Officer produce la recomendación final
6. **Validación** — Regla de 5 condiciones asegura cumplimiento de requisitos
7. **Presentación** — Reporte formateado para decisión humana

## Inicio Rápido

### Requisitos

- Python 3.11+
- API keys: Anthropic (obligatoria), OpenAI (opcional), Alpha Vantage, FRED

### Instalación

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus API keys
```

### Uso

```bash
# Dashboard web (por defecto en http://localhost:8000)
python main.py

# Modo CLI interactivo
python main.py --cli

# Ver estructura organizacional
python main.py --org

# Puerto personalizado
python main.py --port 9000
```

### Comandos CLI

| Comando     | Descripción                          |
|-------------|--------------------------------------|
| `org`       | Ver organización de agentes          |
| `macro`     | Briefing macroeconómico              |
| `scan`      | Escanear oportunidades               |
| `analyze`   | Análisis completo de inversión       |
| `portfolio` | Ver portfolio actual                 |
| `criteria`  | Ver criterios de inversión           |

## Estructura del Proyecto

```
family_office/
├── agents/
│   ├── analysis/        # Macro, Fundamental, Técnico, Crédito, Real Assets
│   ├── direction/       # CIO, Head of Tax, Investment Committee
│   ├── fiscal/          # 7 jurisdicciones + Cross-Border
│   ├── operations/      # Portfolio Ops, Opportunity Scanner
│   └── risk/            # Risk Manager, Tax Risk & Audit
├── core/
│   ├── base_agent.py    # Clase base abstracta de agentes
│   ├── llm_client.py    # Cliente LLM (Anthropic/OpenAI)
│   ├── message_bus.py   # Comunicación inter-agentes
│   ├── models.py        # Modelos de datos (Pydantic)
│   └── registry.py      # Registro y ciclo de vida de agentes
├── config/              # Settings desde .env
├── dashboard/           # FastAPI + HTML dashboard
├── integrations/        # Market data (yfinance, FRED, Alpha Vantage)
├── memory/              # Persistencia de decisiones y memoria
├── pipeline/            # Debate engine, Decision pipeline, Veto gate
└── orchestrator.py      # Orquestador principal
```

## Principios de Diseño

- **Análisis independiente** — Los agentes no ven el trabajo de otros antes de enviar (evita groupthink)
- **Poder de veto** — Solo Risk Manager y Head of Tax pueden bloquear decisiones
- **Debate estructurado** — El Comité sintetiza contradicciones en lugar de ocultarlas
- **Memoria persistente** — Todas las decisiones se registran con supuestos para detección de patrones
- **Asíncrono** — Full async/await para ejecución paralela de agentes
- **Bus de mensajes** — Toda comunicación pasa por el bus (sin comunicación directa agente-a-agente)

## Variables de Entorno

| Variable               | Descripción                     | Requerida |
|------------------------|---------------------------------|-----------|
| `ANTHROPIC_API_KEY`    | API key de Anthropic            | Sí        |
| `OPENAI_API_KEY`       | API key de OpenAI               | No        |
| `ALPHA_VANTAGE_API_KEY`| API key de Alpha Vantage        | No        |
| `FRED_API_KEY`         | API key de FRED                 | No        |
| `DASHBOARD_HOST`       | Host del dashboard (0.0.0.0)    | No        |
| `DASHBOARD_PORT`       | Puerto del dashboard (8000)     | No        |
| `DATABASE_URL`         | URL de base de datos SQLite     | No        |
| `LOG_LEVEL`            | Nivel de logging (INFO)         | No        |
