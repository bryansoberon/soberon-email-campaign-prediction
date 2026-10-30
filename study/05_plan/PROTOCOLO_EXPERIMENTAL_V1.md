# Protocolo experimental v1 — 24/10/2026

Fijado antes del primer ajuste de modelos. Desarrollo autorizado por el autor el 24/10/2026. Conserva título, objetivo general y los seis objetivos de la matriz. Este registro técnico no es la redacción de tesis/manuscrito.

## Alcance y supuestos declarados

Campañas agregadas publicadas en SendGuard900K v1.0.0; tasas de clics únicos registrados y bajas por cada cien envíos, acumuladas a 4320 minutos. No se añade una clasificación comercial/transaccional inexistente. El tipo 0 excluye pruebas A/B y optimización de la población principal. Se acepta la definición de ventanas del proveedor; no existe certificación independiente de captura exhaustiva. Se excluyen envíos a partir de 2024-12-29 00:00 UTC para reservar 72 horas al final del periodo publicado. Esta regla no prueba ausencia de pérdidas anteriores.

La muestra exige IDs no repetidos, envíos positivos, numeradores entre 0 y envíos, fecha válida y características del mensaje no negativas y finitas. Se registran exclusiones secuenciales. Se asume que propiedades estructurales del mensaje reflejan el contenido enviado y pueden obtenerse antes de lanzarlo; no hay instantáneas históricas que prueben su invariabilidad. El volumen enviado solo construye respuestas y estadísticas de campañas anteriores, nunca es entrada de la campaña actual.

## Entradas y maduración

Propiedades: tamaño de contenido; número de imágenes, imágenes embebidas, archivos y enlaces; tamaños de imágenes/archivos; cantidades de marcas de personalización totales y por ubicación. Excluir enlaces bloqueados, moderación, etiquetas manuales, dominios, IDs como números y toda respuesta actual. Se omite calendario como predictor para no equiparar fecha efectiva con fecha planificada.

Historial por emisor: número de campañas maduras, tasas medias y ponderadas por volumen, última tasa, media y mediana de últimas cinco, días desde última campaña madura y volumen medio histórico. Solo se admiten respuestas con envío + 72 h estrictamente anterior a la campaña estimada. Historial actualizado secuencialmente durante validación/test con resultados ya maduros; pesos de modelos y reglas permanecen fijos. Población principal: al menos cinco campañas maduras previas, umbral definido por diseño; nuevos/poco historial se reportan separadamente con referencia global, sin afirmar transferencia externa.

## Separación y selección

Desarrollo: 2022–2023. Tres ventanas prospectivas: enero–abril 2023, mayo–agosto 2023, septiembre–diciembre 2023. En cada origen se entrena con campañas desde 2022 cuyas respuestas ya maduraron, y con al menos cinco campañas históricas. La última ventana se corta el 29/12/2023 para no usar etiquetas que maduren después del origen final.

Test final: 01/01/2024 inclusive a 29/12/2024 exclusivo; ninguna selección según su desempeño. Primero se guardan selección y modelos con hashes; después se ejecuta el test una vez. Corregir defectos de implementación exige registrar causa y efecto, nunca buscar métricas favorables.

Referencias por desenlace: media global, mediana global, media histórica del emisor, mediana de últimas cinco campañas maduras, última campaña madura y cero. Se selecciona la mejor referencia por MAE combinado de las tres ventanas (mismo peso por campaña).

Candidatos por desenlace: Ridge con alpha 1 y 100 (log1p en entradas no negativas, escala ajustada solo en entrenamiento); Random Forest, 160 árboles, hojas mínimas 30/100, profundidad máxima 14, max_features=0.8, bootstrap max_samples=0.7; LightGBM con pérdida L1, 400 árboles, learning_rate=0.04, hojas 15/31, mínimo 100 observaciones por hoja, regularización L2=1. Semilla 20261024, seis hilos. Predicciones limitadas al soporte [0,100] mediante una regla fijada antes del ajuste.

Se elige el candidato ML con menor MAE conjunto de desarrollo por tasa, desempate por nombre. No se añade presupuesto después del test. La pérdida L1 permite estimar una respuesta central orientada al error absoluto; no se presentan esas salidas como medias esperadas de conteos o probabilidades individuales. Ridge y RF son comparadores de otras funciones de ajuste.

Ablación predefinida: repetir la configuración ML elegida usando solamente las variables históricas. La comparación con este modelo informa el aporte incremental de las propiedades del mensaje; no es evidencia causal de modificar un mensaje.

## Evaluación e incertidumbre

Primario: MAE macro por campaña y desenlace, puntos porcentuales. Secundarios: RMSE, sesgo, MAE ponderado por envíos, MAE medio por empresa; desgloses mensuales e historial. Recursos: tiempo de ajuste/inferencia y memoria RSS muestreada del proceso (no memoria incremental exclusiva de un algoritmo).

Contraste pareado: diferencia de errores absolutos ML − referencia. Intervalos percentiles del 97.5% por desenlace (ajuste Bonferroni para dos desenlaces), 2000 repeticiones. Remuestreo cruzado de empresas y bloques de cuatro semanas del calendario (bloques móviles circulares), usando el producto de multiplicidades. Es una adaptación de bootstrap por factores cruzados y bloques, no un intervalo exacto. Sensibilidades predefinidas: bloques de dos y ocho semanas, 1000 repeticiones. Afirmar mejora en ambos requiere límite superior menor que cero en ambos; mostrar también magnitud y estabilidad. La mejora mínima comercial relevante no está establecida, por lo que no se afirma beneficio económico.

No se calcularán AUC/F1 para fingir clasificación de una tarea de tasas. No se elegirán umbrales o ventanas con test. No se mostrarán intervalos predictivos por campaña no validados. Para el producto se usa el ganador entre ML y referencia según desarrollo; el test caracteriza su rendimiento sin cambiar la elección. La inferencia con menos de cinco campañas maduras utiliza referencia global y se identifica como tal.

## Producto y reproducción

Implementación posterior al test: sistema web local, importar CSV bajo esquema verificable, consultar historial, estimar campaña y comparar registros maduros. Demo con datos reales e IDs anonimizados. Importar columnas semejantes de otro proveedor no prueba equivalencia; cualquier adaptación externa debe comprobar definiciones, horizonte, entradas y rendimiento. No hay conector Meta Ads comprometido.

Guardar particiones, exclusiones, configuraciones, selección, predicciones, tablas, figuras PNG/SVG, modelos y manifiestos con hashes. Datos/modelos quedan fuera de Git; fuentes, código y resultados agregados pueden versionarse. Pruebas de causalidad temporal del cálculo, campos prohibidos, maduración, selección sin test, equivalencia offline/web y errores de importación. Capturas de pantallas reales al terminar. Tesis y manuscrito se mantienen pendientes.

## Sustento separado de la RS

La RS del autor orienta familias de modelos. La adaptación a tasas agregadas y el protocolo se sustentan complementariamente en documentación primaria de [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), [Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html), [objetivos LightGBM](https://lightgbm.readthedocs.io/en/stable/Parameters.html), [evaluación temporal](https://scikit-learn.org/stable/modules/cross_validation.html) y [métricas de regresión](https://scikit-learn.org/stable/modules/model_evaluation.html). La incertidumbre toma como fundamento metodológico a [Owen y Eckles, 2012](https://doi.org/10.1214/12-AOAS547); la extensión con bloques temporales se declara decisión del presente protocolo. Estas fuentes no se añaden retrospectivamente al corpus de la RS ni sustituyen el trabajo bibliográfico pendiente.
