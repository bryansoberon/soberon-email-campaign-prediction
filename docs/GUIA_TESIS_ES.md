# Guía en español para la tesis

Esta guía acompaña a la tesis **«Desarrollo de un método basado en Machine Learning para la predicción de métricas clave en campañas de marketing digital»** (Universidad Señor de Sipán), cuyo Anexo 7.4 cita este repositorio. Indica dónde está la evidencia de cada resultado, cómo comprobar las cifras sin volver a entrenar y cómo abrir la aplicación.

El resto de la documentación está en inglés porque el repositorio también acompaña al artículo científico del mismo estudio. Tesis y artículo usan los mismos datos, modelos, predicciones y resultados.

## 1. Qué contiene el repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `study/05_plan/PROTOCOLO_EXPERIMENTAL_V1.md` | Protocolo fijado antes de evaluar: datos, regla de 72 h, particiones, modelos, métrica y criterio de selección. |
| `study/experiment/` | Código del método: preparación (`prepare.py`), construcción de entradas (`core.py`), modelos (`models.py`), desarrollo y selección (`develop.py`), evaluación (`evaluate.py`). |
| `study/artifacts/models/` | Los modelos entrenados y congelados que usan la evaluación y la aplicación. |
| `study/data/processed/test_predictions.parquet` | Predicciones guardadas de las 275,535 campañas de la prueba 2024 y sus respuestas observadas. |
| `study/results/` | Resultados guardados: preparación, desarrollo, selección, evaluación final, resultados mensuales y verificaciones del sistema. |
| `study/experiment/revision_1/` y `study/results/revision_1/` | Código y resultados de los diagnósticos complementarios y de la sensibilidad en desarrollo (secciones 3.1.4 y 3.1.5 de la tesis). |
| `study/app/` | Aplicación web local. |
| `study/tests/` | Pruebas automatizadas del cálculo temporal, las métricas y la aplicación. |
| `S1_Reproducibility_Soberon.zip` | Archivo suplementario enviado con el artículo. |
| `review.py` | Comandos de comprobación, reproducción y aplicación. |

Los datos originales (SendGuard900K, 908,229 filas, licencia CC BY 4.0) no se copian aquí: se descargan de su fuente pública, https://doi.org/10.5281/zenodo.17985618.

## 2. Mapa de la tesis a la evidencia

Las rutas son relativas a `study/` salvo que empiecen por `tools/`. Columna «Se recalcula con `verify`»: «Sí» significa que el comando de la sección 3 vuelve a calcular esas cifras y las compara con las guardadas.

### Capítulo II. Materiales y método

| Parte de la tesis | Evidencia | Se recalcula con `verify` |
|---|---|---|
| Tabla II. Campos utilizados | `05_plan/PROTOCOLO_EXPERIMENTAL_V1.md`; `results/preparation.json` (`feature_columns`) | No; es la definición fijada |
| Tabla III. Entorno computacional | `results/preparation.json` (`platform`, `python`, `logical_cpus`, `memory_gb`); `requirements-lock.txt` | No |
| Tabla IV. Calendario de desarrollo y prueba | `05_plan/PROTOCOLO_EXPERIMENTAL_V1.md`; `experiment/develop.py` | No; lo comprueban las pruebas temporales |
| Tabla V. Configuraciones y referencias | `experiment/models.py`; `results/selection.json` | No |
| Regla de 72 h y construcción de entradas (Fig. 2) | `experiment/core.py`; `tests/test_temporal.py` | Sí, mediante las 17 pruebas |
| Tablas VI y VII. Requisitos del sistema | `tests/test_app.py`; `results/verification_app.json`, `verification_browser.json`, `verification_bilingual.json` | Sí, las pruebas automatizadas |

### Capítulo III. Resultados (3.1.2 a 3.1.6)

