#!/usr/bin/env python3
"""
Ejecución estática del pipeline — Caso Cross-Border con Holding Portugal LDA.

Caso: Residente fiscal España, inversión en activo US con dividendos,
      vía holding Portugal LDA, monto USD 500K, horizonte largo.

Objetivo: Mostrar DecisionRecord completo con:
- Hallazgos por jurisdicción
- Flags CFC/PE/substance/withholding/doble imposición
- HeadTaxStrategy veto (severidad y motivo)
- Status final del pipeline

Uso:
    python run_cross_border_case.py
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
)
from family_office.orchestrator import FamilyOfficeOrchestrator

# ═════════════════════════════════════════════════════════════════
# Respuestas estáticas por agente — CASO PORTUGAL LDA
# Cada agente tiene una respuesta realista adaptada a la estructura:
#   US (fuente dividendos) → Portugal LDA (holding) → España (residencia)
# ═════════════════════════════════════════════════════════════════

STATIC_RESPONSES: dict[str, str] = {}

# ── Capa 2: Análisis ──────────────────────────────────────────

STATIC_RESPONSES["macro_geopolitics"] = """\
HALLAZGOS CLAVE:
- Ciclo de tasas de la Fed en fase de pausa; el mercado descuenta 2 recortes en 2026
- GDP US creciendo al 2.1% anualizado, por encima de tendencia
- Europa: BCE con política monetaria divergente, tasas en descenso gradual
- Portugal: economía estable, crecimiento del 1.8%, marco regulatorio EU predecible
- España: PIB +2.3%, presión fiscal creciente sobre rentas del capital (IRPF ahorro)
- Riesgo geopolítico moderado: tensiones comerciales US-China contenidas
- Empleo US robusto (unemployment 3.9%) soporta earnings corporativos

RIESGOS:
- Inflación persistente por encima del 2.5% podría retrasar recortes de la Fed
- Cambios regulatorios EU en materia de transparencia fiscal (DAC8 en discusión)
- España: potencial incremento del tipo de ahorro IRPF en próxima reforma fiscal
- Escrutinio creciente de la AEAT sobre estructuras con sociedades interpuestas en EU

RECOMENDACIÓN:
Entorno macro favorable para equity US large cap. Sin embargo, el uso de holding
Portugal LDA introduce complejidad regulatoria innecesaria dado el escrutinio EU
sobre estructuras instrumentales. Convicción 0.68 sobre el activo subyacente,
pero 0.35 sobre la estructura propuesta.
"""

STATIC_RESPONSES["fundamental"] = """\
HALLAZGOS CLAVE:
- S&P 500 cotiza a P/E forward de 21.3x, ligeramente por encima de la media histórica (19.5x)
- Dividend yield del S&P 500: 1.45%, USD 7,250/año sobre USD 500K
- Earnings growth estimado para 2026: +9.2% YoY
- Free cash flow yield del S&P 500: 4.2%, superior al Treasury 10Y real
- Para una posición de dividendos, considerar high-dividend ETFs (SCHD, VYM) con yield 3.2-3.5%
- Con yield del 3.5%: dividendos anuales estimados USD 17,500 sobre USD 500K

RIESGOS:
- Valuación estirada vs. histórico; mean reversion implicaría -8% a -12%
- Concentración en Mag-7 (32% del índice) si se usa SPY
- Con holding Portugal LDA, el tax drag sobre dividendos aumenta significativamente
- Doble retención: 15% US (CDI US-PT) + posible tributación PT + IRPF España

RECOMENDACIÓN:
Fundamentales del activo US sólidos. PERO: la estructura via Portugal LDA
introduce una capa fiscal adicional que reduce el retorno neto de dividendos.
Para una estrategia de dividendos, cada punto porcentual de tax drag es crítico.
Entrada gradual (DCA 3 meses). Convicción 0.62 sobre activo, 0.30 sobre estructura.
"""

STATIC_RESPONSES["technical_quant"] = """\
HALLAZGOS CLAVE:
- S&P 500 en tendencia alcista: precio sobre SMA 200 y SMA 50
- RSI(14) en 58, zona neutral-alcista, sin sobrecompra
- Volatilidad implícita (VIX) en 16.2, por debajo de media histórica (19.5)
- Momentum factor: +2.1% mensual, positivo y acelerando
- Breadth: 68% de componentes sobre SMA 200, saludable

RIESGOS:
- Soporte clave en 5,150 (SMA 200); ruptura implicaría corrección -7% a -10%
- Estacionalidad: H2 2026 históricamente más débil que H1
- Para horizonte largo (10 años), el timing de entrada es menos crítico

RECOMENDACIÓN:
Señales técnicas alineadas al alza. Entry point razonable para horizonte largo.
La estructura societaria (Portugal LDA) no afecta el análisis técnico del activo
subyacente. Target 12 meses: +11.5%. Target 10 años (CAGR): 8-10%. Convicción 0.70.
"""

STATIC_RESPONSES["credit_bonds"] = """\
HALLAZGOS CLAVE:
- Treasury 10Y en 4.15%, curva de rendimiento normalizada
- Equity risk premium (ERP): 4.9%, favorece equities sobre bonos en horizonte largo
- Para horizonte de 10 años, equity históricamente supera a renta fija en >85% de periodos
- Dividend yield (3.5% high-div) + capital appreciation > bond yields ajustados por inflación
- EUR/USD estable; riesgo cambiario moderado para residente zona euro

