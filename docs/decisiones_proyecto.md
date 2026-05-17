# Decisiones del proyecto y justificaciones

> Bitácora viva de las decisiones técnicas y metodológicas del proyecto de
> dengue, con las razones detrás de cada una. Sirve como insumo directo
> para el documento final y la sustentación.

---

## D1 — Alcance espacial: 3 municipios foco

**Decisión:** Entrenar **un modelo independiente por cada uno** de los
siguientes 3 municipios:

| DIVIPOLA | Municipio | Departamento | Región | Población 2024 |
|---|---|---|---|---:|
| 23855 | Valencia | Córdoba | Caribe | 36.721 |
| 47288 | Fundación | Magdalena | Sierra Nevada | 75.360 |
| 95025 | El Retorno | Guaviare | Amazonía | 13.324 |

**Por qué 3 (y no 1, ni 10):**

- **1 municipio fue descartado** porque concentra todo el riesgo del proyecto
  en una única serie temporal. Si esa serie presentara un año atípico, un
  hueco de SIVIGILA o estacionalidad rota, no habría plan B. Además, una
  conclusión sobre un solo caso es estadísticamente anecdótica: no permite
  afirmar que "el enfoque regional generaliza".
- **10 municipios fue descartado** por dispersión de esfuerzo. Con el
  tiempo disponible, tunear 10 modelos termina haciendo cada uno a medias.
  Carlos (director) recomendó explícitamente "1 a 3 municipios" en la
  reunión del 2026-04-24.
- **3 es el sweet spot:** suficiente para mostrar robustez de la metodología
  ("funciona en 3 contextos diferentes" no es anécdota), pero pocos para
  cuidar la calidad de cada modelo. Además queda dentro del rango sugerido
  por el director.

**Por qué *estos* 3:**

- Carlos planteó tres criterios válidos para selección: (a) mayor número
  absoluto de casos, (b) mayor incidencia por habitante, (c) interés
  particular. Elegimos **(b) — mayor incidencia × 100k habitantes** —
  porque captura las comunidades más vulnerables (que suelen ser
  invisibilizadas en el criterio de casos absolutos, dominado por ciudades
  grandes como Cali o Ibagué).
- Dentro del top 10 por incidencia, priorizamos **diversidad climática y
  regional** para fortalecer la narrativa del informe:
  - **Valencia (Caribe / Córdoba):** zona ganadera, clima cálido húmedo,
    representativa del foco endémico del Caribe colombiano.
  - **Fundación (Sierra Nevada / Magdalena):** transición entre llanura
    aluvial y piedemonte; contraste de temperatura y precipitación con
    Valencia.
  - **El Retorno (Amazonía / Guaviare):** selva, alta humedad, baja densidad
    poblacional, contexto socioeconómico muy distinto. Es la diferenciación
    geográfica más fuerte respecto al Caribe.

Si la metodología funciona en estos 3 contextos, el argumento de
generalización regional es mucho más fuerte que probarla en 3 municipios
del mismo departamento.

---

## D2 — Cobertura temporal: 2007–2024 continuo

**Decisión:** Usar **todos los años** entre 2007 y 2024 inclusive (18 años,
serie mensual) para entrenamiento y test.

**Por qué:**

- La versión previa del proyecto usaba años discretos sueltos
  (2010/2016/2019/2022/2024), lo cual deja huecos de hasta 6 años entre
  observaciones. Eso impide capturar estacionalidad y ciclos epidémicos,
  y hace inviable la partición train/test cronológica.
- Carlos lo señaló como debilidad metodológica en la reunión del
  2026-04-24: "usar toda la serie continua, no años representativos".
- 18 años × 12 meses = 216 puntos por municipio. Es lo suficiente para
  modelos clásicos (regresión logística, XGBoost) pero **demasiado poco
  para deep learning**, lo cual también se decidió evitar (ver D5).

---

## D3 — Partición train/test cronológica

**Decisión:** Train = primer ~80% de los meses del rango / Test = último
~20%. Aproximadamente:

- Train: 2007–2019 (13 años)
- Test: 2020–2024 (5 años)

**Por qué:**

- En series de tiempo no se hace partición aleatoria — eso produciría
  fuga temporal (información del futuro contaminando el entrenamiento).
- Lo que se quiere predecir es el futuro inmediato; por eso el test debe
  ser el **periodo más reciente**.
- Carlos lo explicitó: "el test debe ser el último 20% de los años".
- El test de 2024 solo (versión previa del proyecto) era un caso atípico
  (año de exceso de dengue por El Niño) que no representa condiciones
  normales. Con test de 5 años se mide rendimiento promedio en
  condiciones variadas.

---

## D4 — Métricas priorizadas: Precision y Recall

**Decisión:** Reportar y optimizar **Precision** y **Recall** sobre el
test como métricas principales. Accuracy se reporta como referencia pero
no se usa para decisión.

**Por qué:**

- El problema es **detección de excesos epidemiológicos** — una clase
  minoritaria altamente desbalanceada. Accuracy en este contexto es
  engañoso: un modelo que siempre predice "no exceso" puede tener 85%+
  de accuracy y ser completamente inservible.
- **Precision** responde: "cuando el modelo dice que hay exceso, ¿qué
  tan confiable es?" — relevante para la utilidad operativa (evitar
  movilizar recursos en falsos positivos).
- **Recall** responde: "de los excesos reales, ¿cuántos detecta el
  modelo?" — relevante para la utilidad sanitaria (no perder brotes
  reales).
- Ambas se reportan **por municipio** (no promediadas), porque la
  decisión de implementar el modelo se toma a nivel local.

**Punto de comparación:** el modelo nacional de Entrega 1 obtuvo
Precision ≈ 43% / Recall ≈ 87%. Es un modelo "alarmista": detecta casi
todo pero con muchas falsas alarmas. **El objetivo cuantitativo es subir
Precision sin sacrificar Recall por debajo de ~60%** en al menos 2 de los
3 municipios foco.

---

## D5 — Modelos: regresión logística regularizada + XGBoost

**Decisión:** Mantener únicamente **Regresión Logística con regularización
L2** y **XGBoost** como modelos finales. Eliminar Random Forest. No usar
deep learning (LSTM, Transformers, TFT).

**Por qué se eliminó Random Forest:**

- En la matriz de Entrega 1, Random Forest dio Recall ≈ 2.4% sobre la
  clase positiva ("exceso"). Es decir, **no detecta excesos** —
  inservible para el problema.

**Por qué no deep learning:**

- 216 puntos por municipio × 3 municipios = 648 observaciones totales.
- Un LSTM con `hidden_size = 64` ya tiene >200 parámetros entrenables.
  Ratio observaciones/parámetros muy bajo → overfitting prácticamente
  garantizado.
- Carlos lo señaló: "el deep learning brillaría si tuvieran ~30 años a
  escala diaria, o muchos municipios × semanas (~700.000 datos)".
  No es el caso.
- Si se intentara, se debería bajar `hidden_size` a 2–8, lo cual ya no
  es "deep" sino esencialmente equivalente a una regresión.

**Por qué Logística + XGBoost son suficientes:**

- Logística regularizada captura relaciones lineales con interpretabilidad
  alta (importante para el reporte y la sustentación).
- XGBoost captura no-linealidades e interacciones, con interpretabilidad
  vía SHAP/feature importance.
- Cubren el espectro de complejidad sin sobrediseñar.

**Manejo del desbalanceo:** `class_weight='balanced'` para Logística;
`scale_pos_weight` recalculado por municipio para XGBoost.

---

## D6 — Población DANE: serie unificada base CNPV 2018

**Decisión:** Usar la serie de proyecciones municipales del DANE
**unificada bajo la base CNPV 2018** (Censo 2018), combinando:

- Retroproyecciones 2005–2017 con base Censo 2018.
- Proyecciones 2018–2042 post-COVID con base Censo 2018.

