# Revisión técnica formal del proyecto (wiki)
 
## **Informe revisión**

| Campo | Contenido |
|---|---|
| **Proyecto, grupo revisado y versión** | Proyecto *Shelfie* · Grupo revisado: 2|
| **Qué se revisó** | Wiki del repositorio del grupo: historias de usuario, gestión de riesgos, estimación y métricas, y planificación |
| **Quién revisó y fecha** | Revisores: **Andrés Cuevas y Alberto Vilches** · Fecha: 22 / 11 / 2026 |
| **Qué se descubrió** | 33 problemas: 5 graves, 26 moderados y 2 leves. Áreas problemáticas: historias de usuario, estimación y planificación. |
| **Conclusiones y decisión** | **Se acepta con cambios** (ver apartado 3) |
 
**Resumen:** 32 problemas: **5 graves**, **25 moderados** y **2 leves**.
 
| Apartado | Graves | Moderados | Leves | Total |
|---|---|---|---|---|
| A. Historias de usuario (HU) | 2 | 12 | 1 | 16 |
| B. Gestión de riesgos (RG) | 1 | 4 | 1 | 6 |
| C. Estimación y métricas (EM) | 1 | 4 | 0 | 5 |
| D. Planificación (PL) | 1 | 5 | 0 | 6 |
| **Total** | **5** | **25** | **2** | **32** |
 
---
 
## 1. Lista de problemas de revisión
 
Severidad: G = grave, M = moderado, L = leve. Todos los problemas están en estado **Abierto**.
 
### A. Historias de usuario
 
| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| HU-01 | Tamaño y prioridad incoherentes entre historias y tabla final | Consistente / priorizada | G | Mantener una única fuente. Revisar las 35 historias discordantes. Añadir 4.6 y 4.7 a la tabla | Abierto |
| HU-02 | Mismo ID con distinta historia o criterios entre backlog y planificaciones | Consistente / trazable | G | Fijar un backlog maestro con IDs inmutables y un historial de cambios. Corregir H3.2 y H2.4 | Abierto |
| HU-03 | Historias solapadas | Independientes (sin duplicidad) | M | Fusionar o delimitar: 1.6/5.4, 2.5/10.1, 9.1/9.3, 1.2/11.1/11.2, 3.1/3.2, 5.2/7.3/7.4, 1.10/10.5/10.8 | Abierto |
| HU-04 | Estados de una obra sin definir | Completa / no ambigua | M | Definir la tabla de estados por tipo de obra (incluyendo "en curso" y "abandonado") | Abierto |
| HU-05 | Ficha técnica sin campos concretos | Verificable | M | Especificar los campos por tipo de obra | Abierto |
| HU-06 | Registro de progreso incompleto y con criterios cambiantes | Verificable / estable | M | Añadir criterio de "cuánto falta". Fijar el progreso por tipo (películas, series, música) | Abierto |
| HU-07 | Estadísticas y exportación mal acotadas | Completa / verificable | M | Cubrir los 5 tipos de obra. Definir géneros favoritos, formato y contenido exportado | Abierto |
| HU-08 | Criterios de búsqueda y recomendación no verificables | Verificable | M | Definir relevancia, similitud, efecto de las valoraciones y métrica de tendencia | Abierto |
| HU-09 | Criterios contradictorios entre historias relacionadas | Consistente | M | Alinear 2.6 con 1.6 (descripción de lista). Resolver en 3.2 "completa" frente a "tres más relevantes" | Abierto |
| HU-10 | Gestión de cuenta incompleta (registro, sesión, eliminación) | Completa / no ambigua | M | Añadir en 6.1 contraseña y usuario. Concretar sesión, caducidad y cierre de sesión. Definir el alcance del borrado en 4.7 | Abierto |
| HU-11 | Modelo social y de privacidad confuso | Consistente | M | Definir un único modelo de relación (seguir/amigo) y de visibilidad | Abierto |
| HU-12 | Roles y moderación sin historias | Completa | M | Añadir historias de asignación de roles y de gestión de reportes | Abierto |
| HU-13 | Asistente inteligente no verificable | Verificable / completa | M | Criterios medibles, casos sin resultado y RNF de la IA | Abierto |
| HU-14 | Historias demasiado grandes y justificaciones INVEST contradictorias | Pequeña (INVEST-S) / estimable | M | Dividir las historias grandes en entregables cerrables en un sprint | Abierto |
| HU-15 | Criterios ambiguos o no medibles | No ambigua / verificable | L | Sustituir "correctamente", "suficiente", "cuando corresponda" por valores concretos | Abierto |
 
