#!/usr/bin/env python3
"""
Ejecución del pipeline — Caso REAL: J Holding Group LDA (Portugal)
===================================================================
Portafolio real en Pershing/Miura, Enero 2026.
Propietario: residente fiscal España (100% dueño de J Holding Group LDA).

Estructura:
  Propietario (ES fiscal resident)
      ↕ (dividendos solo si reparte)
  J Holding Group LDA (Portugal)
      ↕ (cuenta a nombre de J Holding)
  Pershing / Miura (custodio/broker)
      ├── ABANCA 6.125% bond EUR 825,280 (96.7%)
      ├── iShares Aerospace & Defense ETF (ITA) USD 9,295
      ├── Select Sector Financial SPDR (XLF) USD 8,550
      └── Cash EUR 12,409 + USD 973

Total portfolio: USD 1,015,250.12
Income anual estimado: USD 58,401.36

Uso:
    python run_jholding_case.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from family_office.core.models import (
    AgentRole,
    DecisionStatus,
    InvestmentProposal,
    FiscalImpact,
)
from family_office.orchestrator import FamilyOfficeOrchestrator

# ═════════════════════════════════════════════════════════════════
# PORTAFOLIO REAL — J Holding Group LDA @ Pershing/Miura
# ═════════════════════════════════════════════════════════════════

PORTFOLIO = {
    "entity": "J Holding Group LDA",
    "jurisdiction": "Portugal",
    "entity_type": "Sociedade por Quotas (LDA)",
    "owner": "Residente fiscal España — 100% participación",
    "custodian": "Pershing LLC (BNY Mellon)",
    "broker": "Miura Global (España)",
    "report_date": "Enero 2026",
    "total_value_usd": 1_015_250.12,
    "total_value_eur": 837_689.40,
    "accrued_interest_usd": 6_961.88,
    "estimated_annual_income_usd": 58_401.36,
    "positions": [
        {
            "name": "ABANCA Corporación Bancaria S.A. 6.125%",
            "type": "Corporate Bond",
            "isin": "ES0865936035",
            "security_id": "E0001JAR3",
            "issuer_country": "España",
            "quantity": 800_000,
            "market_price": 103.16,
            "market_value_eur": 825_280.00,
            "market_value_usd": 981_670.56,
            "coupon_rate": 6.125,
            "maturity": "09/19/2025 (REG DTD)",
            "accrued_interest_eur": 5_852.78,
            "estimated_annual_income_eur": 49_000.00,
            "estimated_yield": 5.93,
            "pct_portfolio": 96.7,
            "margin_position": True,
        },
        {
            "name": "iShares US Aerospace & Defense ETF",
            "type": "ETF",
            "ticker": "ITA",
            "cusip": "464288760",
            "issuer_country": "Estados Unidos",
            "quantity": 40,
            "market_price_usd": 232.38,
            "market_value_usd": 9_295.20,
            "estimated_annual_income_usd": 0.0,
            "estimated_yield": 0.0,
            "pct_portfolio": 0.9,
            "margin_position": True,
        },
        {
            "name": "Select Sector SPDR Financial ETF",
            "type": "ETF",
            "ticker": "XLF",
            "cusip": "81369Y605",
            "issuer_country": "Estados Unidos",
            "quantity": 160,
            "market_price_usd": 53.44,
            "market_value_usd": 8_550.40,
            "estimated_annual_income_usd": 115.14,
            "estimated_yield": 1.34,
            "pct_portfolio": 0.8,
            "margin_position": True,
        },
        {
            "name": "Cash EUR (Global Cash + Margin)",
            "type": "Cash",
            "currency": "EUR",
            "market_value_eur": 12_409.40,
            "market_value_usd": 14_760.99,
            "pct_portfolio": 1.5,
        },
        {
            "name": "Cash USD (Interlink Ins Bank Deposit)",
            "type": "Cash",
            "currency": "USD",
            "market_value_usd": 972.97,
            "pct_portfolio": 0.1,
        },
    ],
    "currency_allocation": {
        "EUR": {"pct": 98.0, "value_local": 837_689.40, "value_usd": 996_431.55},
        "USD": {"pct": 2.0, "value_local": 18_818.57, "value_usd": 18_818.57},
    },
}

# ═════════════════════════════════════════════════════════════════
# Respuestas estáticas por agente — CASO J HOLDING GROUP LDA
# ═════════════════════════════════════════════════════════════════

STATIC_RESPONSES: dict[str, str] = {}

# ── Capa 2: Análisis ──────────────────────────────────────────

STATIC_RESPONSES["macro_geopolitics"] = """\
HALLAZGOS CLAVE:
- Portfolio concentrado 96.7% en bono corporativo español (ABANCA 6.125%)
- España: PIB +2.3%, sector bancario sólido post-consolidación, ABANCA sin estrés crediticio
- ABANCA: banco gallego, rating investment grade, fusión con Banesco refuerza capitalización
- BCE en fase de recortes graduales de tasas: favorable para valoración de bonos corporativos
- Entorno crediticio europeo estable: defaults corporativos en mínimos (0.8% trailing 12m)
- Riesgo geopolítico bajo para deuda bancaria española: sin exposición a conflictos activos
- ETFs US (ITA + XLF): exposición marginal (1.7%) a defensa y financieras US

RIESGOS:
- Concentración extrema en un solo emisor (ABANCA = 96.7% del portfolio)
- Riesgo de crédito bancario español: sensible a crisis inmobiliaria o recesión EU
- Riesgo regulatorio bancario: incremento de requisitos de capital (Basilea IV) podría presionar márgenes
- Tipo de cambio EUR/USD: exposición mínima (2% en USD)
- Riesgo de tasas: si BCE sube tasas inesperadamente, el bono pierde valor de mercado

RECOMENDACIÓN:
El activo principal (ABANCA 6.125%) tiene fundamentales sólidos en el entorno macro actual.
Sin embargo, la concentración del 96.7% en un solo emisor es el riesgo dominante del portfolio.
Convicción sobre el macro: 0.72. Preocupación por concentración: ALTA.
"""

STATIC_RESPONSES["fundamental"] = """\
HALLAZGOS CLAVE:
- ABANCA 6.125% (ES0865936035): bono senior, cupón fijo 6.125%, yield actual 5.93%
- Precio de mercado 103.16 (sobre par): indica que el mercado percibe bajo riesgo de crédito
- Income anual: EUR 49,000 sobre nominal de EUR 800,000
- ABANCA: CET1 ratio ~12.5%, NPL ratio ~2.8%, rentabilidad mejorada post-fusión Banesco
- Comparación: yield del 5.93% es atractivo vs. benchmark (iBoxx EUR Corps ~3.8%)
- Prima sobre benchmark: +213bp, compensación razonable por riesgo single-name
- ETF ITA (Aerospace): sector defensivo US con backlog récord, valoración estirada (P/E 22x)
- ETF XLF (Financials): yield 1.34%, beneficiado por curva de tasas normalizada

RIESGOS:
- Single-name concentration: ABANCA = 96.7% — si ABANCA tiene evento de crédito, pérdida catastrófica
- Recovery rate en caso de default bancario senior: históricamente 40-60%
- Pérdida máxima en default: EUR 330,000-495,000 (40-60% de EUR 825,280)
- Bono cotiza sobre par (103.16): pull-to-par reducirá valor si se mantiene hasta vencimiento
- ETFs US: posiciones inmateriales ($17,845 = 1.7%), no mueven la aguja del portfolio