| Parte de la tesis | Evidencia | Se recalcula con `verify` |
|---|---|---|
| Tabla VIII. Preparación del conjunto de datos | `results/preparation.json` (`flow`) | No; requiere los datos originales (sección 5) |
| Tabla IX. Campañas por periodo e historial | `results/preparation.json` (`cohorts`); `results/final_evaluation.json` (`limited_history_n`) | No; requiere los datos originales |
| Tabla X. MAE de desarrollo | `results/development_summary.json`; `results/selection.json` | Sí, la agregación de las tres ventanas |
| Tabla XI. Errores en la prueba 2024 | `data/processed/test_predictions.parquet`; `results/final_evaluation.json` | Sí |
| Tabla XII. Aporte del mensaje (solo historial) | Mismas predicciones; `final_evaluation.json` (`message_ablation`) | Sí |
| Tabla XIII. Errores por unidad de ponderación | `final_evaluation.json` (`weighted_mae_pp`, `company_macro_mae_pp`) | Sí |
| Tabla XIV. Recursos computacionales | `results/selection.json`; `final_evaluation.json` (`prediction_seconds`) | No; son mediciones de la ejecución original |
| Fig. 6. Diferencias pareadas e intervalos | `experiment/evaluate.py`; predicciones guardadas; `final_evaluation.json` (`comparison`) | Sí; los intervalos, con `--intervals` |
| Fig. 7. MAE mensual | `results/monthly_test.csv` | Sí |
| Fig. 8. Grupos de predicción | `results/figures_tesis/diagnostic_groups.csv` | Sí |
| Figs. 9–15 y Tabla XV. Aplicación y pruebas de integración | `app/`; `tests/test_app.py` (los diez casos de integración); `results/verification_app.json` | Sí, las pruebas; las vistas se comprueban abriendo la aplicación (sección 4) |

### Análisis complementarios (3.1.4 y 3.1.5)

Estos análisis se hicieron después de la evaluación principal y no la modifican. La carpeta se llama `revision_1` porque se añadió durante la revisión editorial del artículo asociado. Su README en inglés describe cada archivo.

- **Diagnósticos (archivos `fase1_*`):** usan las predicciones de 2024 ya guardadas, sin reentrenar.
- **Sensibilidad (archivos `fase2_*`):** reentrena modelos solo con los datos de desarrollo 2022–2023. Ninguno de esos modelos se evaluó en 2024 ni reemplazó a los modelos congelados.

| Resultado de la tesis | Archivo en `results/revision_1/` | Dónde encontrar la cifra |
|---|---|---|
| 3.1.5: identificación de bajas altas (umbral 0.2400 %, 14.43 % frente a 30.19 %; Recall@k 40.91 % y 41.45 %) | `fase1_a_riesgo_bajas.csv` | Filas `observed >= training P90`; columna `recall` (en proporción: 0.144275 = 14.43 %); `alarm_rule` distingue el umbral (`score >= threshold`) de Recall@k (`top k`); `method` distingue el modelo (`full_model`) de la regla (`last5_median`) |
| 3.1.5: mediana y media observadas por grupo de predicción (9.6114 % estimado frente a 6.1159 % observado) | `fase1_b_calibracion.csv` | Columnas `pred_mean`, `obs_median` y `obs_mean` |
| 3.1.5: reducción por quintil de volumen (3.92 % a 40.36 % en clics) | `fase1_subgrupos.csv` | `dimension = campaign_volume`; columna `relative_mae_reduction_pct`; `delta_lower` y `delta_upper` son el intervalo |
| 3.1.5: 373 empresas sin participación en el desarrollo (12,907 campañas) | `fase1_subgrupos.csv`; `fase1_resumen.json` | `dimension = development_participation`, grupo `unseen (all)`; en el JSON, `development_participation` muestra que esas empresas no aparecen en el ajuste ni en la validación de las tres ventanas |
| 3.1.4: 20 configuraciones aleatorias por familia | `fase2_f_resumen_familias.csv` (resumen); `fase2_f_busqueda.csv` (todas) | Columnas `best_original_mae_pp`, `best_expanded_mae_pp` y `beats_reference` |
| 3.1.4: otras funciones de pérdida de LightGBM | `fase2_g_perdidas.csv`; `fase2_g_riesgo_bajas.csv` | Filas `scope = pooled`; columnas `mae_pp` y `bias_pp`; `method` indica la pérdida (`lightgbm_l1` es la absoluta usada) |

