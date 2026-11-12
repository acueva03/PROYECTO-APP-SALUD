# Pruebas manuales antes de cada entrega

Lista que pide el riesgo 3.18.2. Se hace con `python3 backend/seed.py` (usuarios `maria` y `alberto`, contraseña `1234`),
la pantalla del paciente en un móvil (o el navegador en modo móvil) y el panel del supervisor en otra ventana.
Marca cada punto; si alguno falla, no se entrega.

## 1. Botón SOS (sos.js)

- [ ] Pulsar SOS con conexión: «Aviso enviado. Tu supervisor ha sido notificado.» y el panel del supervisor suena.
- [ ] Apagar el Wi-Fi y pulsar SOS: mensaje en rojo «Error de conexión… LLAME AL 112» y botón «📞 Llamar al 112» que abre el marcador.
- [ ] Cerrar sesión en otra pestaña y pulsar SOS: dice que la sesión ha caducado (no «sin conexión»).

## 2. Alarmas

- [ ] Crear una alarma «Solo una vez», otra «Todos los días» y otra «Elegir los días…»: aparecen en «Alarmas activas».
- [ ] Crear dos alarmas con dosis a la misma hora: salen **dos** avisos, cada uno con su dosis y sus botones (3.16).
- [ ] Pulsar «Ya lo hice» en una: la otra sigue en pantalla y el supervisor la sigue viendo sin confirmar.
- [ ] Pulsar «Deshacer» antes de 1 minuto: el aviso vuelve (3.16.3).
- [ ] «Posponer 10 minutos»: el aviso vuelve a los 10 minutos.

## 3. Eliminar y recuperar (3.14)

- [x] «Eliminar» en una alarma con dosis: el diálogo dice el nombre y la dosis, y el botón grande es «Desactivar».
- [x] Eliminarla: aparece «Deshacer»; pulsarlo la recupera.
- [x] Eliminarla otra vez y recuperarla desde «Alarmas eliminadas».
- [x] Pulsar Esc o «Cancelar» en el diálogo: no se borra nada.
- [x] En el panel del supervisor (pestaña Medicación): aparecen las alarmas eliminadas por el paciente y el botón «Restaurar alarma» las devuelve a las activas (3.14.3).

## 4. Pantalla abierta (3.12, prueba 3.12.2 en móvil real)

- [x] Se ve el aviso «Mantén esta pantalla abierta y con el volumen subido» y el estado de la pantalla.
- [x] Con una alarma a 2 minutos: bloquear la pantalla, minimizar el navegador y cambiar de aplicación. Anotar si suena, cuándo y qué se ve al volver (comprobado: suena al recuperar el foco/desbloquear gracias a `visibilitychange`).
- [x] Cerrar la página con una alarma pendiente: a los 15 minutos el supervisor la ve «(no ha sonado en su móvil)».

## 5. Accesibilidad (3.25)

- [x] «Ajustes de letra, contraste y voz»: letra muy grande, alto contraste y voz. Recargar: se mantienen.
- [x] Con voz activada, el aviso de alarma se lee en voz alta y «🔊 Leer en voz alta» lo repite.
- [x] Navegar con el teclado (Tab): el foco siempre se ve y el aviso de alarma recibe el foco al aparecer.
- [x] Con letra muy grande, en el móvil no hay que desplazarse a los lados.

## 6. Errores (3.18)

- [x] Consola del navegador (F12) sin errores en rojo durante el uso normal.
- [x] `npx eslint frontend/static` sin errores y los tests de `backend` en verde.