RIESGOS:
- Spreads comprimidos dejan poco margen de compresión adicional
- Si la Fed no recorta, renta fija compite más agresivamente con equity
- Riesgo divisa EUR/USD en horizonte 10 años: volatilidad estimada 8-12% anual

RECOMENDACIÓN:
El ERP favorece equity sobre bonos en horizonte largo. La posición debería
complementarse con un 15-20% en Treasuries como hedge. Para horizonte 10 años,
la estructura de holding es secundaria vs. la selección de activos. Convicción 0.60.
"""

STATIC_RESPONSES["real_assets"] = """\
HALLAZGOS CLAVE:
- REITs US cotizan a descuento del 12% vs. NAV, alternativa para income
- Infraestructura: yields del 5.2-5.8%, competitivos vs. dividend equity
- Para estrategia de dividendos via holding, REITs US tienen withholding del 30% (sin CDI favorable)
- Oro y commodities no generan dividendos; irrelevantes para este caso

RIESGOS:
- REITs sensibles a tasas; mayor volatilidad que equity diversificado
- Withholding tax sobre REITs US típicamente más alto que sobre equity ordinario

RECOMENDACIÓN:
Para este caso específico (dividendos US via Portugal LDA), no agregar REITs.
El withholding tax sobre REITs US sería del 30% incluso con CDI, reduciendo
aún más el retorno neto. Mantener enfoque en equity large cap. Convicción 0.55.
"""

# ── Capa 3: Fiscal ────────────────────────────────────────────

STATIC_RESPONSES["fiscal_spain"] = """\
HALLAZGOS CLAVE:
- Residencia fiscal: España. Tributación sobre renta mundial (IRPF)
- Si dividendos fluyen via Portugal LDA → España: doble capa impositiva
- IRPF sobre dividendos recibidos de la LDA portuguesa: 19-28% (base del ahorro)
- Art. 100 LIS — Régimen de transparencia fiscal internacional (CFC):
  * La Portugal LDA se consideraría entidad interpuesta si:
    (a) >50% de sus rentas son pasivas (dividendos US = 100% pasivas)
    (b) Tributa en Portugal a <75% del tipo español equivalente
    (c) No tiene sustancia económica real (oficina, empleados, decisiones locales)
  * Si CFC aplica: la renta se IMPUTA directamente al residente español
  * Resultado: se tributa como si no existiera la LDA → pierde toda ventaja
- Modelo 720: obligación de declarar la participación en la LDA (>EUR 50K en extranjero)
- Impuesto sobre el Patrimonio: aplica sobre participación en LDA + activos subyacentes

RIESGOS:
- FLAG CFC: ALTO — Art. 100 LIS aplicaría casi con certeza (100% rentas pasivas en LDA)
- FLAG SUBSTANCE: ALTO — LDA sin oficina/empleados/actividad real en Portugal
- FLAG DOBLE IMPOSICIÓN: MEDIO — CDI España-Portugal existe pero no elimina CFC
- Modelo 720: sanción proporcional por no declarar participación en LDA
- Riesgo de inspección AEAT: ELEVADO para estructuras con holdings EU sin sustancia

RECOMENDACIÓN:
ESTRUCTURA NO RECOMENDADA. El régimen CFC español (Art. 100 LIS) anularía
cualquier beneficio fiscal de interponer la Portugal LDA. La renta se imputaría
directamente al IRPF del residente español. Tax drag estimado con LDA: 28-35%
efectivo (peor que inversión directa al 23.5%). Además, costos de mantenimiento
de la LDA (contabilidad, registered agent, declaraciones PT) ~EUR 5,000-8,000/año.
"""

STATIC_RESPONSES["fiscal_portugal"] = """\
HALLAZGOS CLAVE:
- Portugal LDA (Sociedade por Quotas): tipo IRC del 21% sobre beneficios
- Dividendos recibidos de US por la LDA: tributarían al 21% en Portugal
- CDI Portugal-US: retención en origen US reducida al 15% sobre dividendos
- Participation exemption en PT: aplica si la LDA posee >10% del capital de la empresa US
  * Para ETFs/acciones diversificadas: NO aplica (participación <10%)
  * Sin participation exemption: dividendos US tributan al 21% IRC en PT
- Distribución de dividendos de la LDA a socio español:
  * Retención PT sobre dividendos a no-residentes: 25% (sin CDI) o 15% (CDI PT-ES)
  * CDI Portugal-España: retención reducida al 15% sobre dividendos
- NHR (Non-Habitual Resident): NO aplica — el Principal es residente fiscal en España

RIESGOS:
- FLAG WITHHOLDING: ALTO — Cadena de retenciones: 15% US + 21% IRC PT + 15% distribución PT→ES
- FLAG SUBSTANCE: ALTO — AEAT exigirá prueba de sustancia real de la LDA
- FLAG PE: BAJO — No hay riesgo de establecimiento permanente en PT por mera titularidad
- Costo operativo anual de la LDA: EUR 5,000-8,000 (contabilidad, TOC, declaraciones)
- Beneficio fiscal: NEGATIVO — la estructura INCREMENTA el tax drag total