### B. Gestión de riesgos
 
| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| RG-01 | Riesgos críticos ya materializados sin medidas efectivas en el plan siguiente | Ningún riesgo H/IN sin tratar / planificación dirigida por riesgos | G | Convertir las medidas de R1 y R7 en tareas concretas del Sprint 4, con responsable y fecha | Abierto |
| RG-02 | Sin responsable, fechas ni historial por riesgo | Responsable y seguimiento periódico / lista actualizada | M | Añadir responsable, fecha de revisión y registro de cambios de probabilidad e impacto | Abierto |
| RG-03 | Sin decisión evitar, controlar, asumir o transferir | Decisión por riesgo | M | Indicar la estrategia elegida por riesgo y su coste en tiempo | Abierto |
| RG-04 | Supervisión y gestión sin disparadores medibles y sin evidencia | Reducción, supervisión y gestión (contingencia + disparador) | M | Definir umbrales y registrar la supervisión en los daily | Abierto |
| RG-05 | Escala sin definir y valoraciones no justificadas | Probabilidad × consecuencia con criterio / priorización explícita | M | Definir los niveles y fijar una línea de corte. Revisar R12, R8 y R10 | Abierto |
| RG-06 | Inconsistencias menores con otros documentos de la wiki | Consistente | L | Alinear R10 y R8 con la retrospectiva y los daily | Abierto |
 
### C. Estimación y métricas
 
| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| EM-01 | No hay estimación cuantitativa de esfuerzo | Tamaño con VE, esfuerzo = tamaño / productividad | G | Estimar en horas, personas-día o puntos, con productividad explícita | Abierto |
| EM-02 | Tallas sin definición ni calibración | Estimación con datos históricos | M | Definir cada talla (en horas) y recalibrarla con los sprints hechos | Abierto |
| EM-03 | Sin datos históricos, velocidad ni reestimación | Datos históricos / estimaciones actualizadas | M | Registrar historias y esfuerzo planificado frente a real por sprint | Abierto |
| EM-04 | Ámbito y recursos sin definir | Ámbito definido y recursos descritos | M | Definir el alcance del MVP y describir recursos: horas por persona, herramientas, servicios externos y fecha de entrega | Abierto |
| EM-05 | Métricas de producto y proceso ausentes | Métricas del software | M | Fijar un conjunto mínimo de métricas con valores objetivo | Abierto |
 
### D. Planificación
 
| ID | Nombre | Criterio incumplido | Sev. | Acción propuesta | Estado |
|---|---|---|---|---|---|
| PL-01 | Sprint 4 sobredimensionado | Plan abarcable / compromiso ajustado a la capacidad | G | Recortar el compromiso según la velocidad real y dejar un colchón | Abierto |
| PL-02 | Acciones de la retrospectiva del sprint 3 no aplicadas al sprint 4 | Seguimiento de mejora | M | Incorporar al plan contingencia, división de historias grandes y dependencias | Abierto |
| PL-03 | Objetivos poco medibles y definición de hecho ausente en los sprints 3 y 4 | Objetivos medibles y criterios de éxito | M | Definir un objetivo evaluable y recuperar la definición de hecho | Abierto |
| PL-04 | Sprint 4 inconsistente con el backlog y con las reviews | Consistente / trazable | M | Alinear alcance, historias y criterios con el backlog y los resultados reales | Abierto |
| PL-05 | Las reviews no reconcilian lo planificado con lo entregado | Seguimiento: progreso real frente a planificado | M | Hacer una tabla por sprint de historias planificadas, hechas y parciales | Abierto |
| PL-06 | Acciones de retrospectiva sin responsable, fecha ni indicador | Mejora del proceso | M | Asignar responsable, fecha e indicador a cada acción | Abierto |
 
---
 
## 2. Descripción detallada de los errores
 
## A. Historias de usuario
 
### HU-01 (G) · Tamaño y prioridad incoherentes
 
La tabla final de `Backlog.md` no coincide con lo que dice cada historia. De las 59 historias que aparecen en la tabla, 35 tienen discrepancias: 23 de tamaño y 25 de prioridad.
 
