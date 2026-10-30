from experiment.core import *


def main():
    final=json.loads((ROOT/'results/final_evaluation.json').read_text(encoding='utf-8'))
    prep=json.loads((ROOT/'results/preparation.json').read_text(encoding='utf-8'))
    selection=json.loads((ROOT/'results/selection.json').read_text(encoding='utf-8'))
    lines=['# Registro de ejecución — modelos y evaluación', '',
           'Ejecución del 24/10/2026. Registro técnico; no capítulo de tesis ni manuscrito.', '',
           '## Datos y separación', '',
           f"Archivo de origen: 908 229 filas. Conjunto después de calidad y borde: {prep['flow'][-1]['rows']:,} campañas.",
           f"Test principal: {final['primary_n']:,} campañas de {final['primary_companies']:,} empresas, con al menos cinco campañas maduras de historial.",
           f"Poco historial en test: {final['limited_history_n']:,} campañas, informadas aparte. Desarrollo 2022–2023; test 2024.", '',
           '## Comparación final', '',
           '| Respuesta | ML seleccionado | Referencia | MAE ML (pp) | MAE referencia (pp) | Cambio relativo de MAE | IC 97.5% de diferencia (pp) |',
           '|---|---|---|---:|---:|---:|---|']
    labels={'clicks':'Clics únicos','unsubscribes':'Bajas de suscripción'}
    for target,item in final['targets'].items():
        m=item['metrics'];ci=item['comparison'];relative=item['relative_mae_reduction_pct']
        lines.append(f"| {labels[target]} | {item['ml']} | {item['reference']} | {m['full']['mae_pp']:.6f} | {m['reference']['mae_pp']:.6f} | {relative:.2f}% | [{ci['lower_pp']:.6f}, {ci['upper_pp']:.6f}] |")
    lines += ['', 'El cambio relativo positivo indica reducción del error; no es exactitud ni aumento de resultados comerciales.',
              'Los intervalos usan remuestreo cruzado de empresas y bloques temporales de cuatro semanas, con sensibilidades de dos y ocho semanas. Son aproximados; el protocolo y todos los resultados se conservan.', '',
              '## Alcance del hallazgo', '',
              ('La regla predefinida de evidencia favorable para ambas tasas se cumple.' if final['joint_hypothesis_supported'] else
               'La regla predefinida de evidencia favorable para ambas tasas no se cumple. Conservar el resultado sin cambiar modelos o desenlaces usando test.'), '',
              'La comparación de historia sola e historia más mensaje está registrada en final_evaluation.json. Estima valor predictivo añadido, no efectos de cambiar el contenido.', '',
              'El procedimiento para el producto fue elegido en desarrollo, por respuesta:']
    for target,item in selection['targets'].items(): lines += [f"- {labels[target]}: {item['product']}."]
    lines += ['', '## Límites de uso', '',
              'El sesgo medio es negativo: −2.0645 pp en clics y −0.2712 pp en bajas. El método subestima especialmente respuestas altas. La reducción de MAE no implica que su salida sea una media condicional calibrada; se optimizó error absoluto. El valor añadido del mensaje frente a historia sola es pequeño, especialmente en bajas; ver la ablación y sus intervalos.', '',
              'La evidencia se refiere a campañas posteriores del proveedor y a su definición de clics/bajas. Se acepta el supuesto de captura de ventanas; no existe auditoría independiente de seguimiento. Las propiedades del mensaje se tratan como disponibles antes del envío. Las empresas nuevas o con escaso historial usan referencia global y no acreditan transferencia a otra plataforma. No se ha medido impacto comercial causal.', '',
              '## Artefactos', '',
              '- preparation.json: exclusiones y cohortes.',
              '- development_summary.json y development/comparison.csv: comparación de desarrollo.',
              '- selection.json: decisiones congeladas antes del test y hashes de modelos.',
              '- final_evaluation.json y monthly_test.csv: evaluación y estabilidad.',
              '- figures/: gráficos PNG y SVG regenerables con experiment.figures.',
              '- verification_experiment.json: verificaciones de integridad.',
              '- ../data/processed/test_predictions.parquet: predicciones individuales por campaña, fuera de Git.',
              '- ../artifacts/models/: modelos locales y esquema de entradas, fuera de Git.']
    if (ROOT/'results/verification_app.json').exists():
        verified=json.loads((ROOT/'results/verification_app.json').read_text(encoding='utf-8'))
        lines += ['', '## Sistema y evidencia visual', '',
                  f"Aplicación local implementada: {verified['tests_run']} pruebas de integración; estado {verified['status']}. Navegación en Chromium, importación real y descarga verificadas en verification_browser.json.",
                  'Cinco vistas: Resumen, Historial, Estimar campaña, Comparar resultados y Evaluación. El registro local persiste entre reinicios y asocia respuestas por empresa, campaña, instante y mensaje. Las reproducciones históricas se identifican expresamente.', '',
                  '- [Ocho capturas reales](capturas/index.html).',
                  '- [Ocho figuras en PNG y SVG](figures/INDICE.md).',
                  '- [Inicio y reproducción](../EJECUTAR_ESTUDIO.md).', '',
                  'La verificación funcional no constituye un estudio de usabilidad con participantes, validación externa ni aprobación académica. Tesis y manuscrito permanecen pendientes.']
    (ROOT/'results/RESUMEN_EJECUCION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':main()