RECOMENDACIÓN:
El bono ABANCA es fundamentalmente sólido INDIVIDUALMENTE. El problema NO es el activo,
es la CONCENTRACIÓN. Un portfolio de USD 1M con 96.7% en un solo emisor bancario viola
cualquier principio de diversificación prudente. Income atractivo (EUR 49K/año) pero
riesgo de cola inaceptable. Convicción sobre ABANCA: 0.70. Convicción sobre el portfolio: 0.30.
"""

STATIC_RESPONSES["technical_quant"] = """\
HALLAZGOS CLAVE:
- Bono ABANCA 6.125%: cotiza a 103.16 (sobre par), spread vs. benchmark estable
- Volatilidad del bono: baja (típico de renta fija IG), desviación estándar ~2-3% anual
- VaR 95% 1-día del portfolio: ~EUR 12,500 (1.5% del valor total)
- CVaR 95%: ~EUR 18,750 (tail risk por concentración single-name)
- Correlación interna del portfolio: irrelevante — un solo activo domina al 96.7%
- ETF ITA: tendencia alcista, RSI 62, sector con momentum positivo
- ETF XLF: lateralizado, RSI 51, sin señal clara

RIESGOS:
- En escenario de estrés crediticio (downgrade ABANCA): caída del bono -15% a -25%
- Drawdown máximo estimado en crisis bancaria: EUR 125,000-210,000 (-15% a -25%)
- Liquidez del bono: MEDIA — mercado OTC, bid-ask spread estimado 50-100bp
- ETFs US: liquidez excelente pero posiciones irrelevantes en tamaño

RECOMENDACIÓN:
Desde perspectiva cuantitativa, el portfolio tiene perfil de riesgo asimétrico:
income estable (EUR 49K/año) vs. tail risk catastrófico (pérdida EUR 330K+ en default).
Ratio Sharpe del portfolio es artificialmente alto por concentración.
El riesgo real está subestimado por métricas estándar. Convicción 0.45.
"""

STATIC_RESPONSES["credit_bonds"] = """\
HALLAZGOS CLAVE:
- ABANCA 6.125% (ES0865936035): bono senior unsecured, emisor español
- Rating estimado: BBB/BBB- (investment grade bajo)
- Cupón 6.125% muy por encima de mercado actual (nuevas emisiones IG EUR ~3.5-4.5%)
- Esto indica que fue emitido en ventana de tasas altas o lleva prima por estructura
- Spread vs. Bund: ~250bp, apropiado para banco mediano español
- ABANCA: capitalización adecuada, sin señales de estrés inminente
- Posición en margin account: ¿se usa apalancamiento? Riesgo de margin call en escenario adverso
- Los EUR 12,409 de cash + EUR 159 margin balance sugieren poco colchón para margin

RIESGOS:
- CONCENTRACIÓN CRÍTICA: 96.7% en un solo bono de un solo banco
- Margin account: si el bono cae -10%, margin call podría forzar venta a pérdida
- Riesgo de subordinación: verificar si es senior preferred o senior non-preferred (bail-in)
- Riesgo de extensión: si tiene cláusula de call, el emisor puede extender
- Cash disponible (EUR 12,409) es insuficiente como buffer para un portfolio de EUR 837K
- Si ABANCA sufre downgrade, el spread se ampliaría 100-200bp → caída del -5% a -10%

RECOMENDACIÓN:
El bono individualmente es ACEPTABLE para una porción de un portfolio diversificado (5-10%).
Al 96.7% del portfolio, el riesgo es INACEPTABLE desde cualquier métrica crediticia.
El uso de margin account agrava el riesgo (margin call en escenario de estrés).
URGENTE: diversificar al menos 50-60% del portfolio fuera de este emisor.
Convicción sobre el bono: 0.65. Convicción sobre la posición al 96.7%: 0.15.
"""

STATIC_RESPONSES["real_assets"] = """\
HALLAZGOS CLAVE:
- Portfolio 100% en activos financieros (bono + ETFs + cash)
- Sin exposición a activos reales (inmobiliario, commodities, infraestructura)
- Para un portfolio de USD 1M, la falta de diversificación en real assets amplifica riesgo
- REITs europeos: yield 4.5-5.5%, diversificación vs. riesgo bancario español
- Oro: hedge contra escenarios de crisis bancaria, correlación negativa con crédito bancario

RIESGOS:
- Sin hedge contra inflación (bono a tasa fija)
- Sin hedge contra crisis bancaria (100% expuesto a banca española)
- En escenario de crisis bancaria EU, tanto el bono ABANCA como los ETF financieros (XLF) caerían

RECOMENDACIÓN:
Agregar 10-15% en real assets (REITs, infraestructura) como diversificación.
En crisis bancaria, real assets y oro actuarían como contrapeso.
Convicción: 0.50. La prioridad NO es agregar real assets sino diversificar el bono.
"""

# ── Capa 3: Fiscal ────────────────────────────────────────────

STATIC_RESPONSES["fiscal_spain"] = """\
HALLAZGOS CLAVE:
- Propietario: residente fiscal España, 100% dueño de J Holding Group LDA (Portugal)
- J Holding es una sociedad portuguesa (LDA) con cuenta en Pershing/Miura
- POSICIÓN PRINCIPAL: Bono ABANCA (emisor ESPAÑOL, ISIN ES0865936035)

ANÁLISIS CFC — Art. 100 LIS (Ley del Impuesto sobre Sociedades):
- J Holding Group LDA tiene 100% de rentas pasivas (cupones de bono + dividendos ETFs)
- El propietario español posee >50% de la entidad (posee 100%)
- Tipo efectivo en Portugal (IRC 21%) es <75% del tipo español para sociedades (25% × 75% = 18.75%)
- RESULTADO: IRC Portugal al 21% > 18.75% → POTENCIALMENTE FUERA DEL UMBRAL CFC POR TIPO
- PERO: Art. 100.3 LIS — exención EU si hay "razones económicas válidas" y "actividad real"
- ¿Tiene J Holding sustancia en Portugal? (oficina, empleados, decisiones en PT?)
- Si NO hay sustancia → la exención EU NO aplica → CFC puede aplicar parcialmente

RETENCIÓN EN ORIGEN SOBRE CUPONES ABANCA:
- ABANCA es emisor español → cupones pagados a J Holding (no residente en ES)
- Retención ES sobre intereses a entidades EU: 0% bajo Directiva de Intereses y Cánones EU
  PERO: requiere que J Holding sea el "beneficiario efectivo" y no una entidad interpuesta
- Si AEAT considera que J Holding es interpuesta → retención del 19% en origen sobre cupones
- Cupones brutos EUR 49,000/año → retención potencial: EUR 9,310 si no aplica exención

IRPF DEL PROPIETARIO:
- Mientras J Holding NO reparta dividendos → no hay tributación directa en IRPF
- Si CFC aplica: imputación de rentas de J Holding en IRPF del propietario
- Dividendos de J Holding → España: IRPF ahorro 19-28%
- CDI Portugal-España: retención PT sobre dividendos a ES reducida al 15%
- Modelo 720: obligatorio declarar participación en J Holding (>EUR 50K en extranjero)