- 8.1 es "prioridad alta" en su texto y "Baja" en la tabla.
- 11.1 es "tamaño grande" en su texto y "Pequeño" en la tabla.
- 2.1 pasa de "grande/media" a "Muy grande/Baja".
- 5.4 pasa de "mediano/alta" a "Pequeño/Media".
- 4.6 y 4.7 no aparecen en la tabla y tienen prioridad "media-alta", que no existe en la escala.
Sin una prioridad fiable no se pueden elegir bien las historias de cada sprint. Por ejemplo, H8.2 y H8.3 son "alta" en el texto y no se planifican, mientras que H1.10, H1.11 y H3.3, que son "baja" en la tabla, entran en el Sprint 4.
 
### HU-02 (G) · Mismo ID, distinta historia
 
El backlog y las planificaciones de sprint usan los mismos identificadores para historias distintas, o criterios de aceptación distintos para la misma historia.
 
- **H3.2:** en el Sprint 2 es "Perfil de usuario" (biografía, que en el backlog es la 4.3). En el Sprint 3 es "Filmografía/Bibliografía".
- **H2.4:** el backlog la define como "Obras similares". El Sprint 2 y el daily del 26/10 la usan para "Autocompletado" (en el backlog es la 2.8). El Sprint 4 vuelve a usarla como "Obras similares".
- **H1.12 y H1.13:** son dos historias en el backlog y una sola (H1.12) en el Sprint 2.
- **H6.2:** el criterio de sesión en el backlog es "según la configuración elegida", pero en el Sprint 2 es "se mantiene durante la navegación", y se añade un criterio de registro que no es de inicio de sesión.
- **H11.1:** el Sprint 2 añade criterios de móvil y de ficha que el backlog no tiene.
- **H2.9:** "Ampliación del catálogo" no existe en el backlog.
- **H4.2, H4.4 y H4.5:** en el Sprint 3 tienen criterios distintos a los del backlog. En H4.2 aparece "la imagen aparece junto a mis publicaciones", en H4.4 "cumple las restricciones de tamaño definidas" y H4.5 no incluye "cambios de estado".
Hay dos fuentes de verdad, así que no se puede trazar qué historia está hecha ni qué pruebas le corresponden. Un ejemplo es que H4.5 se da por cerrada en el Sprint 3 y se replanifica en el Sprint 4 con "cambios de estado".
 
### HU-03 (M) · Historias solapadas
 
- 1.6 (pública o privada, modificar) y 5.4 (configurar cada lista como pública o privada, modificar) piden lo mismo.
- 2.5 y 10.1 recomiendan según valoraciones.
- 9.1 (insignias) y 9.3 (logros desbloqueados) son casi lo mismo.
- 1.2 define la estructura de la ficha, y 11.1 (criterio 4) y 11.2 (criterio 4) vuelven a pedirla.
- 3.1 (criterio 4, obras relacionadas) invade 3.2.
- Las notificaciones aparecen en 5.2 y en el criterio 4 de 7.3 y 7.4.
- 1.10, 10.5 y 10.8 son análisis de la actividad del usuario.
Esto provoca doble estimación y riesgo de implementaciones incoherentes.
 
### HU-04 (M) · Estados de una obra sin definir
 
1.1 solo menciona "quiero ver/leer" y "visto/leído", y su criterio 3 dice que el estado "es diferente según el tipo de obra" sin decir cuáles. La lista de estados solo existe en el plan del Sprint 1. 1.9 añade "Abandonado" a una funcionalidad ya existente, según su propia justificación, pero se declara independiente. 1.8 registra progreso, lo que implica un estado "en curso" que ninguna historia define.
 
El error de diseño del Sprint 1 (guardar el estado en la obra y no en la relación usuario-obra) tuvo su origen en esta falta de definición.
 
### HU-05 (M) · Ficha técnica sin campos concretos
 
En 1.2, "los metadatos relevantes según el tipo de obra" no se puede verificar: no se dice qué campos tiene un libro, una película, una serie, un videojuego o un disco. Los criterios 3 y 4 mezclan la ficha con el estado (1.1) y la valoración (1.4). 11.2 vuelve a pedir "una estructura uniforme" para las fichas sin definirla.
 
### HU-06 (M) · Registro de progreso incompleto y con criterios cambiantes
 
La historia 1.8 quiere "saber cuánto me falta", pero ningún criterio muestra lo que falta, solo lo registrado. Los criterios han cambiado por el camino:
 