Se descartó el archivo previo que mezclaba bases (Censo 2005 hasta 2020 +
Censo 2018 desde 2021).

**Por qué:**

- El archivo previo introducía un **salto artificial en 2020→2021** de
  hasta ±25% por municipio (ej. Valencia: 47.869 → 37.459, una caída del
  22%). Eso no es realidad demográfica, es un cambio metodológico del
  DANE al actualizar la base censal.
- Como la partición train/test cae exactamente en ese borde (test empieza
  ~2020), el escalón contaminaría las métricas: el modelo "vería" un
  cambio fuerte que no es epidemiológico.
- Usar una única base CNPV 2018 retroproyectada elimina el escalón:
  Valencia 2020→2021 = +0.5%, Fundación = +2.1%. Cambios demográficamente
  realistas.

**Por qué no la otra dirección (Censo 2005 hasta 2024):**

- No existe oficialmente. DANE publicó la retroproyección 2005-2017 con
  base Censo 2018, pero **no** una proyección 2021-2024 con base Censo
  2005 (los censos posteriores reemplazan al anterior como base oficial).

---

## D7 — Despliegue: prototipo, no producto

**Decisión:** El entregable de despliegue es un **dashboard prototipo**
que consume el archivo Excel ya procesado y muestra la predicción para
el periodo de test. No se integra Google Earth Engine en tiempo real.

**Por qué:**

- El alcance del proyecto es **demostrativo**, no productivo.
- Integrar APIs en tiempo real (GEE, SIVIGILA stream) requiere
  infraestructura (autenticación, refresco programado, manejo de
  errores) que no aporta al objetivo académico.
- Carlos lo aclaró explícitamente: "que la interfaz consuma la tabla
  de Excel ya generada".

---

## D8 — No esperar datos SIVIGILA 2025

**Decisión:** Cerrar el rango en 2024 y no posponer el cierre del
proyecto esperando publicación de SIVIGILA 2025.

**Por qué:**

- Al momento del análisis, SIVIGILA no había publicado 2025.
- Si llegan a publicarse antes del cierre, se usarían como **segundo
  test sin reentrenar** (validación adicional). Si no llegan, no
  afecta la entrega.

---

## D9 — EDA enfocado, no exhaustivo nacional

**Decisión:** No re-correr el EDA nacional exhaustivo de la Entrega 1
con la serie ampliada. En su lugar, hacer un **EDA focalizado en los 3
municipios foco** dentro del notebook de feature engineering.

**Por qué:**

- El EDA nacional de Entrega 1 (`notebooks/02_eda_dengue.ipynb` +
  `03_eda_dengue_grave.ipynb` + `04_eda_comparativo.ipynb`) ya cubre las
  preguntas descriptivas a nivel país. Repetirlo con más años no
  cambia las conclusiones cualitativas.
- Lo que sí informa decisiones de modelado es entender la dinámica
  específica de los 3 foco: estacionalidad local, calidad de reporte
  por año, correlación clima→casos local. Esto sí se hace nuevo.
- Tiempo invertido en EDA redundante = tiempo no invertido en modelado
  y dashboard.

---

## D10 — Pipeline de datos: loaders genéricos, panel filtrado

**Decisión:** Mantener los loaders de bajo nivel (`cargar_dengue`,
`cargar_dane`, `cargar_clima`) genéricos a nivel país. **Filtrar
únicamente al construir el panel mensual procesado** (`data/processed/
panel_municipal_mensual.csv`).

**Por qué:**

- Los loaders genéricos cuestan lo mismo escribir; reutilizables si en
  el futuro se quiere extender el proyecto.
- El panel filtrado a los 3 foco queda pequeño (~648 filas) y rápido de
  iterar en notebooks.
- La constante `MUNICIPIOS_FOCO` en `src/utils.py` centraliza la
  decisión — un solo lugar para cambiar si se necesitara revisar.

---

## D11 — Fecha del caso: `INI_SIN` (inicio de síntomas)