RIESGOS:
- FLAG CFC: MEDIO-ALTO — depende de sustancia real de J Holding en Portugal
- FLAG SUBSTANCE: ALTO si J Holding no tiene oficina/empleados en PT
- FLAG RETENCIÓN ABANCA: MEDIO — riesgo de que AEAT niegue exención de retención
- FLAG MODELO 720: cumplimiento obligatorio, sanción por omisión
- FLAG CONCENTRACIÓN: no fiscal per se, pero agrava el impacto de cualquier contingencia

RECOMENDACIÓN:
Estructura VIABLE fiscalmente SI J Holding tiene sustancia real en Portugal y razón
económica válida más allá de la mera tenencia pasiva. El test de CFC es el riesgo
central. Tax drag estimado: 21% IRC PT + 15% retención PT→ES + 19-28% IRPF sobre
dividendos efectivamente repartidos. Retorno neto estimado sobre cupón ABANCA:
EUR 49,000 bruto → ~EUR 28,000-32,000 neto al propietario (si reparte 100%).
"""

STATIC_RESPONSES["fiscal_portugal"] = """\
HALLAZGOS CLAVE:
- J Holding Group LDA: sociedad portuguesa, régimen IRC (Imposto sobre o Rendimento Coletivo)
- Tipo IRC general: 21% sobre beneficios
- Derrama municipal: +1.5% adicional (varía por municipio)
- Tipo efectivo total PT: ~22.5%

TRIBUTACIÓN DE LOS INGRESOS EN J HOLDING:
1. Cupones ABANCA (EUR 49,000/año):
   - Intereses de fuente española recibidos por entidad PT
   - Retención ES: 0% si aplica Directiva Intereses/Cánones EU (requiere beneficiario efectivo)
   - IRC Portugal: 21% sobre cupones recibidos = EUR 10,290/año
   - Derrama: +~EUR 735/año
   - Resultado: EUR 49,000 - EUR 11,025 IRC/derrama = EUR 37,975 neto en J Holding

2. Dividendos ETFs US (ITA + XLF, ~USD 115/año):
   - Retención US: 15% (CDI US-PT) sobre dividendos = ~USD 17
   - IRC Portugal: 21% sobre dividendo bruto con crédito por retención US
   - Impacto: inmaterial dado el monto (~USD 115/año)

3. Intereses cash (USD 0.72/año):
   - Inmaterial

DISTRIBUCIÓN DE DIVIDENDOS DE J HOLDING AL PROPIETARIO (ES):
- Retención PT sobre dividendos a socios no residentes: 25% (sin CDI) o 15% (CDI PT-ES)
- CDI Portugal-España aplicable: retención del 15%
- Si J Holding distribuye EUR 37,975 neto → retención PT 15% = EUR 5,696
- Propietario recibe: EUR 32,279 → declara en IRPF España con crédito por retención PT

OBLIGACIONES FORMALES EN PORTUGAL:
- Declaración IRC anual (Modelo 22)
- IES (Informação Empresarial Simplificada)
- Contabilidad organizada (TOC obligatorio)
- Costo estimado de mantenimiento: EUR 3,000-5,000/año (TOC + declaraciones + registered office)

RIESGOS:
- FLAG SUBSTANCE: Si J Holding no tiene oficina/TOC dedicado/decisiones locales
- Beneficio efectivo (beneficial ownership): PT authorities podrían cuestionar si J Holding
  es beneficiario efectivo de los cupones ABANCA o mero conduit
- Derrama municipal varía: verificar municipio de registro de la LDA

RECOMENDACIÓN:
Fiscalmente, J Holding tributa al ~22.5% en Portugal sobre sus ingresos.
Costo anual de mantenimiento: EUR 3,000-5,000. Para un income de EUR 49,000,
el costo operativo representa ~6-10% adicional del income bruto.
La estructura es FUNCIONAL pero el costo fiscal + operativo es significativo.
"""

STATIC_RESPONSES["fiscal_panama"] = """\
HALLAZGOS CLAVE:
- No hay presencia panameña en la estructura actual (J Holding es portuguesa)
- Panamá no es relevante para este caso
- Incluir Panamá añadiría complejidad sin beneficio fiscal

RIESGOS:
- Ninguno relevante

RECOMENDACIÓN:
Sin impacto. No involucrar jurisdicciones adicionales.
"""

STATIC_RESPONSES["fiscal_barbados"] = """\
HALLAZGOS CLAVE:
- No hay presencia en Barbados en la estructura actual
- Barbados no es relevante para este caso

RIESGOS:
- Ninguno relevante

RECOMENDACIÓN:
Sin impacto. No agregar jurisdicciones offshore.
"""

STATIC_RESPONSES["fiscal_us"] = """\
HALLAZGOS CLAVE:
- J Holding tiene dos ETFs US en Pershing: ITA (USD 9,295) y XLF (USD 8,550)
- Total exposición US: USD 17,845 (1.7% del portfolio)
- Dividendos ETFs US → J Holding (entidad portuguesa):
  * Retención US: 30% estándar para NRA entities
  * CDI US-Portugal: reduce retención a 15% (requiere W-8BEN-E)
  * J Holding debe presentar Form W-8BEN-E a Pershing con tax ID portugués
- Dividendo anual estimado: USD 115 (XLF) + ~USD 0 (ITA reporta 0)
- Retención US sobre USD 115: ~USD 17 (al 15% con CDI)
- FATCA: Pershing reporta automáticamente al IRS

ESTATE TAX US:
- No aplica: J Holding es entidad (no persona física)
- Activos US situs (ETFs) están en la entidad portuguesa → sin estate tax exposure

RIESGOS:
- Impacto fiscal US INMATERIAL: total income US es USD 115/año
- Si no se presenta W-8BEN-E, retención sube de 15% a 30% (~USD 17 adicionales)
- Verificar que Pershing tiene W-8BEN-E vigente para J Holding

RECOMENDACIÓN:
Exposición US irrelevante fiscalmente (USD 115/año de dividendos).
Asegurar que W-8BEN-E esté actualizado en Pershing. Sin acción adicional requerida.
"""

STATIC_RESPONSES["fiscal_venezuela"] = """\
HALLAZGOS CLAVE:
- El propietario es residente fiscal en ESPAÑA, no en Venezuela
- J Holding Group LDA es portuguesa, sin nexo con Venezuela
- Sin impacto fiscal venezolano en esta estructura

RIESGOS:
- Verificar que no existe residencia fiscal dual ES/VE
- Si hay doble residencia: ISLR Venezuela podría reclamar tributación

RECOMENDACIÓN:
Sin impacto desde Venezuela. Confirmar ausencia de residencia fiscal dual.
"""

STATIC_RESPONSES["cross_border"] = """\
HALLAZGOS CLAVE:
- FLUJO PRINCIPAL: España (ABANCA cupones) → Portugal (J Holding LDA) → España (propietario)
- El flujo es CIRCULAR: renta originada en España, pasa por Portugal, vuelve a España
- Flujo secundario: US (dividendos ETFs) → Portugal (J Holding) → España (propietario)