- La Review 3 entrega progreso también para películas, algo que "no figuraba en los criterios".
- El Sprint 4 cambia "episodios vistos" por "temporada actual" y "capítulo actual".
- Se necesitan totales (páginas, episodios) que 1.2 no exige en la ficha.
### HU-07 (M) · Estadísticas y exportación mal acotadas
 
- **1.10:** solo cuenta películas y libros, aunque la plataforma tiene cinco tipos de obra (los daily del 14/11 sí planifican series y videojuegos). "Géneros favoritos" no tiene regla (¿por número de obras o por nota?) y no se dice qué periodos de filtrado existen.
- **1.11:** habla de "datos personales" pero solo exporta listas, valoraciones y reseñas, no estados ni progreso. No indica el formato y "el archivo se descarga correctamente" no es un criterio medible.
### HU-08 (M) · Criterios de búsqueda y recomendación no verificables
 
- **2.2:** "resultados relevantes" no define relevancia ni orden.
- **2.4:** "criterios de similitud" no se define, y "al menos cinco" puede ser imposible con un catálogo pequeño.
- **2.5:** "se consideran mis valoraciones" no dice qué resultado esperar, y la "página principal" no existe en ninguna historia.
- **2.7:** "tendencias del momento" no define la métrica ni el periodo.
Si no se puede diseñar una prueba, el requisito es problemático.
 
### HU-09 (M) · Criterios contradictorios entre historias relacionadas
 
- **2.6 y 1.6:** el criterio 4 de 2.6 ("las listas muestran una descripción") depende de un campo que 1.6 no crea. La Review 3 lo confirma: el equipo tuvo que añadir la descripción como "mejora adicional".
- **3.2:** el título pide la trayectoria "completa" y el criterio 2 dice "se muestran las tres obras más relevantes" (sin definir "relevantes"). Además, el criterio 4 de 3.1 ya muestra obras relacionadas.
### HU-10 (M) · Gestión de cuenta incompleta
 
- **6.1:** no define contraseña ni nombre de usuario, aunque 6.2 inicia sesión con "correo y contraseña" y 4.6 elige el usuario "durante el registro".
- **6.2 (criterio 4):** "según la configuración elegida" no corresponde a ningún criterio ni historia.
- **6.3:** "fecha de caducidad" sin valor.
- **Cierre de sesión:** no tiene historia. El daily del 25/10 muestra que se implementaron protección de contraseñas, cierre de sesión, sesión persistente y bloqueo de cuentas sin verificar, comportamientos que no están en ningún criterio.
- **4.7:** "todos los datos asociados dejan de estar disponibles" no aclara qué pasa con reseñas, comentarios y listas públicas que ven otros usuarios, ni si es borrado o anonimización. Tampoco fija plazos ni dice cómo se relaciona con la exportación 1.11.
### HU-11 (M) · Modelo social y de privacidad confuso
 
- 5.3 ofrece "solo para amigos", que depende de 7.2, mientras 7.1 introduce "seguir" sin explicar cómo conviven ambas relaciones.
- 7.2 habla de "contenido restringido" sin decir cuál, y 5.4 solo tiene público y privado.
- 7.5 comparte "listas públicas", pero sus criterios hablan de "usuarios autorizados" y de "mantener la privacidad", lo cual contradice una lista pública.
### HU-12 (M) · Roles y moderación sin historias
 
Existen "autor" (1.3), "moderador" (8.1) y "administrador" (8.3), pero ninguna historia define cómo una cuenta obtiene ese rol. La Review 3 muestra que los roles de usuario y moderador se implementaron dentro de H8.1 sin historia propia.
 
8.2 dice que "los moderadores pueden revisarlo" sin describir qué hacen con el reporte (retirar contenido, descartarlo, avisar al reportado).
 
### HU-13 (M) · Asistente inteligente no verificable
 
Criterios como "el asistente interpreta la petición" (10.3), "compara las opciones" (10.7) o "géneros poco frecuentes" (10.6) no se pueden comprobar. No se define qué hacer si la consulta es ambigua, no tiene relación con obras o no hay resultados (solo 10.1 lo menciona, de forma vaga).
 
### HU-14 (M) · Historias demasiado grandes y justificaciones contradictorias
 