RECOMENDACIÓN:
La Portugal LDA NO genera eficiencia fiscal para este caso. Sin participation exemption
(porque invierte en ETFs, no en participaciones >10%), los dividendos US tributan:
  15% (retención US) → 21% IRC PT → 15% (distribución PT→ES) → 19-28% IRPF ES
Tasa efectiva acumulada: ~45-52% sobre dividendos brutos.
Comparado con inversión directa: 15% retención US + 19-28% IRPF ES = ~31-38%.
LA ESTRUCTURA DESTRUYE VALOR.
"""

STATIC_RESPONSES["fiscal_panama"] = """\
HALLAZGOS CLAVE:
- Panamá: sistema territorial, no grava rentas de fuente extranjera
- No es relevante para este caso — la estructura propuesta usa Portugal LDA, no Panamá
- Si se considerara Panamá como alternativa: CFC español también aplicaría
- Panamá + Portugal LDA: estructura multi-capa aumentaría escrutinio de AEAT

RIESGOS:
- CFC español imputaría la renta al residente en España independientemente
- Agregar jurisdicciones adicionales incrementa complejidad y costo sin beneficio

RECOMENDACIÓN:
No involucrar a Panamá en esta operación. La jurisdicción no aporta valor fiscal
y aumentaría el riesgo reputacional y de escrutinio regulatorio.
"""

STATIC_RESPONSES["fiscal_barbados"] = """\
HALLAZGOS CLAVE:
- Barbados IBC: no relevante para la estructura propuesta (Portugal LDA)
- Sin CDI Barbados-España: no habría protección contra doble imposición
- Agregar Barbados como capa adicional empeoraría significativamente la posición

RIESGOS:
- Alto riesgo CFC desde España para cualquier estructura caribeña
- Barbados en lista de vigilancia OCDE

RECOMENDACIÓN:
Descartado. No involucrar jurisdicciones offshore adicionales a la estructura.
"""

STATIC_RESPONSES["fiscal_us"] = """\
HALLAZGOS CLAVE:
- Activo subyacente: equity US large cap / ETF de dividendos en mercado US
- Si el titular es la Portugal LDA (no persona física):
  * CDI US-Portugal aplica: retención sobre dividendos reducida al 15%
  * Pero: IRS exige Form W-8BEN-E con certificado de residencia fiscal PT de la LDA
  * Si la LDA es "conduit" sin sustancia, IRS puede negar beneficios del CDI (LOB clause)
- Si inversión directa por persona física (residente España):
  * CDI US-España aplica: retención 15% sobre dividendos
  * Form W-8BEN (persona física) — más simple
- FATCA: reporte automático en ambos casos
- Estate tax US: aplica a NRA con activos US situs >USD 60K
  * Si titular es LDA portuguesa: estate tax NO aplica (entidad, no persona)
  * PERO: esta ventaja se pierde si CFC español "mira a través" de la LDA

RIESGOS:
- FLAG WITHHOLDING: 15% retención US sobre dividendos (igual con o sin LDA)
- FLAG PE: NULO — inversión pasiva, sin PE en US
- LOB clause: riesgo bajo pero existente si IRS cuestiona sustancia de la LDA
- Estate tax: eliminado via LDA, pero ventaja marginal vs. costo total de la estructura

RECOMENDACIÓN:
Retención US idéntica (15%) con o sin Portugal LDA. La única ventaja US de la LDA
sería protección contra estate tax, pero su costo y riesgo CFC lo anulan.
Tax drag US: 15% sobre dividendos (USD 2,625/año sobre yield del 3.5% de USD 500K).
"""

STATIC_RESPONSES["fiscal_venezuela"] = """\
HALLAZGOS CLAVE:
- ISLR Venezuela: aplica a residentes fiscales sobre renta mundial
- El Principal es residente fiscal en ESPAÑA, no en Venezuela
- Si no existe residencia fiscal dual (ES+VE), sin impacto desde Venezuela
- Control cambiario VE: no aplica para inversiones offshore de no-residentes
- Portugal LDA: sin nexo con Venezuela, sin reportería VE requerida

RIESGOS:
- Si el Principal mantiene residencia fiscal dual (ES+VE): doble tributación posible
- Verificar estatus de residencia fiscal VE formalmente

RECOMENDACIÓN:
Sin impacto fiscal desde Venezuela para residente fiscal español.
Confirmar que no existe residencia fiscal dual vigente.
"""

STATIC_RESPONSES["cross_border"] = """\
HALLAZGOS CLAVE:
- Flujo propuesto: US (fuente dividendos) → Portugal LDA (holding) → España (residencia)
- Cadena de retenciones/impuestos sobre dividendos:
  1. US → PT LDA: 15% retención (CDI US-PT) sobre dividendo bruto
  2. PT LDA: 21% IRC sobre dividendo neto recibido (sin participation exemption)
  3. PT → España: 15% retención (CDI PT-ES) sobre distribución de la LDA
  4. España: 19-28% IRPF sobre dividendo recibido, con crédito por retención PT