CADENA FISCAL SOBRE CUPONES ABANCA (EUR 49,000/año):
1. España → J Holding: retención 0% (Directiva Intereses EU, si beneficiario efectivo)
   O retención 19% si AEAT niega estatus de beneficiario efectivo
2. Portugal (J Holding): IRC 21% + derrama ~1.5% = ~22.5% = EUR 11,025
3. J Holding → Propietario ES: retención PT 15% (CDI PT-ES)
4. España (IRPF): 19-28% sobre dividendo recibido, con crédito por retención PT

ESCENARIO A — Estructura funciona como diseñada:
- Cupón bruto: EUR 49,000
- IRC Portugal: -EUR 11,025
- Retención PT→ES (15%): -EUR 5,696
- Neto pre-IRPF: EUR 32,279
- IRPF (con créditos): ~EUR 2,000-5,000 adicionales
- NETO FINAL AL PROPIETARIO: ~EUR 27,000-30,000
- TAX DRAG TOTAL: ~39-45%

ESCENARIO B — Inversión directa (sin J Holding):
- Cupón bruto: EUR 49,000
- Retención ES sobre intereses a residente: 19% = EUR 9,310 (a cuenta del IRPF)
- IRPF base del ahorro: 19-28% sobre EUR 49,000 = EUR 9,310-13,720
- NETO FINAL: EUR 35,280-39,690
- TAX DRAG: 19-28% (solo IRPF, retención a cuenta)

DIFERENCIAL DE LA ESTRUCTURA:
- Via J Holding: neto EUR 27,000-30,000 (tax drag 39-45%)
- Inversión directa: neto EUR 35,280-39,690 (tax drag 19-28%)
- PÉRDIDA ANUAL POR LA ESTRUCTURA: EUR 5,000-10,000/año

CIRCULARIDAD DEL FLUJO — Punto crítico AEAT:
- Los cupones SALEN de España (ABANCA) → van a Portugal (J Holding) → VUELVEN a España
- La AEAT puede argumentar: ¿por qué interponer una LDA portuguesa para cobrar cupones
  de un bono ESPAÑOL si el beneficiario final es un residente ESPAÑOL?
- Doctrina del "beneficiario efectivo": la LDA podría no ser considerada beneficiaria real
- Si AEAT aplica look-through: tributación como si inversión fuera directa + sanciones

RIESGOS:
- FLAG CFC: MEDIO-ALTO — 100% rentas pasivas en J Holding
- FLAG SUBSTANCE: ALTO — ¿J Holding tiene actividad real en Portugal?
- FLAG CIRCULARIDAD: ALTO — flujo España→Portugal→España sin razón económica clara
- FLAG BENEFICIAL OWNERSHIP: ALTO — AEAT puede negar estatus de beneficiario efectivo
- FLAG WITHHOLDING: MEDIO — retención 0% en cupones cuestionable si es conduit
- FLAG PE: BAJO — no hay establecimiento permanente
- FLAG DOBLE IMPOSICIÓN: ALTO — la estructura CREA sobre-imposición vs. inversión directa

RECOMENDACIÓN:
La estructura J Holding para mantener un bono ESPAÑOL genera un flujo circular
(ES→PT→ES) que incrementa el tax drag en 11-17 puntos porcentuales vs. tenencia directa.
Para los ETFs US, la estructura es irrelevante (montos inmateriales).
El riesgo principal no es fiscal sino de CONCENTRACIÓN (96.7% en ABANCA).
"""

# ── Dirección ─────────────────────────────────────────────────

STATIC_RESPONSES["investment_committee"] = """\
ACUERDOS ENTRE AGENTES:
- Consenso: ABANCA 6.125% es un bono fundamentalmente sólido (IG, yield atractivo)
- Consenso: la CONCENTRACIÓN del 96.7% en un solo emisor es el RIESGO DOMINANTE
- Consenso: ETFs US (ITA + XLF) son posiciones inmateriales (1.7%), sin impacto real
- Consenso: la estructura J Holding LDA para un bono español genera flujo circular (ES→PT→ES)
- Consenso: el tax drag de la estructura (39-45%) supera al de inversión directa (19-28%)
- Consenso: el costo operativo de J Holding (EUR 3K-5K/año) erosiona ~6-10% del income

CONTRADICCIONES:
- Fundamental dice bono sólido (convicción 0.70) vs. Credit dice posición inaceptable al 96.7%
- Cross-border identifica circularidad fiscal pero reconoce que IRC PT (21%) > umbral CFC (18.75%)
- Fiscal Spain señala que CFC podría NO aplicar si hay sustancia, pero Fiscal Portugal reconoce
  que la sustancia es cuestionable para una LDA de mera tenencia
- Risk Manager preocupado por concentración pero el bono tiene baja volatilidad individual

ESCENARIO BASE:
ABANCA paga cupones normalmente. Income EUR 49,000/año.
Via J Holding: neto ~EUR 27,000-30,000 al propietario (tax drag 39-45%).
Inversión directa: neto ~EUR 35,280-39,690 (tax drag 19-28%).
Pérdida anual por estructura: EUR 5,000-10,000.
Costo operativo LDA: EUR 3,000-5,000/año adicionales.
COSTO TOTAL DE LA ESTRUCTURA: EUR 8,000-15,000/año.

ESCENARIO OPTIMISTA:
ABANCA refinancia el bono a tasas más bajas → J Holding reinvierte en bonos diversificados.
Si J Holding diversifica en 5-10 emisores EU, la estructura podría justificarse como
vehículo de inversión real con sustancia. Tax drag se mantiene pero se mitiga riesgo single-name.

ESCENARIO ADVERSO:
ABANCA sufre evento de crédito (downgrade o default). Con 96.7% concentrado:
- Pérdida de mercado: EUR 125,000-495,000
- Margin call posible: cash insuficiente (EUR 12,409) para cubrir
- Liquidación forzada a precios de estrés
- Agravado por costos de la estructura PT que siguen corriendo

RIESGOS PRINCIPALES:
- Concentración 96.7% en ABANCA — riesgo existencial para el portfolio
- Flujo circular ES→PT→ES sin razón económica clara
- Tax drag excesivo vs. inversión directa (+11-17pp)
- Costo operativo de J Holding sin beneficio proporcional
- Margin account con colchón insuficiente
- Riesgo de que AEAT cuestione la estructura (beneficial ownership)

SÍNTESIS PARA EL CIO:
DOS PROBLEMAS INDEPENDIENTES:
1. CONCENTRACIÓN: el 96.7% en ABANCA es inaceptable — necesita diversificación urgente
2. ESTRUCTURA FISCAL: J Holding para un bono español genera sobrecosto sin beneficio claro

El comité recomienda:
(a) Mantener el bono ABANCA pero reducir a max 20-30% del portfolio
(b) Diversificar en 4-5 emisores adicionales (bonos IG EUR)
(c) Evaluar si J Holding tiene razón económica válida más allá del bono ABANCA
(d) Si J Holding no tiene sustancia real, considerar liquidar la estructura