La tabla marca como "Muy grande" 2.1, 2.5, 10.1, 10.3, 10.4, 10.6 y 10.9, que no caben en una iteración de 2 a 6 semanas. En 1.2, 1.3, 1.8 y 1.10 el tamaño dice "grande" pero el criterio S de INVEST afirma que son "lo suficientemente pequeñas". 11.1 admite que "podría dividirse".
 
La experiencia lo confirma: en el Sprint 3 las tres historias grandes (H1.3, H1.8 y H1.10) quedaron incompletas.
 
### HU-15 (L) · Criterios ambiguos
 
- **1.4:** "entre 0 y 5 estrellas" no aclara si 0 significa "sin valorar" y si se admiten medias estrellas.
- **3.3:** "los enlaces funcionan correctamente".
- **4.2 y 4.4:** "se muestra correctamente", sin formato ni tamaño de imagen.
- **4.3:** "existe un límite de caracteres" sin valor.
- **4.5:** "cuando corresponda" e "información suficiente".
- **5.1:** "categorías configurables" sin nombrarlas. Sus criterios 3 y 4 (guardado automático y persistencia) se solapan.
## B. Gestión de riesgos
 
### RG-01 (G) · Riesgos críticos materializados sin medidas efectivas
 
R1, R4 y R7 son "críticos" (9) y los dos primeros ya se han materializado más de una vez. Las medidas previstas no llegan al plan siguiente.
 
- **R7:** un miembro se quedó sin portátil en los sprints 2 y 3. La retrospectiva dice "seguimos sin un plan de contingencia" y que su trabajo no se reasignó. Aun así, el Sprint 4 asigna a la Persona 5 H1.3, H8.1 y el diseño sin ninguna alternativa. La medida del documento ("acordar de antemano una alternativa") no indica quién, qué ni cuándo.
- **R1:** la medida "ajustar la carga a la capacidad real" no se refleja en el Sprint 4, que tiene más trabajo que el Sprint 3 (ver PL-01).
La guía exige que no queden riesgos altos o intolerables sin tratar y que la elaboración esté dirigida por riesgos.
 
### RG-02 (M) · Sin responsable, fechas ni historial
 
Ningún riesgo tiene responsable asignado. No hay fechas de revisión ni registro de cambios: el documento cuenta que se subieron o bajaron probabilidades, pero la tabla solo muestra los valores actuales. El apartado 4 ("Planificación temporal") describe una supervisión continua sin calendario.
 
### RG-03 (M) · Sin decisión por riesgo
 
No se indica si cada riesgo se evita, se controla, se asume o se transfiere. Por ejemplo, R8 (rendimiento) podría asumirse hasta que crezca el catálogo y R7 podría transferirse a un equipo compartido. La teoría pide evaluar las alternativas teniendo en cuenta el aumento de costes y tiempo.
 
### RG-04 (M) · Supervisión y gestión sin disparadores
 
Casi todas las medidas son genéricas y no tienen umbral:
 
- R1: "comparamos el avance con lo planificado", sin indicar con qué métrica.
- R8: "medir cuánto tardan las búsquedas", sin tiempo objetivo.
- R4: "comprobar que la aplicación arranca".
- R7: "preguntar en cada daily si alguien tiene problemas de recursos".
Además, la supervisión no está evidenciada: ninguno de los 16 daily recoge impedimentos y el problema del portátil no aparece en ninguno.
 
### RG-05 (M) · Escala sin definir y valoraciones no justificadas
 
La escala de 1 a 3 no define qué significa cada nivel (por ejemplo, qué retraso es impacto "alto"). No hay línea de corte: el daily vigila R1, R4, R7 y R10, pero R10 (gravedad 6) no se distingue de R2, R5 y R11 (también 6), que no se vigilan.
 
Algunas valoraciones no coinciden con la evidencia:
 
- **R12 ("Baja"):** el propio texto dice que hubo incidencias con roles en el Sprint 3. Además, el daily del 18/11 pide "revisar que las obras pendientes o rechazadas no aparezcan en el buscador".
- **R3:** se baja por un solo sprint de experiencia.
### RG-06 (L) · Inconsistencias menores
 
- R10 dice que en el Sprint 3 faltaban criterios en H1.3, H1.8 y H8.1, pero la retrospectiva solo cita H1.3 y H8.1.
- R8 dice que la optimización prevista en el Sprint 3 "no se hizo", pero el daily del 18/11 describe consultas reducidas, límite de 50 resultados y espera de 250 ms.
## C. Estimación y métricas
 
