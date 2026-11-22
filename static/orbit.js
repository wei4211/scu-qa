(() => {
  const canvas = document.querySelector(".hero-art");
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const hero = canvas.parentElement;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const tau = 2 * Math.PI;
  const pointer = { x: 0, y: 0 };
  const tilt = { x: 0, y: 0 };
  let width = 0;
  let height = 0;
  let frame = 0;
  let time = 0;
  let previous = 0;

  function draw() {
    ctx.clearRect(0, 0, width, height);
    ctx.save();
    ctx.translate(width * .52, height * .51);
    const radius = Math.min(width * .285, height * .31);

    const pitch = .67 + tilt.y * .2;
    const yaw = tilt.x * .22;
    const roll = -.38 + tilt.x * .10;
    const cosPitch = Math.cos(pitch);
    const sinPitch = Math.sin(pitch);
    const cosYaw = Math.cos(yaw);
    const sinYaw = Math.sin(yaw);
    const cosRoll = Math.cos(roll);
    const sinRoll = Math.sin(roll);

    function project(angle, twist, ring = 1, tube = .165) {
      const r = ring + tube * Math.cos(twist);
      const x = r * Math.cos(angle);
      const y = r * Math.sin(angle);
      const z = tube * Math.sin(twist);
      const pitchedY = y * cosPitch - z * sinPitch;
      const pitchedZ = y * sinPitch + z * cosPitch;
      const yawedX = x * cosYaw + pitchedZ * sinYaw;
      const depth = pitchedZ * cosYaw - x * sinYaw;
      const scale = radius * 4.8 / (4.8 - depth);
      return [
        (yawedX * cosRoll - pitchedY * sinRoll) * scale,
        (yawedX * sinRoll + pitchedY * cosRoll) * scale,
      ];
    }

    function trace(style, lineWidth, start, length, steps, ring, tube, phase, turns) {
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const angle = start + i / steps * length;
        const twist = phase + angle * turns;
        const [x, y] = project(angle, twist, ring, tube);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = style;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }

    // Two guide orbits sit outside the moving filaments.
    trace("#5152ac50", 1, 0, tau, 84, 1.32, 0, 0, 0);
    trace("#5152ac35", 1, 0, tau, 84, 1.46, 0, 0, 0);
    ctx.beginPath();
    for (let i = 0; i < 60; i++) {
      const angle = i * tau / 60;
      ctx.moveTo(...project(angle, 0, 1.43, 0));
      ctx.lineTo(...project(angle, 0, i % 5 === 0 ? 1.49 : 1.46, 0));
    }
    ctx.strokeStyle = "#4e62aa60";
    ctx.lineWidth = 1;
    ctx.stroke();

    const gradient = ctx.createLinearGradient(-radius, radius, radius, -radius);
    gradient.addColorStop(0, "#873bc5");
    gradient.addColorStop(.43, "#5149d1");
    gradient.addColorStop(.8, "#1384cd");
    gradient.addColorStop(1, "#087498");
    ctx.lineCap = "round";

    // A soft core sits underneath the individual strands.
    ctx.globalAlpha = .20;
    ctx.shadowColor = "#6a8afa";
    ctx.shadowBlur = 19;
    trace(gradient, 9, 0, tau, 96, 1, 0, 0, 0);
    ctx.shadowBlur = 0;
    const count = width < 400 ? 24 : 34;
    for (let i = 0; i < count; i++) {
      ctx.globalAlpha = i % 7 === 0 ? .66 : .28;
      const phase = i * tau / count + time * .48;
      trace(gradient, i % 7 === 0 ? 1.3 : .78, 0, tau, 100, 1, .165, phase, 2);
    }

    // Bright arcs and nodes travel around the halo at different speeds.
    ctx.globalAlpha = .88;
    for (let i = 0; i < 4; i++) {
      const angle = time * (.19 + i * .035) + i * tau / 4;
      const ring = i % 2 ? 1.32 : 1.08;
      trace(gradient, i % 2 ? 1.2 : 2.3, angle - .23, .23, 12, ring, 0, 0, 0);
      const [x, y] = project(angle, 0, ring, 0);
      ctx.fillStyle = i % 2 ? "#6244d4" : "#007baf";
      ctx.shadowColor = ctx.fillStyle;
      ctx.shadowBlur = 10;
      ctx.beginPath();
      ctx.arc(x, y, i % 2 ? 2 : 3, 0, tau);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    ctx.restore();
  }

  function animate(now) {
    const delta = previous ? Math.min(now - previous, 50) : 0;
    previous = now;
    time += delta / 1000;
    tilt.x += (pointer.x - tilt.x) * .065;
    tilt.y += (pointer.y - tilt.y) * .065;
    draw();
    frame = requestAnimationFrame(animate);
  }

  function update() {
    cancelAnimationFrame(frame);
    previous = 0;
    const bounds = canvas.getBoundingClientRect();
    width = bounds.width;
    height = bounds.height;
    if (!width || !height || document.hidden) return;

    const scale = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    ctx.setTransform(scale, 0, 0, scale, 0, 0);

    if (reducedMotion.matches) {
      tilt.x = tilt.y = 0;
      draw();
      return;
    }
    frame = requestAnimationFrame(animate);
  }

  hero.addEventListener("pointermove", event => {
    if (event.pointerType !== "mouse" || reducedMotion.matches) return;
    const bounds = hero.getBoundingClientRect();
    pointer.x = (event.clientX - bounds.left) / bounds.width * 2 - 1;
    pointer.y = (event.clientY - bounds.top) / bounds.height * 2 - 1;
  });
  hero.addEventListener("pointerleave", () => { pointer.x = pointer.y = 0; });
  new ResizeObserver(update).observe(canvas);
  reducedMotion.addEventListener("change", update);
  document.addEventListener("visibilitychange", update);
})();