CONDICIONES DE INVALIDACIÓN:
- ABANCA sufre downgrade a sub-IG → vender inmediatamente
- Margin call → liquidar posición forzada
- AEAT abre procedimiento de inspección sobre J Holding
- Cambio en Directiva Intereses/Cánones EU
"""

STATIC_RESPONSES["cio"] = """\
SÍNTESIS DEL CIO — J HOLDING GROUP LDA — PORTFOLIO PERSHING/MIURA

EVALUACIÓN INTEGRAL:
Portfolio de USD 1,015,250 con DOS problemas estructurales:
1. Concentración extrema (96.7%) en bono ABANCA 6.125%
2. Estructura fiscal subóptima (LDA portuguesa para bono español)

COMPOSICIÓN ACTUAL:
- ABANCA 6.125% (ES0865936035): EUR 825,280 — 96.7%
- iShares Aerospace & Defense (ITA): USD 9,295 — 0.9%
- Select Sector Financial SPDR (XLF): USD 8,550 — 0.8%
- Cash EUR: EUR 12,409 — 1.5%
- Cash USD: USD 973 — 0.1%

ANÁLISIS FISCAL — FLUJO CIRCULAR:
Cupones ABANCA: España → J Holding (Portugal) → Propietario (España)
Tax drag via J Holding: 39-45% + EUR 3K-5K/año de costos operativos
Tax drag inversión directa: 19-28%, sin costos de estructura
Sobrecoste anual de la estructura: EUR 8,000-15,000

ANÁLISIS DE RIESGO — CONCENTRACIÓN:
- 96.7% en un solo emisor bancario = riesgo existencial
- En default (probabilidad baja pero no cero): pérdida EUR 330K-495K
- Margin account con cash insuficiente: riesgo de liquidación forzada
- El income de EUR 49K/año NO compensa el tail risk de pérdida catastrófica

RIESGOS PRINCIPALES (ordenados por impacto):
1. Concentración 96.7% en ABANCA — riesgo de cola catastrófico
2. Margin account con buffer insuficiente (EUR 12K sobre EUR 825K)
3. Flujo circular ES→PT→ES incrementa tax drag sin beneficio
4. Costo operativo de la LDA (EUR 3-5K) sobre income de EUR 49K
5. Riesgo de cuestionamiento AEAT (beneficial ownership / CFC)
6. Riesgo de crédito ABANCA (bajo individualmente, alto por concentración)

DECISIÓN RECOMENDADA:
REESTRUCTURACIÓN EN DOS FASES:

FASE 1 — INMEDIATA (1-3 meses): Diversificar
- Reducir ABANCA al 25-30% del portfolio (~EUR 250K nominal)
- Reinvertir EUR 550K en 4-5 bonos IG EUR diversificados
- Mantener cash buffer de EUR 30-50K para margin
- Esto reduce el riesgo de cola de -60% a -15% máximo

FASE 2 — ESTRATÉGICA (3-6 meses): Evaluar estructura
- Si J Holding tiene sustancia real en Portugal (otras actividades, empleados):
  → Mantener la LDA, diversificar las posiciones dentro de ella
- Si J Holding es solo un vehículo de tenencia pasiva:
  → Evaluar liquidación de la LDA y tenencia directa
  → Ahorro estimado: EUR 8,000-15,000/año

PARA LOS ETFs US (ITA + XLF):
- Posiciones inmateriales (1.7%). Sin urgencia de acción.
- Si se liquida J Holding, transferir ETFs a cuenta personal en Pershing/Miura.

CONDICIONES DE INVALIDACIÓN:
- Downgrade de ABANCA a sub-IG → ejecutar venta inmediata
- Margin call → plan de contingencia necesario AHORA
- AEAT inspección → asesor fiscal especializado

RETORNO ESTIMADO (base case actual):
- Income bruto: EUR 49,000/año (cupón ABANCA)
- Neto al propietario (via J Holding): EUR 27,000-30,000/año
- Neto al propietario (inversión directa): EUR 35,280-39,690/año
"""

# ── Riesgo y Tax veto ─────────────────────────────────────────

STATIC_RESPONSES["risk_manager"] = """\
EVALUACIÓN DE RIESGO — J HOLDING GROUP LDA — PORTFOLIO PERSHING/MIURA

HALLAZGOS CLAVE:
- Portfolio total: USD 1,015,250 / EUR 837,689
- CONCENTRACIÓN CRÍTICA: ABANCA = 96.7% del portfolio
- Límite interno de single-name: 20% → EXCEDIDO en 76.7 puntos porcentuales
- Límite de sector (bancario): 35% → EXCEDIDO en 61.7 puntos porcentuales
- VaR 95% 1-día: EUR 12,500 (1.5%) — parece bajo pero subestima tail risk
- CVaR 95%: EUR 18,750 (2.2%)
- Max drawdown en evento de crédito ABANCA: EUR 330,000-495,000 (-40% a -60%)
- Margin account: posición ABANCA en margen con solo EUR 12,409 de cash buffer
- Ratio cash/posición: 1.5% — extremadamente bajo para portfolio apalancado

LÍMITES VIOLADOS:
- max_single_position_pct: 20% → ACTUAL: 96.7% — VIOLADO (+76.7pp)
- max_sector_pct: 35% → ACTUAL: 96.7% bancario — VIOLADO (+61.7pp)

ESCENARIO DE ESTRÉS:
- Downgrade ABANCA 2 notches: bono cae -8% a -12% → pérdida EUR 66K-99K
- Default ABANCA (recovery 45%): pérdida EUR 454K (54% del portfolio)
- Margin call threshold: si bono cae -5% (~EUR 41K) → probable margin call
- Cash insuficiente para cubrir: EUR 12,409 vs. potential margin call EUR 41K+

RECOMENDACIÓN:
EMITIR VETO por violación de límites de concentración.
La posición del 96.7% en un solo emisor bancario viola TODOS los parámetros
de riesgo del Family Office. El uso de margin account sin buffer adecuado
agrava el riesgo exponencialmente. Diversificación URGENTE requerida.
"""

STATIC_RESPONSES["head_tax_strategy"] = """\
NO_VETO — La estructura J Holding LDA es fiscalmente cuestionable pero no indefendible.

EVALUACIÓN FISCAL CONSOLIDADA:
1. CFC (Art. 100 LIS): RIESGO MEDIO-ALTO pero NO automático
   - IRC Portugal (21%) supera el umbral del 75% del tipo español (18.75%)
   - Esto significa que el test de tipo impositivo NO activa CFC automáticamente
   - PERO: la AEAT puede cuestionar bajo otros criterios (100% rentas pasivas)
   - Exención EU disponible si J Holding tiene "razones económicas válidas"

2. CIRCULARIDAD: RIESGO ALTO
   - Bono ESPAÑOL → LDA portuguesa → propietario ESPAÑOL
   - La AEAT puede aplicar look-through y negar beneficios de la estructura
   - PERO: no es ilegal per se, solo fiscalmente ineficiente

3. SUBSTANCE: CUESTIONABLE
   - Si J Holding tiene TOC, oficina registrada y cumple obligaciones PT → defensible
   - Si es solo un buzón → riesgo de reclasificación

4. TAX DRAG: La estructura DESTRUYE valor fiscal (+11-17pp vs. directo)
   - Esto NO es un veto sino una recomendación de optimización