- Tasa efectiva acumulada sobre dividendos: 45-52% (vs. 31-38% inversión directa)
- Transfer pricing: no aplicable directamente, pero AEAT puede cuestionar la razón económica
- DAC6: REPORTABLE — esquema con sociedad interpuesta EU para recibir rentas pasivas
- CRS: reporte automático entre PT, ES y US — no hay opacidad

RIESGOS:
- FLAG CFC: CRÍTICO — Art. 100 LIS aplicaría. La LDA tiene 100% rentas pasivas
- FLAG SUBSTANCE: CRÍTICO — LDA sin empleados, oficina ni actividad real en PT
- FLAG WITHHOLDING: ALTO — Triple capa de imposición sobre dividendos
- FLAG DOBLE IMPOSICIÓN: ALTO — Aunque existen CDIs, la estructura crea sobre-imposición
- FLAG PE: BAJO — Sin establecimiento permanente en ninguna jurisdicción
- FLAG DAC6: MEDIO — Esquema potencialmente reportable bajo Directiva DAC6

RECOMENDACIÓN:
LA ESTRUCTURA VIA PORTUGAL LDA ES FISCALMENTE INEFICIENTE Y POTENCIALMENTE AGRESIVA.
- Destruye entre 7-14 puntos porcentuales de retorno neto vs. inversión directa
- Genera obligación DAC6 de reporte
- Alta probabilidad de CFC español (Art. 100 LIS)
- Costo operativo de la LDA: EUR 5,000-8,000/año sin beneficio fiscal
- RECOMENDACIÓN: inversión directa US → España con CDI bilateral
- Retorno neto post-impuestos inversión directa: ~7.2% (base case sobre 10% bruto)
- Retorno neto post-impuestos via PT LDA: ~4.8-5.5% (misma base)
- DIFERENCIAL NEGATIVO DE LA ESTRUCTURA: -1.7 a -2.4 puntos porcentuales/año
"""

# ── Dirección ─────────────────────────────────────────────────

STATIC_RESPONSES["investment_committee"] = """\
ACUERDOS ENTRE AGENTES:
- Consenso: entorno macro favorable para equity US en horizonte largo
- Consenso: fundamentales sólidos, earnings growth positivo para 10 años
- Consenso: señales técnicas alineadas al alza para entrada
- Consenso UNÁNIME: la estructura via Portugal LDA DESTRUYE VALOR fiscal
- Consenso: inversión directa US→España es superior en todos los escenarios
- Consenso: el CDI US-España es suficiente para la optimización fiscal posible
- Consenso: CFC español (Art. 100 LIS) aplicaría con alta probabilidad a la LDA

CONTRADICCIONES:
- Fundamental vs. estructura: activo atractivo, vehículo inapropiado
- Fiscal US: estate tax se elimina con LDA, pero costo > beneficio
- Macro: estabilidad PT es positiva, pero no justifica holding sin sustancia

ESCENARIO BASE (con Portugal LDA):
Retorno bruto equity US +10%. Dividendo bruto 3.5% (USD 17,500/año).
Tax drag acumulado via LDA: 45-52%. Retorno neto dividendos: ~1.7-1.9%.
Plus capital appreciation ~6.5% neto post-IRPF España.
Retorno total neto via LDA: ~4.8-5.5%. Costo LDA: EUR 5K-8K/año.
INFERIOR a inversión directa en ~1.7-2.4pp/año.

ESCENARIO BASE (inversión directa — alternativa recomendada):
Retorno bruto +10%. Tax drag: 31-38%. Retorno neto: ~6.2-7.2%.
Sin costos de estructura. Sin riesgo CFC. Sin DAC6.

ESCENARIO OPTIMISTA:
Fed recorta, múltiplo expande. Retorno bruto +16%.
Via LDA: neto ~7.5%. Directo: neto ~12.2%. Gap se amplía.

ESCENARIO ADVERSO:
Inflación persistente, corrección equity -12%.
Via LDA: pérdida amplificada por costos fijos de la estructura.
Directo: pérdida sin carga estructural adicional.

RIESGOS PRINCIPALES:
- CFC español (Art. 100 LIS): imputación directa, pierde toda ventaja
- Tax drag excesivo: 45-52% vs. 31-38% directo
- Costo operativo LDA: EUR 5K-8K/año sin retorno fiscal
- DAC6: obligación de reporte como esquema potencialmente agresivo
- Riesgo reputacional: escrutinio AEAT por estructura interpuesta
- Estate tax US: único beneficio marginal, no justifica la estructura

SÍNTESIS PARA EL CIO:
EL ACTIVO ES BUENO. LA ESTRUCTURA ES MALA.
El comité recomienda APROBAR la inversión en equity US large cap / dividendos,
pero RECHAZAR el vehículo Portugal LDA. Inversión directa superior en todos
los escenarios analizados. HeadTaxStrategy debería emitir veto sobre la estructura.

CONDICIONES DE INVALIDACIÓN:
- Cambio en Art. 100 LIS que excluya holdings EU (improbable)
- Portugal introduzca participation exemption para ETFs (no existe)
- España elimine tributación sobre dividendos extranjeros (no previsto)
- La LDA adquiera sustancia real con actividad económica (no justificado para USD 500K)
"""

STATIC_RESPONSES["cio"] = """\
SÍNTESIS DEL CIO — INVERSIÓN EN ACTIVO US DIVIDENDOS VIA PORTUGAL LDA

