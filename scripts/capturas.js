/* Lleva la aplicación al estado que se quiere retratar.
 *
 * Se evalúa DENTRO de la página. El visor se alimenta de un MJPEG —una
 * respuesta que no termina nunca— así que la página jamás queda «cargada» y
 * las esperas tienen que ser de tiempo real, no de tiempo virtual.
 */
(() => {
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
  const $ = (id) => document.getElementById(id)

  async function hasta(fn, ms = 60000, cada = 200) {
    const fin = Date.now() + ms
    for (;;) {
      let v
      try { v = fn() } catch (e) { v = null }
      if (v) return v
      if (Date.now() > fin) throw new Error('se agotó la espera')
      await esperar(cada)
    }
  }

  const ESCENAS = {
    async ppe(op) {
      const sel = await hasta(() => {
        const s = $('videoSelect')
        return s && s.options.length && s.options[0].value ? s : null
      })
      const re = new RegExp(op.video || '.', 'i')
      const elegida = [...sel.options].find((o) => re.test(o.value))
      if (!elegida) throw new Error('ningún video casa con ' + op.video)
      sel.value = elegida.value
      sel.dispatchEvent(new Event('change', { bubbles: true }))
      await esperar(1200)
      $('startBtn').click()
      await hasta(() => $('stream') && $('stream').naturalWidth > 0, 120000)
      // Un panel de personas vacío no enseña nada: se espera a que haya alguien.
      await hasta(() => $('checkList') && $('checkList').children.length > 0,
        90000).catch(() => {})
      await esperar((op.segs || 20) * 1000)
    },
  }

  window.montar = async (nombre, op) => {
    const fn = ESCENAS[nombre]
    if (!fn) throw new Error('escena desconocida: ' + nombre)
    /* Una captura anterior pudo dejar el procesador en marcha; entonces
       /api/start responde con error, el stream nunca recibe src, y la espera
       se agota sin decir por qué. Se para siempre antes de empezar. */
    await fetch('/api/stop', { method: 'POST' }).catch(() => {})
    await esperar(1500)
    await fn(op || {})
    await esperar(1200)
    return 'ok'
  }
})()