CONCLUSIÓN:
No emito VETO porque la estructura no es "fiscalmente indefendible" — es legal
y funcional, solo es INEFICIENTE. El propietario tiene derecho a mantenerla.
Sin embargo, RECOMIENDO FUERTEMENTE evaluar si la LDA tiene razón económica
válida más allá de la tenencia del bono ABANCA. Si no la tiene, la liquidación
de la estructura ahorraría EUR 8,000-15,000/año.

CONDICIONES QUE ACTIVARÍAN VETO:
- Si J Holding se usa para adquirir activos adicionales SIN sustancia
- Si se interpone una segunda entidad (e.g., Panamá, Barbados) en la cadena
- Si se intenta aplicar treaty shopping con la estructura
"""

STATIC_RESPONSES["tax_risk_audit"] = """\
HALLAZGOS CLAVE:
- Riesgo de auditoría AEAT: MEDIO-ALTO
- J Holding Group LDA: entidad portuguesa con 100% rentas pasivas (cupones bono ES)
- El flujo circular (ES→PT→ES) es un patrón que la AEAT revisa activamente
- CRS: intercambio automático Portugal-España — AEAT ve la estructura completa
- Modelo 720: obligatorio declarar participación en J Holding (>EUR 50K)
- DAC6: la estructura podría ser reportable (hallmark D — circulación de fondos)
- Precedentes: la AEAT ha cuestionado holdings EU sin sustancia en múltiples casos

CUANTIFICACIÓN DEL RIESGO:
- Probabilidad de inspección (5 años): 15-25% (patrón de flujo circular + LDA EU)
- Si inspección:
  * Mejor caso: se aceptan declaraciones → costo de defensa EUR 5K-10K
  * Caso medio: reclasificación CFC → liquidación adicional + intereses
    EUR 49K × 28% IRPF = EUR 13,720/año × años abiertos (4) = EUR 54,880
    + intereses demora (3.75%/año) ≈ EUR 8,000
    Total: ~EUR 63,000
  * Peor caso: reclasificación + sanción (50-150%)
    EUR 54,880 + sanción EUR 27,440-82,320 = EUR 82,320-137,200

OBLIGACIONES DE REPORTE ACTUALES:
- Modelo 720 (activos extranjeros): participación en J Holding + saldos Pershing
- Modelo 232 (operaciones vinculadas): si hay transacciones J Holding ↔ propietario
- Declaración IRPF: dividendos recibidos de J Holding (si se distribuyen)
- Portugal: Modelo 22 IRC, IES, contabilidad organizada