**Decisión:** Asignar cada caso al mes correspondiente a su `INI_SIN`
(fecha de inicio de síntomas), no a `FEC_NOT` (notificación) ni a
`FEC_HOS` (hospitalización).

**Por qué:**

- **Estándar epidemiológico**: las curvas epidémicas se construyen sobre
  fecha de inicio de síntomas porque es la que mejor refleja la dinámica
  real de transmisión. La notificación introduce retrasos administrativos
  variables (entre días y semanas), y la hospitalización solo aplica a
  un subconjunto.
- **Consistencia con el modelo de transmisión**: el lag biológico
  (ciclo del mosquito, incubación viral) tiene sentido respecto al
  inicio de síntomas, no respecto a cuándo el sistema de salud registró
  el caso.
- **Robustez frente a cambios administrativos**: si en algún año
  SIVIGILA cambió los plazos de notificación, `INI_SIN` no se ve
  afectado pero `FEC_NOT` sí.

**Fallback:** si `INI_SIN` está nulo para un caso (en Entrega 1 era
~0% en regular y 0% en grave), usar `FEC_NOT` como respaldo en lugar
de descartar el caso.

---

## D12 — Definición del target: percentil 75 histórico por mes con piso de 2

**Decisión:** El target binario "exceso epidemiológico" se define
**por municipio y por mes calendario** así:

```
umbral(m, año) = max( percentil_75( casos(m, año') para año' < año ), 2 )
exceso(m, año) = 1 si casos(m, año) > umbral(m, año)
                 0 en otro caso
```

Es decir: para cada municipio y cada mes (enero, febrero, ...), se
calcula el percentil 75 de casos observados **en años anteriores**,
**con un piso mínimo de 2 casos**, y el mes actual cuenta como "exceso"
si supera ese umbral.

**Evidencia que motivó el piso de 2:**

El EDA exploratorio (notebook `06_eda_foco.ipynb`) comparó tres
variantes sobre Valencia:

| Definición | Prevalencia | Calidad |
|---|---:|---|
| A: p75 sin piso | 57.3 % | ❌ Marca como "exceso" meses con 1-2 casos en 2010-2015, cuando el reporte estaba incompleto / la transmisión era muy baja. Ruido. |
| **B: p75 con piso 2** | **39.6 %** | ✅ Los excesos coinciden con los picos visualmente claros de los brotes. |
| C: p90 sin piso | 42.7 % | ⚠️ Todavía contamina los años pre-2013 (mismo problema que A en menor escala). |

Sin el piso, el target degenera en municipios pequeños o años con
reporte incipiente: si los primeros años tienen historial de 0 casos
en cierto mes, el p75 = 0 y cualquier mes con ≥1 caso se marca como
"exceso", inflando la prevalencia con falsos positivos.

Con piso de 2 casos, la prevalencia global pasó de 50.3 % a 36.8 %
y las prevalencias por municipio quedaron más balanceadas
(Valencia 39.6 %, Fundación 38.5 %, El Retorno 32.3 %).

**Por qué:**

- **Captura estacionalidad real**: el dengue tiene picos estacionales.
  Lo "anormal" no es lo mismo en enero (mes seco) que en julio (lluvioso).
  Calcular el umbral por mes calendario respeta esto.
- **Sin fuga temporal**: el umbral solo usa años previos, no contamina
  con información del futuro. Compatible con la partición cronológica
  (D3).
- **Interpretable**: "exceso = mes en el cuartil superior histórico"
  es fácil de explicar a un revisor.
- **Defendible**: es la formulación que usa el INS Colombia en sus
  canales endémicos publicados.

**Alternativas descartadas:**

- *Umbral fijo por incidencia* (ej. ≥30 × 100k): no respeta diferencias
  entre municipios — Valencia y El Retorno tienen niveles base muy
  distintos.
- *Media + 2 desviaciones móvil*: más sensible a outliers individuales
  y menos interpretable que un percentil.