### EM-01 (G) · No hay estimación cuantitativa de esfuerzo
 
La wiki solo usa tallas cualitativas (muy pequeño, pequeño, mediano, grande, muy grande). No hay horas, personas-día ni puntos de historia, ni valor esperado (optimista, probable, pesimista), ni productividad. Sin esos datos no se puede calcular esfuerzo, duración ni capacidad por sprint.
 
Las retrospectivas del Sprint 1 y 2 hablan de "estimación del esfuerzo" y "estimaciones poco precisas" sin ninguna cifra. La guía parte de esfuerzo = tamaño / productividad.
 
### EM-02 (M) · Tallas sin definición ni calibración
 
La escala no se corresponde con ninguna unidad de esfuerzo, y el backlog y su tabla no coinciden (HU-01). Tampoco está calibrada: H1.2 era "grande" y se entregó en el Sprint 1, mientras que las tres grandes del Sprint 3 quedaron incompletas. Aun así, el Sprint 4 vuelve a incluir historias grandes (H1.10, H3.3 y el resto de H1.8).
 
### EM-03 (M) · Sin datos históricos ni reestimación
 
Tras tres sprints no hay velocidad registrada. Solo el Sprint 3 cuantifica lo planificado y lo entregado (7 de 10 completas, 2 parciales y 1 sin terminar). En el Sprint 2 la Review no informa de 11 de las 13 historias planificadas. No se reestima el backlog tras cada sprint y el Sprint 4 no se apoya en el rendimiento anterior.
 
### EM-04 (M) · Ámbito y recursos sin definir
 
No hay un documento con el alcance del MVP: el Sprint 2 lo declara "producto mínimo viable" y el Sprint 4 busca "la plataforma prácticamente terminada" sin definir qué es eso. Tampoco se describen los recursos:
 
- Disponibilidad y horas por persona (la Persona 5 no podía desarrollar).
- Herramientas: Eclipse, Neon, pgAdmin, GitHub.
- Servicios externos.
- Fecha de entrega final.
### EM-05 (M) · Métricas de producto y proceso ausentes
 
Los datos son cualitativos ("la cobertura es inferior a la prevista", "resultados satisfactorios", "optimización de consultas") y no hay cifras. Faltan:
 
- Cobertura de pruebas y número de pruebas.
- Defectos por sprint.
- Tiempos de carga y búsqueda (las pruebas con Lighthouse no tienen objetivo).
- Velocidad.
- Porcentaje de criterios de aceptación cumplidos.
Un conjunto mínimo razonable sería velocidad, historias completadas, defectos abiertos, cobertura y tiempo de respuesta del buscador.
 
## D. Planificación
 
### PL-01 (G) · Sprint 4 sobredimensionado
 
El plan toca 14 historias (11 listadas más H2.4, H3.3 y H1.3 en el reparto), más la mejora visual, y declara 12 como terminadas. El Sprint 3 cerró 7 de 10 con una persona sin poder programar.
 
- La Persona 1 recibe H1.8, H1.10 (ambas grandes) y H1.11 (mediana).
- La Persona 3 recibe solo H2.4 y H3.3, de prioridad media y baja.
- No se indica capacidad por persona ni colchón.
- No hay contingencia para la persona que ya perdió dos sprints.
La retrospectiva del Sprint 3 ya había marcado "ajustar el compromiso" como acción de mejora.
 
### PL-02 (M) · Acciones de la retrospectiva del Sprint 3 no aplicadas
 
- **Plan de contingencia de equipos:** no aparece.
- **Dividir las historias grandes:** H1.10 se lista como cuatro viñetas, pero no hay entregables ni estimaciones separados. H1.8 y H3.3 no se dividen.
- **Dependencias:** las secciones "Dependencias" de los planes 1 a 3 desaparecen en el Sprint 4.
- **Cronograma completo con hitos:** se incluye, pero es genérico (diseño, backend, frontend, testing) y no revisa los criterios en cada daily.
- **Cerrar primero lo pendiente:** se incluye H1.3, H1.8 y H8.1, pero se añaden muchas historias nuevas.
- **Ajustar compromiso:** no se hace (PL-01).
### PL-03 (M) · Objetivos poco medibles y definición de hecho ausente
 