RECOMENDACIÓN:
Riesgo de auditoría significativo por patrón circular. Asegurar que TODA la
documentación esté en orden: justificación económica de J Holding, Modelo 720
actualizado, declaraciones PT al día. Si J Holding no tiene sustancia documentada,
considerar asesoría preventiva de fiscalista español antes de que la AEAT actúe.
Provisión recomendada para contingencia fiscal: EUR 30,000-60,000.
"""


def _get_agent_role_from_prompt(system_prompt: str, user_prompt: str) -> str:
    """Identifica el agente a partir del campo 'Rol:' del system prompt."""
    import re
    match = re.search(r"Rol:\s*(\w+)", system_prompt)
    if match:
        role = match.group(1)
        if role in STATIC_RESPONSES:
            return role
    sp = system_prompt.lower()
    role_map = [
        ("rol: risk_manager", "risk_manager"),
        ("rol: head_tax_strategy", "head_tax_strategy"),
        ("rol: cio", "cio"),
        ("rol: investment_committee", "investment_committee"),
        ("rol: macro_geopolitics", "macro_geopolitics"),
        ("rol: fundamental", "fundamental"),
        ("rol: technical_quant", "technical_quant"),
        ("rol: credit_bonds", "credit_bonds"),
        ("rol: real_assets", "real_assets"),
        ("rol: fiscal_spain", "fiscal_spain"),
        ("rol: fiscal_portugal", "fiscal_portugal"),
        ("rol: fiscal_panama", "fiscal_panama"),
        ("rol: fiscal_barbados", "fiscal_barbados"),
        ("rol: fiscal_us", "fiscal_us"),
        ("rol: fiscal_venezuela", "fiscal_venezuela"),
        ("rol: cross_border", "cross_border"),
        ("rol: tax_risk_audit", "tax_risk_audit"),
        ("rol: opportunity_scanner", "opportunity_scanner"),
        ("rol: portfolio_ops", "portfolio_ops"),
    ]
    for keyword, role in role_map:
        if keyword in sp:
            return role
    if "veto" in user_prompt.lower() and "fiscal" in user_prompt.lower():
        return "head_tax_strategy"
    return "unknown"


async def mock_call_llm(system_prompt: str, user_prompt: str, **kwargs) -> str:
    role = _get_agent_role_from_prompt(system_prompt, user_prompt)
    response = STATIC_RESPONSES.get(role)
    if response:
        return response
    return f"[STATIC — {role}] Análisis no disponible en modo estático."


def serialize_result(result: dict) -> dict:
    output = {}
    proposal = result["proposal"]
    output["proposal"] = {
        "id": proposal.id,
        "title": proposal.title,
        "asset_class": proposal.asset_class,
        "description": proposal.description,
        "amount_usd": proposal.amount_usd,
        "expected_gross_return_pct": proposal.expected_gross_return_pct,
        "time_horizon_months": proposal.time_horizon_months,
        "jurisdiction": proposal.jurisdiction,
        "holding_vehicle": proposal.holding_vehicle,
        "status": proposal.status.value,
        "created_at": proposal.created_at.isoformat(),
        "updated_at": proposal.updated_at.isoformat(),
    }
    output["analyses"] = []
    for a in proposal.analyses:
        output["analyses"].append({
            "agent_role": a.agent_role.value,
            "subject": a.subject,
            "summary": a.summary[:500] if len(a.summary) > 500 else a.summary,
            "conviction_level": a.conviction_level,
            "key_findings": a.key_findings,
            "risks_identified": a.risks_identified,
            "recommendation": a.recommendation,
            "timestamp": a.timestamp.isoformat(),
        })
    output["portfolio_real"] = PORTFOLIO
    output["phases"] = result.get("phases", {})
    output["vetoes"] = []
    for v in result.get("vetoes", []):
        output["vetoes"].append({
            "agent_role": v.agent_role.value,
            "veto_type": v.veto_type.value,
            "justification": v.justification,
            "severity": v.severity,
            "conditions_to_lift": v.conditions_to_lift,
            "timestamp": v.timestamp.isoformat(),
        })
    veto_check = result.get("veto_check", {})
    output["veto_check"] = {
        "blocked": veto_check.get("blocked", False),
        "status": veto_check.get("status", DecisionStatus.PENDING).value
            if hasattr(veto_check.get("status", ""), "value")
            else str(veto_check.get("status", "")),
        "veto_summary": veto_check.get("veto_summary", ""),
        "can_override": veto_check.get("can_override", True),
    }
    cd = result.get("committee_decision")
    if cd:
        output["committee_decision"] = {
            "id": cd.id,
            "proposal_id": cd.proposal_id,
            "agreements": cd.agreements,
            "contradictions": cd.contradictions,
            "status": cd.status.value,
            "requires_user_approval": cd.requires_user_approval,
            "timestamp": cd.timestamp.isoformat(),
        }
        if cd.scenarios:
            output["committee_decision"]["scenarios"] = {
                "scenario_base": cd.scenarios.scenario_base,
                "scenario_optimistic": cd.scenarios.scenario_optimistic,
                "scenario_adverse": cd.scenarios.scenario_adverse,
                "main_risks": cd.scenarios.main_risks,
                "recommended_decision": cd.scenarios.recommended_decision,
                "invalidation_conditions": cd.scenarios.invalidation_conditions,
            }
    cio = result.get("cio_synthesis")
    if cio:
        output["cio_synthesis"] = {
            "id": cio.id,
            "proposal_id": cio.proposal_id,
            "cio_synthesis": cio.cio_synthesis,
            "final_recommendation": cio.final_recommendation,
            "status": cio.status.value,
        }
        if cio.scenarios:
            output["cio_synthesis"]["scenarios"] = {
                "scenario_base": cio.scenarios.scenario_base,
                "scenario_optimistic": cio.scenarios.scenario_optimistic,
                "scenario_adverse": cio.scenarios.scenario_adverse,
                "main_risks": cio.scenarios.main_risks,
                "recommended_decision": cio.scenarios.recommended_decision,
                "invalidation_conditions": cio.scenarios.invalidation_conditions,
            }
    output["validation"] = result.get("validation", {})
    status = result.get("status", DecisionStatus.PENDING)
    output["status"] = status.value if hasattr(status, "value") else str(status)
    output["ready_for_principal"] = result.get("ready_for_principal", False)

    # ═══════════════════════════════════════════════════════════
    # Flags cross-border consolidados — caso real J Holding
    # ═══════════════════════════════════════════════════════════
    output["cross_border_flags"] = {
        "cfc_risk": {
            "level": "MEDIO-ALTO",
            "detail": "Art. 100 LIS — IRC PT (21%) > umbral 75% tipo ES (18.75%), "
                      "por lo que test de tipo NO activa CFC automáticamente. "
                      "PERO: 100% rentas pasivas + posible falta de sustancia → "
                      "AEAT puede cuestionar bajo otros criterios.",
            "jurisdictions_affected": ["España (residencia)", "Portugal (J Holding)"],
        },
        "permanent_establishment_risk": {
            "level": "BAJO",
            "detail": "Tenencia pasiva de bonos y ETFs. Sin actividad que genere PE.",
            "jurisdictions_affected": [],
        },
        "substance_risk": {
            "level": "ALTO",
            "detail": "J Holding Group LDA — verificar: ¿tiene oficina real, TOC dedicado, "
                      "empleados, decisiones de inversión tomadas en Portugal? "
                      "Si es solo un vehículo de tenencia pasiva, sustancia insuficiente.",
            "jurisdictions_affected": ["Portugal"],
        },
        "withholding_tax_chain": {
            "level": "MEDIO",
            "detail": "Cupones ABANCA: 0% retención ES (Directiva Intereses EU, si beneficiario "
                      "efectivo) → 22.5% IRC PT → 15% distribución PT→ES (CDI) → 19-28% IRPF. "
                      "Tax drag total: 39-45% vs. 19-28% inversión directa.",
            "chain": [
                {"from": "ABANCA (España)", "to": "J Holding (Portugal)", "rate": "0%",
                 "note": "Directiva Intereses EU — requiere beneficiario efectivo"},
                {"from": "J Holding", "tax": "IRC Portugal", "rate": "22.5%",
                 "note": "21% IRC + 1.5% derrama municipal"},
                {"from": "J Holding (Portugal)", "to": "Propietario (España)", "rate": "15%",
                 "note": "CDI PT-ES sobre dividendos distribuidos"},
                {"from": "España", "tax": "IRPF", "rate": "19-28%",
                 "note": "Base del ahorro, con crédito por retención PT"},
            ],
        },
        "circular_flow_risk": {
            "level": "ALTO",
            "detail": "Flujo circular: cupones SALEN de España (ABANCA) → pasan por Portugal "
                      "(J Holding) → VUELVEN a España (propietario). La AEAT puede aplicar "
                      "look-through y negar beneficios de la estructura.",
        },
        "double_taxation_risk": {
            "level": "MEDIO",
            "detail": "CDIs España-Portugal y US-Portugal aplican. La estructura no genera "
                      "doble imposición jurídica pero sí sobre-imposición económica.",
            "treaties": ["CDI ES-PT", "CDI US-PT", "Directiva Intereses/Cánones EU"],
        },
        "concentration_risk": {
            "level": "CRÍTICO",
            "detail": "96.7% del portfolio en un solo emisor (ABANCA). Viola límites "
                      "de single-name (20%) y sector (35%). Riesgo catastrófico en default.",
        },
    }

    # HeadTaxStrategy detail
    output["head_tax_strategy_veto"] = {
        "veto_issued": any(
            v.get("agent_role") == "head_tax_strategy" for v in output["vetoes"]
        ),
        "severity": next(
            (v.get("severity") for v in output["vetoes"]
             if v.get("agent_role") == "head_tax_strategy"), None,
        ),
        "assessment": "Estructura legal pero fiscalmente ineficiente. No indefendible → NO VETO. "
                      "IRC PT (21%) supera umbral CFC (18.75%) evitando activación automática. "
                      "PERO: flujo circular ES→PT→ES y 100% rentas pasivas son factores de riesgo.",
        "recommendation": "Evaluar sustancia real de J Holding. Si no tiene actividad económica "
                          "en Portugal, considerar liquidación y tenencia directa. "
                          "Ahorro estimado: EUR 8,000-15,000/año.",
    }

    # Comparativa fiscal
    output["tax_comparison"] = {
        "via_j_holding": {
            "gross_income_eur": 49_000,
            "irc_portugal_22_5_pct": -11_025,
            "net_in_j_holding": 37_975,
            "withholding_pt_to_es_15_pct": -5_696,
            "pre_irpf": 32_279,
            "irpf_estimated": -4_000,
            "net_to_owner": 28_279,
            "lda_operating_costs": -4_000,
            "final_net": 24_279,
            "effective_tax_rate_pct": 50.5,
        },
        "direct_investment": {
            "gross_income_eur": 49_000,
            "irpf_19_28_pct": -11_515,
            "net_to_owner": 37_485,
            "operating_costs": 0,
            "final_net": 37_485,
            "effective_tax_rate_pct": 23.5,
        },
        "annual_cost_of_structure_eur": 13_206,
        "annual_cost_of_structure_pct": 27.0,
    }

    return output


async def main():
    print("=" * 72)
    print("  FAMILY OFFICE — ANÁLISIS CASO REAL")
    print("  J Holding Group LDA (Portugal) @ Pershing/Miura")
    print("  Propietario: Residente Fiscal España (100%)")
    print("  Portfolio: USD 1,015,250 — Enero 2026")
    print("=" * 72)
    print()

    import family_office.core.base_agent as _ba
    import family_office.core.llm_client as _ll
    _orig_ba, _orig_ll = _ba.call_llm, _ll.call_llm
    _ba.call_llm = mock_call_llm
    _ll.call_llm = mock_call_llm

    try:
        print("[1/7] Inicializando organización (20 agentes, 5 capas)...")
        orchestrator = FamilyOfficeOrchestrator()
        orchestrator.initialize()
        print(f"       {orchestrator.registry.agent_count} agentes registrados.\n")

        print("[2/7] Cargando portafolio real de J Holding Group LDA...")
        print(f"       Entidad: {PORTFOLIO['entity']}")
        print(f"       Jurisdicción: {PORTFOLIO['jurisdiction']}")
        print(f"       Custodio: {PORTFOLIO['custodian']}")
        print(f"       Broker: {PORTFOLIO['broker']}")
        print(f"       Total: USD {PORTFOLIO['total_value_usd']:,.2f}")
        print(f"       Income anual: USD {PORTFOLIO['estimated_annual_income_usd']:,.2f}")
        print()
        print("       POSICIONES:")
        for p in PORTFOLIO["positions"]:
            val = p.get("market_value_usd", p.get("market_value_eur", 0))
            pct = p.get("pct_portfolio", 0)
            print(f"         {p['name'][:50]:50s}  {pct:5.1f}%  ${val:>12,.2f}")
        print()

        proposal = InvestmentProposal(
            title="J Holding Group LDA — Portfolio Pershing/Miura Enero 2026",
            asset_class="Multi-asset (Renta Fija 96.7%, ETFs 1.7%, Cash 1.6%)",
            description=(
                "Análisis del portfolio existente de J Holding Group LDA (Portugal), "
                "100% propiedad de residente fiscal español. "
                "Cuenta en Pershing/Miura. Posición dominante: bono ABANCA 6.125% "
                "(ISIN ES0865936035) al 96.7% del portfolio. "
                "Posiciones menores: ETF ITA (Aerospace US), ETF XLF (Financial US). "
                "Flujo: ABANCA (España) → J Holding (Portugal) → Propietario (España). "
                "Income anual: EUR 49,000 (cupón) + USD 115 (dividendos ETFs)."
            ),
            amount_usd=1_015_250.12,
            expected_gross_return_pct=5.93,
            time_horizon_months=12,
            jurisdiction="España / Portugal / Estados Unidos",
            holding_vehicle="J Holding Group LDA (Portugal)",
        )

        print(f"[3/7] Propuesta creada: {proposal.id}")
        print("[4/7] Ejecutando pipeline de 7 fases...")
        print("       Fase 1+2: Análisis (5 agentes) + Fiscal (7 agentes) en paralelo")
        print("       Fase 3: Debate del Comité de Inversión")
        print("       Fase 4: Veto Gate (Risk Manager + Head of Tax Strategy)")
        print("       Fase 5: Síntesis del CIO")
        print("       Fase 6-7: Validación + Presentación")
        print()

        result = await orchestrator.process_proposal(proposal)

        decision_record = serialize_result(result)

        # ═══ JSON COMPLETO ═══
        print("=" * 72)
        print("  DECISION RECORD COMPLETO (JSON)")
        print("=" * 72)
        print(json.dumps(decision_record, indent=2, ensure_ascii=False, default=str))

        # ═══ REPORTE PRINCIPAL ═══
        print()
        print()
        report = orchestrator.pipeline.format_principal_report(result)
        print(report)

        # ═══ PIPELINE LOG ═══
        print()
        print("=" * 72)
        print("  PIPELINE LOG")
        print("=" * 72)
        for entry in orchestrator.pipeline.get_pipeline_log():
            print(f"  [{entry['phase']}] {entry['detail']}  — {entry['timestamp']}")

        # ═══ FLAGS CROSS-BORDER ═══
        print()
        print("=" * 72)
        print("  FLAGS CROSS-BORDER — J HOLDING GROUP LDA")
        print("=" * 72)
        flags = decision_record["cross_border_flags"]
        for flag_name, flag_data in flags.items():
            level = flag_data.get("level", "N/A")
            detail = flag_data.get("detail", "")
            print(f"  [{level:>12}] {flag_name}")
            # Wrap detail text
            words = detail.split()
            line = "                 "
            for w in words:
                if len(line) + len(w) > 90:
                    print(line)
                    line = "                 " + w
                else:
                    line += " " + w
            print(line)
            print()

        # ═══ COMPARATIVA FISCAL ═══
        print("=" * 72)
        print("  COMPARATIVA FISCAL — J HOLDING vs. INVERSIÓN DIRECTA")
        print("=" * 72)
        tc = decision_record["tax_comparison"]
        jh = tc["via_j_holding"]
        di = tc["direct_investment"]
        print(f"  {'':40s}  {'J Holding':>12s}  {'Directo':>12s}")
        print(f"  {'─'*40}  {'─'*12}  {'─'*12}")
        print(f"  {'Income bruto (cupón ABANCA)':40s}  EUR {jh['gross_income_eur']:>7,d}  EUR {di['gross_income_eur']:>7,d}")
        print(f"  {'IRC Portugal (22.5%)':40s}  EUR {jh['irc_portugal_22_5_pct']:>7,d}  {'—':>12s}")
        print(f"  {'Retención PT→ES (15% CDI)':40s}  EUR {jh['withholding_pt_to_es_15_pct']:>7,d}  {'—':>12s}")
        print(f"  {'IRPF España':40s}  EUR {jh['irpf_estimated']:>7,d}  EUR {di['irpf_19_28_pct']:>7,d}")
        print(f"  {'Costos operativos LDA':40s}  EUR {jh['lda_operating_costs']:>7,d}  EUR {di['operating_costs']:>7,d}")
        print(f"  {'─'*40}  {'─'*12}  {'─'*12}")
        print(f"  {'NETO AL PROPIETARIO':40s}  EUR {jh['final_net']:>7,d}  EUR {di['final_net']:>7,d}")
        print(f"  {'Tasa efectiva':40s}  {jh['effective_tax_rate_pct']:>10.1f}%  {di['effective_tax_rate_pct']:>10.1f}%")
        print(f"  {'':40s}")
        print(f"  COSTO ANUAL DE LA ESTRUCTURA: EUR {tc['annual_cost_of_structure_eur']:,d}/año ({tc['annual_cost_of_structure_pct']:.0f}% del income)")

        # ═══ HEAD TAX STRATEGY ═══
        print()
        print("=" * 72)
        print("  HEAD TAX STRATEGY — DECISIÓN DE VETO")
        print("=" * 72)
        htv = decision_record["head_tax_strategy_veto"]
        print(f"  Veto emitido: {'SÍ' if htv['veto_issued'] else 'NO'}")
        if htv["severity"]:
            print(f"  Severidad: {htv['severity']}")
        print(f"  Evaluación: {htv['assessment'][:200]}")
        print(f"  Recomendación: {htv['recommendation'][:200]}")

        # ═══ STATUS FINAL ═══
        print()
        print("=" * 72)
        st = decision_record['status'].upper()
        print(f"  STATUS FINAL DEL PIPELINE: {st}")
        print("=" * 72)

        # ═══ DECISION STORE ═══
        print()
        stored = orchestrator.decision_store.get_decision(proposal.id)
        if stored:
            print("  [Decisión persistida en disco]")

    finally:
        _ba.call_llm = _orig_ba
        _ll.call_llm = _orig_ll


if __name__ == "__main__":
    asyncio.run(main())
