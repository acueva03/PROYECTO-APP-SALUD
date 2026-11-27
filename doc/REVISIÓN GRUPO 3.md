# Revisión técnica formal del proyecto

## **Informe revisión**

| Campo | Contenido |
|---|---|
| **Proyecto, grupo revisado y versión** | Proyecto *Motorflow* (repositorio Alvaro1331/Proyecto-IS1) · Grupo revisado: 3 · Versión: wiki a 24/11/2026 |
| **Qué se revisó** | Wiki del repositorio del grupo: historias de usuario, gestión de riesgos, estimación y métricas, y planificación, contrastadas con el Checklist, la página de Pruebas Unitarias y los Sprints 1 a 4. No se ha revisado el código ni el tablero de GitHub Projects. |
| **Quién revisó y fecha** | Revisores: **Laura Ávila, Sofía Puebla y Javier Monfort** · Fecha: 24 / 11 / 2026 |
| **Qué se descubrió** | 33 problemas: 7 graves, 24 moderados y 2 leves. Áreas problemáticas: historias de usuario (estado, duplicidad y trazabilidad), seguridad y validez de pruebas, estimación y planificación. |
| **Conclusiones y decisión** | **Se acepta con cambios (ver apartado 3)** |

**Resumen:** 33 problemas: 7 graves, 24 moderados y 2 leves.

| Apartado | Graves | Moderados | Leves | Total |
|---|---|---|---|---|
| A. Historias de usuario (HU) | 2 | 8 | 1 | 11 |
| B. Gestión de riesgos (RG) | 1 | 5 | 1 | 7 |
| C. Estimación y métricas (EM) | 2 | 6 | 0 | 8 |
| D. Planificación (PL) | 2 | 5 | 0 | 7 |
| **Total** | **7** | **24** | **2** | **33** |

---

## 1. Lista de problemas de revisión

Severidad: G = grave, M = moderado, L = leve. Todos los problemas están en estado **Abierto**.

### A. Historias de usuario

| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| HU01 | Estado de las historias contradictorio entre la página de HU, el Checklist y las pruebas | Consistente / trazable | G | Fijar una única fuente de estado (tablero) y revisar una a una #58–#61 y #64–#67 frente al código | Abierto |
| HU02 | Prioridades incoherentes con las dependencias | Priorizada / consistente | M | Reordenar prioridades con un mapa de dependencias (#16, #17, #25, #62, #63) | Abierto |
| HU03 | Contadores y distribuciones distintos en HU y Checklist; épica #14 contada como Done | Consistente | M | Unificar totales y retirar la épica #14 del conteo | Abierto |
| HU04 | HU #31 completada en el Sprint 2 pero ausente del catálogo | Completa / trazable | M | Añadir #31 al catálogo o explicar su retirada | Abierto |
| HU05 | Criterios no condicionales y acoplados a la implementación en #58–#61 y #67 | Verificable / negociable | M | Reescribir en formato Si… entonces… sin nombres de clases ni endpoints; decidir los comportamientos alternativos | Abierto |
| HU06 | Tamaño y justificación de INVEST-S contradictorios | Pequeña / estimable | M | Alinear tamaño, días y justificación; dividir las GRANDE | Abierto |
| HU07 | Independencia declarada pero no demostrada | Independiente | M | Añadir sección de dependencias por historia | Abierto |
| HU08 | Funcionalidades entregadas sin historia (tesorería, confirmación del administrador, tarifas, despliegue) | Completa / trazable | M | Crear las historias o épicas que faltan, incluidos los requisitos no funcionales | Abierto |
| HU09 | Criterios ambiguos o no medibles | No ambigua / verificable | M | Sustituir expresiones como inmediato, claro o correctamente por valores concretos | Abierto |
| HU10 | Enlaces de issues rotos y erratas | Calidad documental | L | Corregir los enlaces de #65–#67 y la terminología | Abierto |
| HU11 | Duplicidad funcional de historias y mezcla de roles en el Product Backlog | Independiente / Negociable / Pequeña (INVEST) | G | Fusionar historias duplicadas (#2 y #30; #4 y #36), dividir #4 y unificar los roles del catálogo | Abierto |

### B. Gestión de riesgos

| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| RG01 | Riesgo de seguridad infravalorado con la aplicación ya desplegada | Ningún riesgo alto sin tratar / planificación dirigida por riesgos | G | Reevaluar R24, incorporarlo a los relevantes y planificar #65 con responsable y fecha | Abierto |
| RG02 | Plan desactualizado respecto al proyecto real | Lista de riesgos actualizada | M | Retirar o rehacer R1 y R4; añadir riesgos de despliegue; llevar registro de cambios | Abierto |
| RG03 | Responsables y fechas genéricos, sin historial | Responsable y seguimiento periódico | M | Nombrar una persona por riesgo, fecha de revisión y registro de cambios | Abierto |
| RG04 | Riesgos materializados sin reevaluar (R23, R26, R27) | Seguimiento / gestión de contingencia | M | Registrar incidentes, reevaluar valores y aplicar el protocolo escrito | Abierto |
| RG05 | Escala y línea de corte no reconciliadas; Pareto no demostrado; sin decisión por riesgo | Probabilidad × consecuencia con criterio / decisión por riesgo | M | Unificar escala, justificar el corte e indicar evitar, controlar, asumir o transferir | Abierto |
| RG06 | Supervisión sin disparadores medibles ni evidencia | Reducción, supervisión y gestión | M | Definir umbrales y dejar constancia de la supervisión en cada sprint | Abierto |
| RG07 | Las fichas de la wiki no coinciden con lo que declara el Checklist | Consistente | L | Completar las fichas o ajustar el Checklist | Abierto |

### C. Estimación y métricas

| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| EM01 | Sin estimación cuantitativa ni velocidad | Tamaño y productividad / esfuerzo calculable | G | Estimar en horas o puntos, medir velocidad por sprint y reestimar el backlog | Abierto |
| EM02 | Escala de tallas inconsistente | Estimación definida | M | Definir cada talla en horas y por persona | Abierto |
| EM03 | Sin tabla de planificado frente a real por sprint | Datos históricos / estimaciones actualizadas | M | Registrar historias y esfuerzo planificado y real | Abierto |
| EM04 | Métricas de pruebas incoherentes (51 frente a 58) | Métricas consistentes | M | Actualizar Checklist y README con la suite real | Abierto |
| EM05 | Cumplimiento de TDD y cobertura sin evidencia | Métricas del software / proceso | M | Medir cobertura y aportar evidencia de TDD o corregir la afirmación | Abierto |
| EM06 | Rendimiento y despliegue sin medir | Métricas con valores objetivo | M | Medir latencia en Azure y abrir una incidencia para el huso horario | Abierto |
| EM07 | Alcance del MVP y recursos sin definir | Ámbito definido y recursos descritos | M | Documentar el alcance del MVP, las horas disponibles, los servicios y la fecha final | Abierto |
| EM08 | Falsa seguridad en pruebas unitarias de RBAC y ausencia de tests de integración | Validez de verificación / cobertura real | G | Añadir pruebas de integración HTTP (MockMvc) sobre controladores y dividir la suite monolítica | Abierto |

### D. Planificación

| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| PL01 | Sprint 4 sin Sprint Backlog trazable ni objetivo medible | Plan abarcable / objetivos medibles / trazable | G | Rehacer el plan con historias, objetivo evaluable y definición de hecho | Abierto |
| PL02 | Sprints sin fechas, duración ni capacidad | Plan con calendario y recursos | M | Añadir fechas, duración y capacidad por sprint | Abierto |
| PL03 | Las reviews no reconcilian lo planificado con lo entregado | Seguimiento: progreso real frente a planificado | M | Tabla por sprint de historias planificadas, hechas, parciales y añadidas | Abierto |
| PL04 | Acciones de retrospectiva sin responsable, fecha ni seguimiento | Mejora del proceso | M | Asignar responsable, fecha e indicador y revisarlas en el sprint siguiente | Abierto |
| PL05 | El Checklist declara documentación de sprints que no coincide con la wiki | Consistente | M | Completar el Sprint 1 y aportar el Sprint 5 o corregir el Checklist | Abierto |
| PL06 | Historias pendientes sin sprint ni responsable | Plan hasta la entrega final | M | Asignar las pendientes a sprints concretos, empezando por #65 y #66 | Abierto |
| PL07 | Carga imposible en Sprint 2 (estimación retrospectiva) y ruptura de cadencia Scrum | Plan abarcable / estimación empírica / cadencia fija | G | Recalibrar tallas con criterios empíricos y fijar una duración uniforme para todos los sprints | Abierto |

---

## 2. Descripción detallada de los errores

## A. Historias de usuario

**HU-01 (G) · Estado de las historias contradictorio**
La página de Historias de Usuario da #58, #59, #60, #61, #65, #66 y #67 como Sin iniciar (7). Sin embargo, la página de Pruebas Unitarias incluye las pruebas 54 a 58 sobre la lógica de #58, #59, #60, #61 y #67, y la suite figura como 58/58 en verde. O el estado está desactualizado o esas pruebas no ejercitan código real.
El Checklist dice 34 Done y 6 Sin iniciar (40 historias), enumera «5 historias en Sin iniciar» con siete números (#58, #59, #60, #61, #64, #65 y #66), incluye #64 (que es Done) y omite #67. También dice que las historias van de HU #2 a HU #64, cuando existen hasta la #67. El repositorio muestra 14 issues abiertos y la página de HU solo 7 pendientes, sin explicar la diferencia. Sin un estado fiable no se puede saber qué falta para el MVP.

**HU-02 (M) · Prioridades incoherentes con las dependencias**
#17 (Aceptar o rechazar presupuestos) es BAJA porque «no bloquea el trabajo diario si el personal confirma los presupuestos por teléfono». Pero #63 (ALTA) extiende el flujo de #17 y #62 (ALTA) se apoya en el estado RECHAZADO del presupuesto. Una historia ALTA depende de una BAJA. #25 (Generar facturas) es BAJA porque «se pueden cerrar y cobrar sin la plantilla de factura», mientras el Sprint 3 presenta el ciclo presupuesto–factura (#16, #17, #25) como eje de las nuevas funcionalidades. La prioridad no refleja el orden real del trabajo.

**HU-03 (M) · Contadores distintos**

| Dato | Página de HU | Checklist |
|---|---|---|
| Total de historias | 41 | 40 |
| Done / sin iniciar | 34 / 7 | 34 / 6 |
| Prioridad ALTA / MEDIA / BAJA | 13 / 23 / 5 (41) | 12 / 21 / 5 (38) |
| Tamaño GRANDE / MEDIA / PEQUEÑO | 7 / 19 / 15 (41) | 6 / 18 / 14 (38) |

Además, la épica #14 no tiene criterios de aceptación, está dividida en #29 y #30 y aun así cuenta como Done, con prioridad ALTA y tamaño GRANDE (doble conteo que el propio Checklist reconoce como pendiente de corregir).

**HU-04 (M) · HU #31 desaparecida**
El Sprint 2 (planificación y review) da por completada la HU #31, «Visualización de los recursos del taller». No aparece en el índice ni en el catálogo, mientras que el resto de historias del Sprint 2 sí. La numeración también tiene huecos (#1, #11, #28, #33, #37–#57); si se debe a que issues y pull requests comparten numeración, debería indicarse.

**HU-05 (M) · Criterios no condicionales y acoplados a la implementación**
El Checklist afirma que los criterios están redactados en formato «Si…, entonces…». En #58 (4 de 7), #59 (4 de 7), #60 (3 de 7), #61 (4 de 7) y #67 (2 de 6) hay 17 criterios que no lo siguen, de 201 en total. Además citan clases, campos y endpoints: #58 criterio 2 (vehiculoId, descripcionAveria), #59 criterio 6 (DELETE /api/usuarios/{id}) y #60 criterio 6 (DELETE /api/materiales/{id}). Esto contradice el criterio Negociable, que pide el qué y no el cómo. Además, #59 criterio 5 admite dos comportamientos distintos («desasignarlo o exigir su reasignación previa») y no se puede escribir una prueba única.

**HU-06 (M) · Tamaño y justificación de INVEST-S contradictorios**
#61 es MEDIA (2–3 días) pero su justificación de S dice «pocas horas». #66 figura como MEDIA en la cabecera, «uno o dos días» en S y «Pequeño / Medio» en el texto de tamaño. #59 y #67 se justifican con «pocas horas» pese a tener siete y seis criterios, con cambios de contraseña con hash, datos fiscales e integridad con reparaciones. Las GRANDE (#2, #29, #30, #36 y #65) afirman cumplir S «porque caben en el sprint de 2 semanas», lo que no es un argumento de tamaño. Además GRANDE se describe como «+3 días» en el resumen y «3–4 días» en cada historia.

**HU-07 (M) · Independencia no demostrada**
Todas las historias declaran cumplir «íntegramente» el criterio I, pero hay dependencias claras no documentadas: #62 y #63 dependen de #16 y #17; #25 de #16, #17 y #62; #34 de #32; #58 de #23 y #24; #67 de #4. Solo #3 y #63 reconocen alguna. Sin un mapa de dependencias no se puede ordenar el backlog.

**HU-08 (M) · Funcionalidades entregadas sin historia**
La wiki describe como entregadas, o las usa en el Checklist como regla de negocio, funcionalidades que no tienen una historia propia: la tesorería del taller (solo visible para el administrador, con fondo inicial de 2.000 €), la confirmación del administrador antes de entregar y cobrar (estado CONFIRMADA) con su centro de control de notificaciones, la configuración de margen comercial (15 %), IVA (21 %) y tarifas, el modo claro/oscuro y rediseño del Sprint 4, y el despliegue en Azure con el problema del huso horario. Estas últimas son requisitos no funcionales sin historia ni criterios de aceptación.

**HU-09 (M) · Criterios ambiguos o no medibles**
Ejemplos: #3 criterio 1 («notificación… (y/o aviso por correo)») no decide el canal; #15 criterio 1 («de forma inmediata»); #65 criterio 1 («al instante»); #66 criterio 2 («se muestran correctamente»); «mensaje claro» en #2, #15 y #59. Expresiones de este tipo aparecen en más de la mitad de las historias y no se pueden convertir en una prueba sin definir un valor (tiempo, texto o formato).

**HU-10 (L) · Enlaces y erratas**
Los enlaces de #65, #66 y #67 apuntan a una búsqueda de Google que contiene la URL del issue, en lugar de al issue. Hay erratas en los nombres: «#HU 3» y «#3HU» (Sprint 4), «HHU» y «Spring Planning» (Sprint 3).

**HU-11 (G) · Duplicidad funcional de historias y mezcla de roles en el catálogo**
La HU #2 («Vista del cliente», ALTA, GRANDE, Done) y la HU #30 («Muestra de datos y actividad», ALTA, GRANDE, Done) describen exactamente la misma funcionalidad para el rol Cliente (consultar el estado de reparación en tiempo real desde su panel personal y vincular códigos localizadores de 8 caracteres), habiéndose planificado y dado por completadas ambas en el Sprint 2. Lo mismo sucede con el solapamiento entre HU #4 («Inicio de sesión de clientes», GRANDE) y HU #36 («Log-In», GRANDE), donde además HU #4 agrupa tres funcionalidades distintas (registro con auto-vinculación telefónica, inicio de sesión y recuperación de clave por código de 6 dígitos) sin aplicar splitting. Asimismo, el catálogo mezcla los roles «Mecánico Jefe» (#8, #10, #12), «Mecánico jefe (administrador)» (#7) y «Administrador» (#16, #20, #27, #35, #59, #60), llegando el Sprint 3 Planning a atribuir la elaboración de presupuestos al «mecánico jefe» cuando la HU #16 la asigna al «administrador».

## B. Gestión de riesgos

**RG-01 (G) · Riesgo de seguridad infravalorado**
R24 («Que nos hackeen el código») está valorado Catastrófica × Improbable = 5 puntos y queda fuera de los 13 relevantes. Pero la aplicación ya está desplegada en Azure y la HU #65 (ALTA, GRANDE, Sin iniciar) describe que hoy se pueden pedir datos de clientes y facturas o borrar gastos saltándose la web con Postman o curl. Aun así, el Checklist marca el área de seguridad y RBAC como CUMPLE. No hay ningún riesgo sobre los datos personales alojados en la nube (DNI, teléfono, dirección fiscal). La probabilidad de R24 ya no es Improbable y la medida (#65) no tiene sprint, responsable ni fecha.

**RG-02 (M) · Plan desactualizado**
R1 (quedarnos sin RAM con H2) y R4 (problemas con la migración de base de datos, con contingencia «mantener H2») hablan de una situación ya superada: la base de datos pasó a MySQL en el Sprint 3 y a un servidor en Polonia en el Sprint 4. No hay riesgos de despliegue: latencia entre servidores en Suecia y Polonia, huso horario, coste de los servicios en la nube, pérdida de fotos al redesplegar (#66) o dependencia del servidor de correo (#3). La página se editó hace dos semanas y no muestra qué cambió en la revisión que declara el Sprint 4.

**RG-03 (M) · Responsables, fechas e historial**
La Tabla 3 usa responsables genéricos («Equipo Backend», «Todo el equipo», «Mentores internos») y controles como «Sprint intermedio» o «Daily / Semanal», sin una persona ni una fecha. No hay registro de los cambios de probabilidad e impacto.

**RG-04 (M) · Riesgos materializados sin reevaluar**
El Sprint 3 cuenta que ocurrió el riesgo del código generado con IA (R27) y que se resolvió «muy rápidamente», pero no hay registro del incidente ni se reevalúa su probabilidad. R23 (desconocimiento) se materializó con las pruebas, que «no entendíamos del todo». R26 (planificaciones incoherentes) se materializó en el Sprint 4, cuya retrospectiva admite que se planteó mal, y no está entre los 13 relevantes, por lo que carece de contingencia.

**RG-05 (M) · Escala, línea de corte y decisión por riesgo**
La Tabla 1 es cualitativa y la Tabla 2 numérica (1–5), y el corte de 10 puntos no se relaciona con las etiquetas. R31 (Menor × Frecuente, «Alta») y R33 (Catastrófica × Remota, «Media») entran, mientras que R10 («Media») queda fuera, igual que R13, R24 y R25 (todos Catastrófica × Improbable, «Media»). Los 13 riesgos elegidos son 13 de 34 (38 %) y suman 177 de 313 puntos (56,5 %), lejos del 80/20 que se declara. Seis riesgos con 9 puntos (R10, R18, R21, R26, R28 y R29) quedan justo por debajo del corte. Tampoco se indica si cada riesgo se evita, se controla, se asume o se transfiere.

**RG-06 (M) · Supervisión sin disparadores ni evidencia**
R31 fija un objetivo de latencia inferior a 300 ms, pero no hay ninguna medida publicada, ni siquiera tras desplegar la web en Suecia y la base de datos en Polonia. No hay rastro de la «auditoría aleatoria de comprensión» (R5), del control de 48 horas sin reportar (R9) ni del control semanal de tokens (R14). El compromiso del Sprint 2 de actualizar la tabla de riesgos al inicio de cada sprint no se reporta en los Sprints 3 y 4.

**RG-07 (L) · Fichas frente al Checklist**
El Checklist dice que cada riesgo relevante tiene una explicación, factores de aparición y un plan de contingencia paso a paso. En la wiki cada riesgo solo tiene tres líneas (Reducción, Supervisión, Gestión). Además R33 usa el término «fregado de requisitos» sin definirlo.

## C. Estimación y métricas

**EM-01 (G) · Sin estimación cuantitativa ni velocidad**
Las tallas se expresan en días aproximados y no hay horas, puntos, capacidad ni velocidad. La estimación no está calibrada: en el Sprint 2 «la velocidad del equipo ha sido superior a la estimada» y se añadieron cuatro historias (#27, #31, #32 y #34); en el Sprint 3 se entregaron además funcionalidades no planificadas; y en el Sprint 4 «nos sobró tiempo» y se saltó al despliegue. R33 cita un Burndown Chart que no aparece en la wiki.

**EM-02 (M) · Escala de tallas inconsistente**
Pequeño es «~1 día» o «pocas horas», Medio «2–3 días» y Grande «+3 días» o «3–4 días» según la página. #58 estima «1 o 2 días por una pareja», otras historias no indican cuántas personas. La duración del sprint es «primera semana» en el Sprint 1 y «2 semanas» en las historias.

**EM-03 (M) · Sin planificado frente a real**
El Sprint 2 planifica 12 historias (sin contar la épica #14) y añade 4; el Sprint 3 planifica 5 más #29; el Sprint 4 lista solo #3. No hay una tabla por sprint de esfuerzo planificado y real, ni se reestiman las 7 pendientes tras cada sprint.

**EM-04 (M) · Métricas de pruebas incoherentes**
El Checklist y el README (según el Checklist) hablan de 51 pruebas, 51/51 en verde, y reparten el bloque E en 34–43 y 44–51. La página de Pruebas, editada hace unas horas, tiene 58 pruebas con «Tests run: 58» y bloque E en 34–58. Los comandos de ejecución también difieren. Ambas páginas son documentos de entrega.

**EM-05 (M) · TDD y cobertura sin evidencia**
El Checklist marca TDD como CUMPLE, pero la retrospectiva del Sprint 3 dice que el código de ese sprint «no cumple las reglas TDD», la planificación del Sprint 3 habla de pruebas «para revisar el código ya escrito», y las pruebas 54–58 figuran en verde sobre historias Sin iniciar. No hay medida de cobertura ni de defectos por sprint, ni evidencia (commits) del ciclo rojo–verde–refactor. El Sprint 3 planificó pruebas de caja negra y de caja blanca y solo se documentan unitarias.

**EM-06 (M) · Rendimiento y despliegue sin medir**
No hay latencia medida con la web en Suecia y la base de datos en Polonia, ni métricas de disponibilidad o coste en Azure. El problema del huso horario está «localizado» pero no tiene incidencia, responsable ni fecha.

**EM-07 (M) · Alcance del MVP y recursos sin definir**
El Sprint 4 dice que se dio «un salto directo hacia el MVP», pero no se define qué incluye. Quedan pendientes #65 (control de acceso en el servidor) y #66 (fotos persistentes), que afectan a producción. No se documentan las horas por persona, los servicios externos (correo, Azure) ni la fecha de entrega final.

**EM-08 (G) · Falsa seguridad en pruebas unitarias de RBAC y ausencia de tests de integración**
El Checklist (apartado 3) da por cumplido el control de acceso basado en roles (RBAC) apoyándose en las pruebas unitarias 17, 18, 36 y 42. Sin embargo, todas estas pruebas invocan directamente métodos de servicio en memoria (ReparacionService) con repositorios simulados con Mockito, sin ejercitar ningún controlador REST (/api/...) ni filtro HTTP. Como reconoce la propia HU #65 (Sin iniciar), los endpoints desplegados en producción en Azure carecen de verificación de sesión o token en el servidor, generando un falso positivo de seguridad en la suite. Además, las 58 pruebas se concentran en una única clase monolítica (PruebasUnitariasTest.java) exclusivamente de caja blanca, sin pruebas de integración ni de caja negra pese a haberse comprometido en el Sprint 3.

## D. Planificación

**PL-01 (G) · Sprint 4 sin backlog trazable ni objetivo medible**
El plan del Sprint 4 enlaza una sola historia (#3). El resto del trabajo (pruebas, README, riesgos, rediseño del frontend) no tiene historia ni issue. Su principal resultado, el despliegue en servidores externos, se decidió «a última hora» y no estaba planificado ni tiene historia. El objetivo («perfeccionar el funcionamiento y formalizar la documentación») no es evaluable y los sprints 3 y 4 no tienen definición de hecho. La retrospectiva admite que se enfocó demasiado en tareas internas.

**PL-02 (M) · Sin fechas, duración ni capacidad**
Ningún sprint tiene fecha de inicio y fin, ni personas disponibles. Sin ello no se puede calcular la velocidad ni saber qué cabe en un sprint.

**PL-03 (M) · Reviews que no reconcilian**
La review del Sprint 3 dice que se cumplieron «todos los objetivos», pero la retrospectiva reconoce que no se aplicó TDD y la planificación incluía pruebas de caja negra y blanca que no se documentan. Mezcla lo planificado con lo añadido (tesorería, alertas de stock y presupuesto, validación del administrador, centro de control, línea temporal) sin distinguirlo. La del Sprint 4 dice «cumplido con creces» y deja pendiente el huso horario. Ninguna incluye una tabla de historias planificadas, hechas, parciales y añadidas.

**PL-04 (M) · Acciones de retrospectiva sin seguimiento**
El Sprint 2 se comprometió a pactar los DTOs, a mejorar las buenas prácticas de Git y a revisar los riesgos al inicio de cada sprint, pero el Sprint 3 no informa de su cumplimiento. La retrospectiva del Sprint 3 no define acciones concretas para el Sprint 4. La del Sprint 4 propone «equilibrar mejor las tareas internas con funcionalidades visibles» sin responsable, fecha ni indicador.

**PL-05 (M) · Checklist frente a la wiki**
El Checklist dice que hay «Actas de Sprints 1–5» y diarios de los Sprints 1 a 5 con sus cuatro ceremonias. El Sprint 1 solo tiene Planning, Sprint y Review, sin retrospectiva, y en la wiki entregada solo existen los Sprints 1 a 4 (si hay un Sprint 5 no se ha facilitado). El Sprint 4 afirma que la documentación quedó «totalmente revisada», pese a las inconsistencias anteriores.

**PL-06 (M) · Historias pendientes sin sprint**
Las historias pendientes (#58–#61, #65–#67) no están asignadas a ningún sprint ni persona, incluidas #65 y #66, que son necesarias para producción. No hay plan hasta la entrega final.

**PL-07 (G) · Carga imposible en el Sprint 2 y ruptura de la cadencia fija de Scrum**
Según la escala definida en la página de Historias de Usuario, una historia GRANDE supone 3–4 días, una MEDIA 2–3 días y una PEQUEÑA ~1 día. Sin embargo, en el Sprint 2 el equipo declara haber completado 16 historias ejecutables (5 GRANDE más la épica #14, 7 MEDIA y 4 PEQUEÑO), lo que equivale a entre 36 y 48 días-persona de esfuerzo en un único sprint de 2 semanas, justificándolo con una «velocidad superior a la estimada». Esto evidencia que las tallas se asignaron a posteriori sin criterio real de capacidad ni calibración. Asimismo, el Sprint 1 tuvo una duración de 1 semana frente a las 2 semanas declaradas para los sprints posteriores, rompiendo la cadencia fija (time-boxing) de Scrum.

---

## 3. Decisión propuesta

**Aceptar con cambios.** Hay siete problemas graves: el estado contradictorio de las historias (HU-01), la duplicidad funcional de historias y mezcla de roles (HU-11), el riesgo de seguridad infravalorado con la aplicación ya desplegada (RG-01), la falta de estimación cuantitativa (EM-01), la falsa seguridad de las pruebas unitarias de RBAC sin tests de integración (EM-08), un Sprint 4 sin backlog trazable (PL-01) y la carga imposible del Sprint 2 con ruptura de cadencia (PL-07).

El proyecto no está mal ejecutado: según la wiki hay una aplicación desplegada en red, 58 pruebas unitarias en verde, historias con justificación INVEST y criterios de aceptación, una matriz de riesgos con contingencias y retrospectivas autocríticas. Los problemas son de coherencia documental, trazabilidad y estimación, y se pueden corregir sin rehacer el producto. Por eso corresponde aceptar con cambios: se fija esta lista de acciones y se corrige sin nueva RTF. La excepción es HU #65, que debe planificarse con responsable y fecha antes de la entrega final por afectar a la seguridad de datos personales.

**Seguimiento:** el jefe de revisión comprueba cada punto de la lista, empezando por los 7 graves y la unificación del estado de las historias, antes de la planificación del siguiente sprint.

---

## 5. Registro de revisión (firmas)

| Asistente | Rol | Conformidad con la decisión | Firma |
|---|---|---|---|
| Laura Ávila | Revisor | Sí | |
| Sofía Puebla | Revisor | Sí | |
| Javier Monfort | Revisor | Sí | |
| Álvaro Sánchez | Participante del grupo 3 | Sí | |
| Marcos Martín | Participante del grupo 3 | Sí | |