Los errores y sesgos están en puntos porcentuales. Recall, precisión y proporción de alertas están en proporciones (0 a 1).

**Solo en el artículo:** los archivos `fase2_h_*` (atributos del mensaje transformados) y `fase2_i_*` (horizontes de 24 y 48 h y mínimos de historial de 3 y 10 campañas) respaldan análisis que el artículo informa y la tesis no.

## 3. Comprobar las cifras sin reentrenar

Entorno registrado: Windows 11 y Python 3.14.2 de 64 bits. En PowerShell, desde la carpeta del repositorio:

```powershell
python -X utf8 review.py integrity
```

Comprueba que ningún archivo cambió respecto de sus huellas SHA-256. Solo necesita Python.

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r study\requirements-lock.txt
.venv\Scripts\python.exe -X utf8 review.py verify --name verificacion_01
```

`verify` trabaja sobre una copia en `runs/verificacion_01/` y no modifica los archivos originales. Hace cinco cosas:

1. Comprueba que el código, el protocolo, la selección y los modelos congelados coinciden con las huellas registradas.
2. Recalcula desde las predicciones guardadas el MAE, el RMSE, el sesgo, las ponderaciones, las diferencias pareadas, la reducción relativa, el aporte del mensaje, los resultados mensuales y los grupos de predicción, y los compara con los resultados guardados.
3. Comprueba la agregación del MAE de desarrollo de las tres ventanas.
4. Ejecuta las 17 pruebas automatizadas.
5. Genera tablas y figuras del artículo.

Si todo coincide, imprime `PASS`. Para recalcular también los intervalos bootstrap de la prueba principal (tarda más):

```powershell
.venv\Scripts\python.exe -X utf8 review.py verify --intervals --name intervalos_01
```

**Lo que `verify` no recalcula:**

- **Los análisis de `revision_1` (3.1.4 y 3.1.5).** Sus resultados están guardados en `study/results/revision_1/` y pueden abrirse en Excel. Recalcularlos exige los datos procesados que solo genera la reproducción completa (sección 5). Las instrucciones están en `study/experiment/revision_1/README.md`. Cada script de esa carpeta registra al empezar las huellas de los modelos, la selección y la evaluación final, y comprueba al terminar que no cambiaron.
- **Las Tablas VIII y IX**, que dependen de los datos originales.
- **Los tiempos y la memoria de la Tabla XIV**, que corresponden a la ejecución original.

## 4. Abrir la aplicación

```powershell
.venv\Scripts\python.exe -X utf8 review.py app --name aplicacion_01
```

Abre http://127.0.0.1:8765/ en el navegador; la interfaz está en español, y los enlaces EN / ES cambian el idioma. Detén el servidor con Ctrl+C.

La aplicación usa los modelos congelados y un historial público de demostración. Los ejemplos reproducen campañas pasadas; no son pronósticos emitidos en sus fechas originales. Lo que importes o estimes se guarda solo en la carpeta de esa ejecución. El manual completo, en inglés, está en `docs/APPLICATION_USER_GUIDE.md`.

## 5. Repetir el estudio completo (opcional)

```powershell
.venv\Scripts\python.exe -X utf8 review.py reproduce --name reproduccion_01
```

Descarga el CSV original (unos 322 MB), comprueba su huella y repite la preparación, el desarrollo, la selección, el ajuste final y la evaluación 2024 en una carpeta nueva, sin usar los resultados archivados. Requiere bastante tiempo y espacio en disco. Los modelos reentrenados en otro equipo deben compararse por sus cifras, no por la huella de sus archivos.

## 6. Alcance

- La prueba 2024 corresponde a campañas posteriores del mismo proveedor, de empresas con al menos cinco campañas maduras previas.
- No demuestra el desempeño en otro proveedor, en empresas sin historial ni efectos causales sobre ventas o clientes.
- Los intervalos se refieren a la diferencia media de error entre el método y la referencia; no son intervalos de predicción para una campaña individual.