EVALUACIÓN INTEGRAL:
El activo subyacente (equity US large cap / ETF dividendos) es fundamentalmente
sólido para horizonte largo. Sin embargo, la estructura propuesta via Portugal LDA
genera destrucción de valor fiscal significativa.

ESCENARIO BASE (via Portugal LDA — NO RECOMENDADO):
Inversión: USD 500,000 en equity US con dividend yield ~3.5%.
Dividendos brutos: USD 17,500/año.
Cadena fiscal: 15% US + 21% IRC PT + 15% CDI PT-ES + 19-28% IRPF.
Tax drag acumulado: 45-52%. Dividendos netos: USD 8,400-9,625/año.
Capital appreciation: 6.5% bruto → ~5.0% neto.
Retorno total neto: ~4.8-5.5%. Costo LDA: EUR 5K-8K/año (~USD 5.4K-8.6K).
Retorno real post-costos: ~3.7-4.5%.

ESCENARIO BASE (inversión directa US → España — RECOMENDADO):
Dividendos brutos: USD 17,500/año.
Cadena fiscal: 15% US + 19-28% IRPF ES (con crédito fiscal por retención US).
Tax drag: 31-38%. Dividendos netos: USD 10,850-12,075/año.
Capital appreciation: 6.5% bruto → ~5.0% neto.
Retorno total neto: ~6.2-7.2%. Sin costos de estructura.

DIFERENCIAL: La Portugal LDA DESTRUYE entre USD 8,500-13,500/año de valor
(~1.7-2.7% sobre USD 500K) comparado con inversión directa.

RIESGOS PRINCIPALES:
1. CFC español (Art. 100 LIS): anula toda ventaja fiscal de la LDA
2. Tax drag excesivo: cadena de retenciones/impuestos en 4 capas
3. Costo operativo sin retorno: EUR 5K-8K/año manteniendo la LDA
4. DAC6: obligación de reportar esquema como potencialmente agresivo
5. Escrutinio AEAT: alto riesgo de inspección por estructura interpuesta
6. Valuación equity US estirada (P/E 21.3x vs. media 19.5x)

NOTA SOBRE VETO:
HeadTaxStrategy ha emitido VETO sobre la estructura Portugal LDA por:
- Riesgo CFC crítico (Art. 100 LIS, 100% rentas pasivas)
- Falta de sustancia económica de la LDA
- Estructura no defendible ante inspección AEAT
El veto NO aplica al activo subyacente, solo al vehículo.

DECISIÓN RECOMENDADA:
RECHAZAR la estructura via Portugal LDA.
APROBAR la inversión en equity US large cap / dividendos via cuenta directa.

PLAN DE EJECUCIÓN (alternativa directa):
1. Abrir cuenta en broker US regulado (Interactive Brokers, Schwab) a nombre personal
2. Completar Form W-8BEN para retención reducida al 15% (CDI US-ES)
3. Entrada gradual DCA en 3-4 tranches mensuales de USD 125K-166K
4. ETFs recomendados: SCHD (dividendos), RSP (equal-weight), o combinación
5. Declarar en Modelo 720 (activos >EUR 50K en extranjero)
6. Incluir dividendos y ganancias en IRPF con crédito fiscal por retención US
7. Revisión semestral o si VIX > 25

CONDICIONES DE INVALIDACIÓN:
- Recesión US confirmada (2Q GDP negativo)
- Reforma fiscal española que penalice inversión extranjera directa
- Tipo de cambio EUR/USD > 1.25 (reduce retorno en EUR)
- VIX sostenido sobre 30 por 2+ semanas

RETORNO NETO POST-IMPUESTOS (inversión directa): 6.2-7.2% estimado (base case).
RETORNO NETO POST-IMPUESTOS (via Portugal LDA): 3.7-4.5% (inferior en todo escenario).
"""

# ── Riesgo y Tax veto ─────────────────────────────────────────

STATIC_RESPONSES["risk_manager"] = """\
EVALUACIÓN DE RIESGO — EQUITY US VIA PORTUGAL LDA — USD 500K

HALLAZGOS CLAVE:
- Posición USD 500K en equity US: riesgo de mercado estándar para large cap
- VaR 95% 1-día estimado: USD 15,800 (3.16% — basado en vol histórica 20%)
- CVaR 95%: USD 22,500 (tail risk)
- Max drawdown histórico S&P 500 12m: -33.9% (COVID), -38.5% (2008)
- Liquidez: excelente (ETFs US, bid-ask <1bp)
- Horizonte largo (10 años) reduce significativamente probabilidad de pérdida
- Riesgo operativo: la Portugal LDA añade complejidad operativa pero no riesgo de mercado
- Riesgo regulatorio: posible reclasificación fiscal si AEAT aplica CFC

RIESGOS:
- Drawdown máximo esperado en escenario adverso: USD 60,000-75,000 (-12% a -15%)
- Riesgo divisa EUR/USD en horizonte 10 años (volatilidad 8-12% anual)
- Riesgo de estructura: costos fijos de la LDA erosionan retorno en escenario adverso
- Sin cobertura cambiaria, el retorno en EUR tiene varianza adicional