- *Anomaly detection no supervisado*: pierde la ventaja del aprendizaje
  supervisado y agrega complejidad.

**Parámetro abierto:** el percentil exacto (75 o 90) se afina en la
fase de modelado. Empezamos con 75 (más casos positivos = más fácil
entrenar) y se puede subir a 90 si el modelo lo aguanta.

---

## D13 — Casos = dengue total (regular + grave)

**Decisión:** El target del modelo se construye sobre **dengue total**
(suma de cód 210 + cód 220) por (municipio, mes). En el panel se
preservan también `casos_dengue_regular` y `casos_dengue_grave` como
columnas separadas, para análisis descriptivo y como features
potenciales.

**Por qué:**

- **Volumen**: dengue grave es ~4% del total. En municipios pequeños
  (El Retorno, pob 13k) el grave es 0–2 casos/mes la mayoría del tiempo
  — señal estadísticamente insuficiente para detectar "excesos" como
  target binario.
- **Convención epidemiológica**: los sistemas de alerta temprana de
  PAHO/OMS/INS monitorean **casos totales** porque reflejan la
  intensidad de transmisión. El grave es una clasificación clínica
  derivada que sigue al total con lag.
- **Continuidad con el comparador**: la cifra de Entrega 1 (P=43%,
  R=87%) se calculó sobre dengue total. Mantener el target permite la
  comparación "antes vs después" en el informe.

**Cuándo grave habría sido el target:** si el objetivo fuera planificación
hospitalaria/UCI directa, en lugar de vigilancia epidemiológica.
No es el caso de este proyecto.

---

## D14 — Clima a granularidad departamental

**Decisión:** Mantener las variables climáticas
(`temperatura_c`, `precipitacion_mm`, `ndvi`, `dewpoint_c`) a nivel
**departamental** — es decir, todos los municipios de un mismo
departamento reciben el mismo vector climático mensual.

**Por qué:**

- **Granularidad muncipal no aporta discriminación útil** entre los
  3 foco: cada uno está en un departamento distinto (Córdoba, Magdalena,
  Guaviare), así que el clima departamental ya los separa
  completamente.
- **Costo de redescargar a granularidad municipal:** ~1.040 municipios
  × 18 años × 12 meses × 4 datasets ≈ 900.000 reducciones GEE. Con el
  script paralelo serían ~2 horas adicionales.
- **Calidad de la señal:** los datasets usados (MODIS LST, CHIRPS,
  MODIS NDVI, ERA5 dewpoint) tienen resoluciones nativas de 1–11 km;
  agregar a municipio en algunos casos sería casi recolectar el mismo
  pixel varias veces. La ganancia informativa es marginal.
- **Si en el futuro se quisiera escalar a más municipios** dentro del
  mismo departamento, ahí sí valdría la pena migrar a granularidad
  municipal. Para 3 foco en 3 departamentos, no.

**Limitación reconocida:** dos municipios del mismo departamento
tendrían exactamente las mismas covariables climáticas. No es nuestro
caso, pero queda documentado para una eventual extensión.

---

## D15 — Features del modelo (28 columnas) e EXCLUSIONES por leakage

**Decisión:** El feature matrix consta de **28 columnas**:

| Familia | Variables | # |
|---|---|---:|
| Clima actual | `temperatura_c`, `precipitacion_mm`, `ndvi`, `dewpoint_c` | 4 |
| Clima rezagado | cada variable × lag 1, 2, 3 | 12 |
| Clima MM3 | media móvil 3 meses (sin incluir el mes actual) por variable | 4 |
| Casos rezagados | `casos_total_lag1`, `_lag2`, `_lag3` | 3 |
| Incidencia rezagada | `incidencia_x100k_lag1`, `_lag2`, `_lag3` | 3 |
| Estacionalidad | `mes_sin = sin(2π·mes/12)`, `mes_cos = cos(2π·mes/12)` | 2 |

**Excluido explícitamente (con razón):**

