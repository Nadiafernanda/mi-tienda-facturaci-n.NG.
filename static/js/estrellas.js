(function () {
  const canvas = document.getElementById("estrellas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const colores = ["#19f0ff", "#ff3df2", "#b9ff3d", "#9b6bff", "#ffffff"];
  const reducir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let estrellas = [];
  let ancho = 0,
    alto = 0,
    mx = 0,
    my = 0;

  function iniciar() {
    const dpr = window.devicePixelRatio || 1;
    ancho = window.innerWidth;
    alto = window.innerHeight;
    mx = ancho / 2;
    my = alto / 2;
    canvas.width = ancho * dpr;
    canvas.height = alto * dpr;
    canvas.style.width = ancho + "px";
    canvas.style.height = alto + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const cantidad = Math.min(140, Math.floor((ancho * alto) / 9000));
    estrellas = Array.from({ length: cantidad }, () => ({
      x: Math.random() * ancho,
      y: Math.random() * alto,
      r: Math.random() * 2.2 + 1,
      color: colores[Math.floor(Math.random() * colores.length)],
      fase: Math.random() * Math.PI * 2,
      vel: Math.random() * 0.02 + 0.008,
      prof: Math.random() * 0.04 + 0.01,
    }));
    if (reducir) dibujar();
  }

  function dibujar() {
    ctx.clearRect(0, 0, ancho, alto);
    for (const e of estrellas) {
      e.fase += e.vel;
      const brillo = 0.5 + 0.5 * Math.abs(Math.sin(e.fase));
      const x = e.x + (mx - ancho / 2) * e.prof;
      const y = e.y + (my - alto / 2) * e.prof;
      ctx.globalAlpha = brillo;
      ctx.fillStyle = e.color;
      ctx.shadowColor = e.color;
      ctx.shadowBlur = 18;
      ctx.beginPath();
      ctx.arc(x, y, e.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
    if (!reducir) requestAnimationFrame(dibujar);
  }

  window.addEventListener("mousemove", (ev) => {
    mx = ev.clientX;
    my = ev.clientY;
  });
  window.addEventListener("resize", iniciar);
  iniciar();
  if (!reducir) dibujar();
})();
