const USER_ID = 2;  // provisional hasta que haya login

document.getElementById('boton-sos').addEventListener('click', async () => {
    // 3.1.1 Reducción: Timeout estricto de 5 segundos
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); 

    try {
        const respuesta = await fetch('/api/sos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!respuesta.ok) throw new Error('Error del servidor');
        alert('Aviso enviado. Tu supervisor ha sido notificado.');
    } catch (error) {
        clearTimeout(timeoutId);
        // 3.1.3 Gestión: Mensaje de emergencia local
        alert('Error de conexión: LLAME AL 112');
    }
});