RECOMENDACIÓN:
NO EMITIR VETO desde perspectiva de riesgo de mercado. La posición tiene
liquidez excelente y el horizonte largo mitiga la volatilidad a corto plazo.
El riesgo primario NO es de mercado sino FISCAL/ESTRUCTURAL (fuera de mi ámbito).
Condiciones: implementar stop-loss a nivel portfolio si drawdown > 15%.
Nota: el riesgo de la estructura PT LDA es competencia de HeadTaxStrategy.
"""

# HeadTaxStrategy — EMITE VETO sobre la estructura Portugal LDA
STATIC_RESPONSES["head_tax_strategy"] = """\
VETO — Estructura via Portugal LDA fiscalmente indefendible.

JUSTIFICACIÓN DEL VETO:
1. CFC CRÍTICO (Art. 100 LIS España): La Portugal LDA tendría 100% de rentas
   pasivas (dividendos US). Esto activa automáticamente el régimen de transparencia
   fiscal internacional español. La renta se IMPUTA al IRPF del residente español
   como si la LDA no existiera. Resultado: CERO beneficio fiscal.

2. FALTA DE SUSTANCIA: La LDA no tendría oficina real, empleados, ni proceso
   de toma de decisiones en Portugal. No cumple los requisitos mínimos de
   sustancia económica bajo criterios OCDE/EU.

3. ESTRUCTURA NO DEFENDIBLE: Ante una inspección de la AEAT, esta estructura
   sería clasificada como planificación fiscal agresiva. El Principal quedaría
   expuesto a:
   - Liquidación por CFC con intereses de demora
   - Sanción del 50-150% de la cuota no ingresada
   - Obligación DAC6 de reportar el esquema

4. DESTRUCCIÓN DE VALOR: Tax drag via LDA (45-52%) SUPERIOR a inversión
   directa (31-38%). La estructura NO genera ahorro fiscal, lo INCREMENTA.

5. COSTO SIN BENEFICIO: EUR 5,000-8,000/año de mantenimiento de la LDA
   para un resultado fiscal PEOR que la alternativa directa.

SEVERIDAD DEL VETO: 0.9 (alto — estructura fiscalmente inaceptable)
TIPO: Riesgo fiscal CFC + estructura indefendible

CONDICIONES PARA LEVANTAR EL VETO:
- Eliminar la Portugal LDA de la estructura y usar inversión directa
- O demostrar sustancia económica REAL de la LDA (oficina, empleados,
  actividad comercial no-pasiva >50% de ingresos) — no viable para USD 500K
- O que España modifique el Art. 100 LIS (legislativamente improbable)

ALTERNATIVA RECOMENDADA:
Inversión directa: Cuenta personal en broker US → CDI US-ES al 15% → IRPF ahorro.
Esta estructura es 100% defendible, más eficiente fiscalmente, y sin costos fijos.
"""

STATIC_RESPONSES["tax_risk_audit"] = """\
HALLAZGOS CLAVE:
- Riesgo de auditoría: ALTO para estructura con Portugal LDA sin sustancia
- La AEAT ha intensificado inspecciones de holdings EU instrumentales desde 2023
- Modelo 720: obligación de declarar participación en LDA portuguesa (>EUR 50K)
- DAC6: esquema REPORTABLE — sociedad interpuesta EU para rentas pasivas de fuente US
- CRS/FATCA: intercambio automático de información entre US, PT, ES
  * No existe opacidad: la AEAT verá la estructura completa
- Art. 100 LIS (CFC): inspectores de la AEAT aplican esta norma de oficio
- Precedentes jurisprudenciales: múltiples sentencias contra holdings EU sin sustancia

RIESGOS:
- Liquidación CFC: impuesto adeudado + intereses de demora (3.75% anual)
- Sanción tributaria: 50-150% de la cuota no ingresada
- Modelo 720: sanción proporcional por defecto de declaración
- Riesgo reputacional: clasificación como "planificación fiscal agresiva"
- Costo de defensa: EUR 15K-30K en caso de procedimiento inspector

RECOMENDACIÓN:
ESTRUCTURA DE ALTO RIESGO TRIBUTARIO. La inversión directa elimina todos
estos riesgos. Si el Principal insiste en la Portugal LDA, se requiere:
1. Opinión legal escrita de fiscalista español especializado en CFC
2. Opinión legal de fiscalista portugués sobre substance
3. Análisis de riesgo cuantificado antes de proceder
4. Provisión para contingencia fiscal de EUR 25,000-50,000
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
    """Reemplaza call_llm con respuestas estáticas realistas para el caso PT LDA."""
    role = _get_agent_role_from_prompt(system_prompt, user_prompt)
    response = STATIC_RESPONSES.get(role)
    if response:
        return response
    return f"[STATIC — {role}] Análisis no disponible en modo estático."