| Variable excluida | Por qué |
|---|---|
| `casos_total` (lag 0) | **Leakage directo:** el target `exceso` es función de `casos_total > umbral`. |
| `casos_regular`, `casos_grave` | Subconjuntos de `casos_total` en la misma fila → leakage. |
| `hospitalizaciones`, `fallecidos` | Conteos derivados del propio outbreak — disponibles **después** de que el caso ocurre. |
| `umbral_exceso` | Función directa de `casos_total` históricos; aporta poco valor predictivo y huele a leakage indirecto. |
| `incidencia_x100k` (lag 0) | `casos_total / poblacion` — leakage. |
| `casos_total_mm3`, `incidencia_x100k_mm3` | El `mm3` actual del panel incluye el mes corriente → leakage. Re-derivado en el notebook si se requiere. |
| `ano` | El test (2020-2024) tiene años nunca vistos por el train (2007-2019). Incluir `ano` como feature numérica hace que XGBoost no pueda extrapolar y favorece memorización en Logística. Se excluye. |
| `poblacion` | Casi constante dentro de un municipio en train → no aporta señal y se acerca a un id de tiempo. |
| `cod_mpio`, `municipio`, `departamento` | Un modelo por municipio → constantes dentro del modelo. |

**Codificación de la estacionalidad:** se elige codificación cíclica
`sin(2πm/12)` y `cos(2πm/12)` en lugar de one-hot, porque preserva la
proximidad real entre enero/diciembre (importante para modelos lineales).

---

## D16 — Tuning: defaults para Logística + GridSearchCV moderado para XGBoost

**Decisión:**

- **Regresión Logística:** entrenar con defaults de scikit-learn más
  `class_weight="balanced"` (D5). Sin grid search — tiene pocos
  hiperparámetros con impacto y los defaults regularizados (L2, C=1.0)
  son razonables para este volumen.
- **XGBoost:** `GridSearchCV` con `TimeSeriesSplit(n_splits=5)` sobre el
  conjunto de entrenamiento (2007-2019). Grid pequeño:

  ```python
  param_grid = {
      "n_estimators":    [100, 300],
      "max_depth":       [3, 5],
      "learning_rate":   [0.05, 0.1],
  }
  ```

  8 combinaciones × 5 folds = 40 ajustes por municipio × 3 municipios
  = 120 ajustes totales. Tiempo estimado: 2-5 minutos.

**Por qué TimeSeriesSplit y no K-Fold:** mantener la coherencia temporal
del split principal (D3). K-Fold aleatorio violaría la regla "no usar
información del futuro" dentro del CV.

**Por qué no Optuna/bayesiano:** el dataset es pequeño (~150 filas de
train por municipio). El tuning más sofisticado no compensa el costo
de implementación.

**Métrica de selección en GridSearchCV:** `f1` (balance Precision/Recall).
No usamos `roc_auc` porque el problema es desbalanceado y AUC puede ser
optimista cuando la prevalencia es baja.

---

## D17 — Baseline trivial como piso comparativo

**Decisión:** entrenar y evaluar también un **baseline trivial** definido
así:

```
exceso_baseline(m, año) = 1 si casos_total_lag1 > 2
                          0 en otro caso
```

Es decir: "si el mes anterior hubo más de 2 casos, alerta".

**Por qué:**

- Es el "modelo memoria pura" — solo mira el mes pasado.
- Si Logística o XGBoost no le ganan al baseline, probablemente no
  hayan aprendido nada útil sobre clima.
- Para el informe: el baseline da un punto de referencia interno
  ("nuestro modelo Y subió Precision de X% del baseline a Z%") que
  acompaña al comparador externo (43%/87% del modelo nacional de
  Entrega 1).

**Esfuerzo:** ~20 líneas de código, no requiere entrenamiento.

---

## Referencias

- Reunión con Carlos (director) — `docs/reuniones/2026-04-24_seguimiento_carlos.md`
- Mejoras post-reunión — `docs/mejoras_proyecto_post_reunion_carlos.md`
- Constantes del proyecto — `src/utils.py`
