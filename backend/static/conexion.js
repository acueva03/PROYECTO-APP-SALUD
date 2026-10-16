const USER_ID = 2;  // provisional hasta que haya login
const botonSOS = document.getElementById('boton-sos');

botonSOS.addEventListener('click', async () => {
    botonSOS.disabled = true;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
        const respuesta = await fetch('/api/sos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID }),
            signal: controller.signal
        });
        if (!respuesta.ok) throw new Error('Error del servidor');
        alert('Aviso enviado. Tu supervisor ha sido notificado.');
    } catch (error) {
        alert('Error de conexión: LLAME AL 112');
    } finally {
        clearTimeout(timeoutId);
        botonSOS.disabled = false;
    }
});