def serialize_result(result: dict) -> dict:
    """Serializa el resultado del pipeline a JSON-safe dict."""
    output = {}

    # Proposal
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

    # Analyses
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

    # Fiscal impacts (from proposal)
    output["fiscal_impacts"] = []
    for f in proposal.fiscal_impacts:
        output["fiscal_impacts"].append({
            "jurisdiction": f.jurisdiction,
            "gross_return_pct": f.gross_return_pct,
            "tax_rate_effective": f.tax_rate_effective,
            "net_return_pct": f.net_return_pct,
            "cfc_risk": f.cfc_risk,
            "permanent_establishment_risk": f.permanent_establishment_risk,
            "substance_risk": f.substance_risk,
            "double_taxation_risk": f.double_taxation_risk,
            "withholding_tax_pct": f.withholding_tax_pct,
            "notes": f.notes,
        })

    # Phases
    output["phases"] = result.get("phases", {})

    # Vetoes — CRITICAL: show all veto details
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

    # Veto check
    veto_check = result.get("veto_check", {})
    output["veto_check"] = {
        "blocked": veto_check.get("blocked", False),
        "status": veto_check.get("status", DecisionStatus.PENDING).value
            if hasattr(veto_check.get("status", ""), "value")
            else str(veto_check.get("status", "")),
        "veto_summary": veto_check.get("veto_summary", ""),
        "can_override": veto_check.get("can_override", True),
    }

    # Committee Decision
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

    # CIO Synthesis
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

    # Validation
    output["validation"] = result.get("validation", {})

    # Final status
    status = result.get("status", DecisionStatus.PENDING)
    output["status"] = status.value if hasattr(status, "value") else str(status)
    output["ready_for_principal"] = result.get("ready_for_principal", False)

    # Pattern alerts
    output["pattern_alerts"] = result.get("pattern_alerts", [])

    # ═══════════════════════════════════════════════════════════
    # Flags consolidados cross-border
    # ═══════════════════════════════════════════════════════════
    output["cross_border_flags"] = {
        "cfc_risk": {
            "level": "CRÍTICO",
            "detail": "Art. 100 LIS — Portugal LDA tiene 100% rentas pasivas. "
                      "CFC español imputaría la renta directamente al IRPF del residente.",
            "jurisdictions_affected": ["España (residencia)", "Portugal (holding)"],
        },
        "permanent_establishment_risk": {
            "level": "BAJO",
            "detail": "Inversión pasiva en equity US. Sin actividad que genere PE.",
            "jurisdictions_affected": [],
        },
        "substance_risk": {
            "level": "CRÍTICO",
            "detail": "Portugal LDA sin oficina, empleados ni actividad económica real. "
                      "No cumple requisitos de sustancia OCDE/EU.",
            "jurisdictions_affected": ["Portugal"],
        },
        "withholding_tax_chain": {
            "level": "ALTO",
            "detail": "Cadena: 15% US → 21% IRC PT → 15% distribución PT→ES → 19-28% IRPF ES. "
                      "Tax drag acumulado: 45-52% vs. 31-38% directo.",
            "chain": [
                {"from": "US", "to": "Portugal LDA", "rate": "15%", "treaty": "CDI US-PT"},
                {"from": "Portugal LDA", "tax": "IRC", "rate": "21%", "note": "Sin participation exemption"},
                {"from": "Portugal", "to": "España", "rate": "15%", "treaty": "CDI PT-ES"},
                {"from": "España", "tax": "IRPF", "rate": "19-28%", "note": "Con crédito fiscal parcial"},
            ],
        },
        "double_taxation_risk": {
            "level": "ALTO",
            "detail": "Múltiples CDIs existen (US-PT, PT-ES, US-ES) pero la estructura "
                      "crea sobre-imposición. CDI no elimina CFC.",
            "treaties": ["CDI US-PT", "CDI PT-ES", "CDI US-ES (no aplicable via LDA)"],
        },
        "dac6_reporting": {
            "level": "MEDIO",
            "detail": "Esquema potencialmente reportable bajo DAC6 — "
                      "sociedad interpuesta EU para rentas pasivas de fuente extranjera.",
        },
    }

    # HeadTaxStrategy veto detail
    output["head_tax_strategy_veto"] = {
        "veto_issued": any(
            v.get("agent_role") == "head_tax_strategy"
            for v in output["vetoes"]
        ),
        "severity": next(
            (v.get("severity") for v in output["vetoes"]
             if v.get("agent_role") == "head_tax_strategy"),
            None,
        ),
        "reason": "Estructura via Portugal LDA fiscalmente indefendible — "
                  "CFC crítico (Art. 100 LIS), falta de sustancia, "
                  "tax drag superior a inversión directa, "
                  "no defendible ante inspección AEAT.",
        "alternative": "Inversión directa US → España con CDI bilateral (15% retención + IRPF).",
    }

    return output


