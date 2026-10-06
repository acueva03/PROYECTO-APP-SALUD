const USER_ID = 2;  // provisional hasta que haya login

document.getElementById('boton-sos').addEventListener('click', async () => {
    try {
        const respuesta = await fetch('/alerta', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID })
        });
        if (!respuesta.ok) throw new Error('Error del servidor');
        alert('Aviso enviado. Tu supervisor ha sido notificado.');
    } catch (error) {
        alert('No se pudo enviar el aviso. Inténtalo de nuevo.');
    }
});