El objetivo del Sprint 4 ("dejando la plataforma prácticamente terminada") no es evaluable. Los planes de los sprints 3 y 4 no tienen "Definición de hecho". El Sprint 3 tampoco tiene "Resultado esperado". Ambos apartados sí estaban en los sprints 1 y 2, por lo que se han perdido por el camino.
 
El "Resultado esperado" del Sprint 4 lista H1.1 (que no está en el alcance y se cerró en el Sprint 2) y omite H1.3 (que sí se asigna).
 
### PL-04 (M) · Sprint 4 inconsistente con el backlog y con las reviews
 
- **H1.1:** aparece como resultado esperado sin estar asignada, y la Persona 2 tiene un bloque "Estados" huérfano.
- **H1.8:** se listan como pendientes "páginas leídas" y otras tareas que la Review 3 da como hechas, y se cambia el alcance de series.
- **H1.10:** se reduce a cuatro criterios y se descarta sin decirlo la parte de series, videojuegos y panel visual.
- **H4.5:** se replanifica cuando la Review 3 la daba por completa.
- **H1.3:** se renombra "Editar obra enviada" y se añade "revalidación automática", que no está en ningún criterio.
- **Tarea suelta:** "Conectar la API" no pertenece a ninguna historia.
- **Importación automática del catálogo:** estaba en el Sprint 3, no se hizo y desaparece sin ninguna decisión.
- **Mejoras ya hechas:** "meter los géneros en la ficha" figura como pendiente, pero el daily del 18/11 la da por hecha.
### PL-05 (M) · Las reviews no reconcilian lo planificado con lo entregado
 
- **Sprint 1:** la Review dice que H1.4 se "ha comenzado", pero el daily del 14/10 la da por desarrollada, junto con H1.5 (con operaciones completas y límite de 200 palabras).
- **Sprint 2:** la Review da como completadas H1.4, H1.5 y H2.2, que son del Sprint 1. De las 13 historias planificadas solo nombra explícitamente H1.1 y, de forma parcial, H11.1. No informa de H6.1, H6.2, H3.2, H4.1, H1.6, H1.7, H1.9, H1.12, H2.3, H2.4 y H2.9, aunque los daily muestran que se trabajaron (25/10, 26/10, 28/10).
- **Sprint 3:** la Review dice que no se avanzó en Intro, obras recientes, géneros, estrellas, avatar, logotipo y rendimiento, pero el daily del 18/11 los lista como hechos. Sin fechas de sprint no se sabe a qué sprint pertenece ese daily. Además, la Review declara H4.2 y H4.4 completas "con todos sus criterios" sin mencionar "aparece junto a mis publicaciones" ni "restricciones de tamaño".
- **Retrospectiva 2:** dice que se completó "la mayor parte de los objetivos", pero la Review 2 deja pendiente casi toda la mejora de interfaz.
### PL-06 (M) · Acciones de retrospectiva sin responsable, fecha ni indicador
 
Las acciones de mejora no tienen persona asignada, fecha ni forma de comprobar su cumplimiento. Las del Sprint 2 (revisar dependencias, mejorar estimaciones) reaparecen como fallos en el Sprint 3. La propia retrospectiva 3 reconoce que "un problema que se repite necesita un plan concreto, no basta con anotarlo".
 
---
 
## 3. Decisión propuesta
 
**Aceptar con cambios.** Hay cinco problemas graves, entre ellos la falta de estimación (EM-01) y un backlog con criterios contradictorios (HU-01 y HU-02). Además, el Sprint 4 repite los errores de sobrecarga que el propio equipo ya reconoció (PL-01, RG-01).
 
El proyecto no está mal ejecutado: hay entregas reales, pruebas y buena autocrítica en las retrospectivas. Los problemas son de documentación, estimación y planificación, y se pueden corregir sin rehacer el producto. Por eso corresponde aceptar con cambios: se fija esta lista de acciones y se corrige sin nueva RTF.
 
**Seguimiento:** el jefe de revisión comprueba cada punto de la lista, empezando por los 5 graves y la actualización del backlog, antes de empezar el Sprint 4.
 
---
 
## 5. Registro de revisión (firmas)
 
| Asistente | Rol | Conformidad con la decisión | Firma |
|---|---|---|---|
| Andrés Cuevas | Revisor | |     |
| Alberto Vilches | Revisor | |     |
|  | Participante del grupo 2 | |     |
|  | Participante del grupo 2 | |     |
|  | Participante del grupo 2 | |     |
 