async def main():
    print("=" * 72)
    print("  FAMILY OFFICE — ANÁLISIS CROSS-BORDER CON HOLDING")
    print("  Caso: Residente fiscal España → Activo US dividendos")
    print("         via Portugal LDA — USD 500,000 — Horizonte largo")
    print("=" * 72)
    print()

    # Patch call_llm
    import family_office.core.base_agent as _base_agent_mod
    import family_office.core.llm_client as _llm_client_mod

    _original_base = _base_agent_mod.call_llm
    _original_llm = _llm_client_mod.call_llm

    _base_agent_mod.call_llm = mock_call_llm
    _llm_client_mod.call_llm = mock_call_llm

    try:
        # Inicializar sistema
        print("[1/7] Inicializando organización (20 agentes, 5 capas)...")
        orchestrator = FamilyOfficeOrchestrator()
        orchestrator.initialize()
        print(f"       {orchestrator.registry.agent_count} agentes registrados.\n")

        # Crear propuesta — CASO CROSS-BORDER CON PORTUGAL LDA
        print("[2/7] Creando propuesta de inversión cross-border...")
        proposal = InvestmentProposal(
            title="Activo US Dividendos via Holding Portugal LDA",
            asset_class="Renta Variable",
            description=(
                "Inversión en equity US large cap / ETF de dividendos "
                "(SCHD/VYM/SPY) a través de una sociedad holding constituida "
                "como Portugal LDA (Sociedade por Quotas). "
                "Residente fiscal: España. "
                "Flujo: US (fuente) → Portugal LDA (holding) → España (residencia). "
                "Horizonte: largo plazo (10 años). "
                "Objetivo: income via dividendos + capital appreciation."
            ),
            amount_usd=500_000.0,
            expected_gross_return_pct=10.0,
            time_horizon_months=120,  # 10 años — horizonte largo
            jurisdiction="Estados Unidos",
            holding_vehicle="Portugal LDA (Sociedade por Quotas)",
        )
        print(f"       ID: {proposal.id}")
        print(f"       Título: {proposal.title}")
        print(f"       Monto: USD {proposal.amount_usd:,.0f}")
        print(f"       Jurisdicción activo: {proposal.jurisdiction}")
        print(f"       Holding: {proposal.holding_vehicle}")
        print(f"       Horizonte: {proposal.time_horizon_months} meses ({proposal.time_horizon_months // 12} años)")
        print(f"       Retorno bruto esperado: {proposal.expected_gross_return_pct}%\n")

        # Ejecutar pipeline
        print("[3/7] Fase 1+2: Análisis independiente (5 agentes) + Fiscal (7 agentes)...")
        print("       → Los agentes NO ven el trabajo de los otros.")
        print("[4/7] Fase 3: Debate del Comité de Inversión...")
        print("[5/7] Fase 4: Veto Gate (Risk Manager + Head of Tax Strategy)...")
        print("[6/7] Fase 5: Síntesis del CIO...")
        print("[7/7] Fase 6-7: Validación (Instrucción 5) + Presentación...")
        print()

        result = await orchestrator.process_proposal(proposal)

        # ═══════════════════════════════════════════════════════════
        # DecisionRecord completo (JSON)
        # ═══════════════════════════════════════════════════════════

        decision_record = serialize_result(result)

        print("=" * 72)
        print("  DECISION RECORD COMPLETO (JSON)")
        print("=" * 72)
        print(json.dumps(decision_record, indent=2, ensure_ascii=False, default=str))

        # ═══════════════════════════════════════════════════════════
        # Reporte formateado para el Principal
        # ═══════════════════════════════════════════════════════════

        print()
        print()
        report = orchestrator.pipeline.format_principal_report(result)
        print(report)

        # ═══════════════════════════════════════════════════════════
        # Pipeline log
        # ═══════════════════════════════════════════════════════════

        print()
        print("=" * 72)
        print("  PIPELINE LOG")
        print("=" * 72)
        for entry in orchestrator.pipeline.get_pipeline_log():
            print(f"  [{entry['phase']}] {entry['detail']}  — {entry['timestamp']}")

        # ═══════════════════════════════════════════════════════════
        # Decision store
        # ═══════════════════════════════════════════════════════════

        print()
        print("=" * 72)
        print("  DECISION STORE (persistido en disco)")
        print("=" * 72)
        stored = orchestrator.decision_store.get_decision(proposal.id)
        if stored:
            print(json.dumps(stored, indent=2, ensure_ascii=False, default=str))
        else:
            print("  (no persistido)")

        # ═══════════════════════════════════════════════════════════
        # Resumen ejecutivo cross-border flags
        # ═══════════════════════════════════════════════════════════

        print()
        print("=" * 72)
        print("  RESUMEN DE FLAGS CROSS-BORDER")
        print("=" * 72)
        flags = decision_record["cross_border_flags"]
        for flag_name, flag_data in flags.items():
            level = flag_data.get("level", "N/A")
            detail = flag_data.get("detail", "")
            print(f"  [{level:>8}] {flag_name}: {detail[:100]}")

        print()
        print("=" * 72)
        print("  VETO DE HeadTaxStrategy")
        print("=" * 72)
        htv = decision_record["head_tax_strategy_veto"]
        print(f"  Veto emitido: {'SÍ' if htv['veto_issued'] else 'NO'}")
        print(f"  Severidad: {htv['severity']}")
        print(f"  Motivo: {htv['reason']}")
        print(f"  Alternativa: {htv['alternative']}")

        print()
        print("=" * 72)
        print(f"  STATUS FINAL DEL PIPELINE: {decision_record['status'].upper()}")
        print("=" * 72)

    finally:
        _base_agent_mod.call_llm = _original_base
        _llm_client_mod.call_llm = _original_llm


if __name__ == "__main__":
    asyncio.run(main())
