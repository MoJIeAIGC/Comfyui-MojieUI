<!--<template>-->
<!--  <canvas id="neuro"></canvas>-->
<!--  <div class="canvas-mask"></div>-->
<!--</template>-->

<!--<script setup>-->
<!--import {onUnmounted} from "vue";-->

<!--setTimeout(() => {-->
<!--  const canvasEl = document.querySelector("canvas#neuro");-->


<!--  const pointer = {-->
<!--    x: 0,-->
<!--    y: 0,-->
<!--    tX: 0,-->
<!--    tY: 0,-->
<!--    index: 0,-->
<!--    refresh: 60 * 10 * 4 * 10-->
<!--  };-->


<!--  let uniforms;-->
<!--  const gl = initShader();-->

<!--  setupEvents();-->

<!--  resizeCanvas();-->
<!--  window.addEventListener("resize", resizeCanvas);-->

<!--  render();-->

<!--  function initShader() {-->
<!--    const vsSource = `      precision mediump float;-->

<!--      varying vec2 vUv;-->
<!--      attribute vec2 a_position;-->

<!--      void main() {-->
<!--          vUv = .5 * (a_position + 1.);-->
<!--          gl_Position = vec4(a_position, 0.0, 1.0);-->
<!--      }`-->
<!--    const fsSource = `precision mediump float;-->

<!--      varying vec2 vUv;-->
<!--      uniform float u_time;-->
<!--      uniform float u_ratio;-->
<!--      uniform vec2 u_pointer_position;-->
<!--      uniform float u_scroll_progress;-->

<!--      vec2 rotate(vec2 uv, float th) {-->
<!--          return mat2(cos(th), sin(th), -sin(th), cos(th)) * uv;-->
<!--      }-->

<!--      float neuro_shape(vec2 uv, float t, float p) {-->
<!--          vec2 sine_acc = vec2(0.);-->
<!--          vec2 res = vec2(0.);-->
<!--          float scale = 8.;-->

<!--          for (int j = 0; j < 15; j++) {-->
<!--              uv = rotate(uv, 1.);-->
<!--              sine_acc = rotate(sine_acc, 1.);-->
<!--              vec2 layer = uv * scale + float(j) + sine_acc - t;-->
<!--              sine_acc += sin(layer) + 2.4 * p;-->
<!--              res += (.5 + .5 * cos(layer)) / scale;-->
<!--              scale *= (1.2);-->
<!--          }-->
<!--          return res.x + res.y;-->
<!--      }-->

<!--      void main() {-->
<!--          vec2 uv = .5 * vUv;-->
<!--          uv.x *= u_ratio;-->

<!--          vec2 pointer = vUv - u_pointer_position;-->
<!--          pointer.x *= u_ratio;-->
<!--          float p = clamp(length(pointer), 0., 1.);-->
<!--          p = .5 * pow(1. - p, 2.);-->

<!--          float t = .001 * u_time;-->
<!--          vec3 color = vec3(0.);-->

<!--          float noise = neuro_shape(uv, t, p);-->

<!--          noise = 1.2 * pow(noise, 3.);-->
<!--          noise += pow(noise, 10.);-->
<!--          noise = max(.0, noise - .5);-->
<!--          noise *= (1. - length(vUv - .5));-->

<!--          color = normalize(vec3(.2, .5 + .4 * cos(3. * u_scroll_progress), .5 + .5 * sin(3. * u_scroll_progress)));-->

<!--          color = color * noise;-->

<!--          gl_FragColor = vec4(color, noise);-->
<!--      }`-->
<!--    const gl = canvasEl.getContext("webgl") || canvasEl.getContext("experimental-webgl");-->

<!--    if (!gl) {-->
<!--      alert("WebGL is not supported by your browser.");-->
<!--    }-->

<!--    function createShader(gl, sourceCode, type) {-->
<!--      const shader = gl.createShader(type);-->
<!--      gl.shaderSource(shader, sourceCode);-->
<!--      gl.compileShader(shader);-->
<!--      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {-->
<!--        console.error("An error occurred compiling the shaders: " + gl.getShaderInfoLog(shader));-->
<!--        gl.deleteShader(shader);-->
<!--        return null;-->
<!--      }-->

<!--      return shader;-->
<!--    }-->

<!--    const vertexShader = createShader(gl, vsSource, gl.VERTEX_SHADER);-->
<!--    const fragmentShader = createShader(gl, fsSource, gl.FRAGMENT_SHADER);-->

<!--    function createShaderProgram(gl, vertexShader, fragmentShader) {-->
<!--      const program = gl.createProgram();-->
<!--      gl.attachShader(program, vertexShader);-->
<!--      gl.attachShader(program, fragmentShader);-->
<!--      gl.linkProgram(program);-->

<!--      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {-->
<!--        console.error("Unable to initialize the shader program: " + gl.getProgramInfoLog(program));-->
<!--        return null;-->
<!--      }-->

<!--      return program;-->
<!--    }-->

<!--    const shaderProgram = createShaderProgram(gl, vertexShader, fragmentShader);-->
<!--    uniforms = getUniforms(shaderProgram);-->

<!--    function getUniforms(program) {-->
<!--      let uniforms = [];-->
<!--      let uniformCount = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);-->
<!--      for (let i = 0; i < uniformCount; i++) {-->
<!--        let uniformName = gl.getActiveUniform(program, i).name;-->
<!--        uniforms[uniformName] = gl.getUniformLocation(program, uniformName);-->
<!--      }-->
<!--      return uniforms;-->
<!--    }-->

<!--    const vertices = new Float32Array([-1., -1., 1., -1., -1., 1., 1., 1.]);-->

<!--    const vertexBuffer = gl.createBuffer();-->
<!--    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);-->
<!--    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);-->

<!--    gl.useProgram(shaderProgram);-->

<!--    const positionLocation = gl.getAttribLocation(shaderProgram, "a_position");-->
<!--    gl.enableVertexAttribArray(positionLocation);-->

<!--    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);-->
<!--    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);-->

<!--    return gl;-->
<!--  }-->

<!--  function render() {-->
<!--    const currentTime = performance.now();-->
<!--    pointer.index++-->
<!--    if (pointer.index > pointer.refresh) pointer.index = 0-->
<!--    pointer.x += (pointer.tX - pointer.x) * .2;-->
<!--    pointer.y += (pointer.tY - pointer.y) * .2;-->

<!--    gl.uniform1f(uniforms.u_time, currentTime);-->
<!--    gl.uniform2f(uniforms.u_pointer_position, pointer.x / window.innerWidth, 1 - pointer.y / window.innerHeight);-->
<!--    gl.uniform1f(uniforms.u_scroll_progress, (pointer.index / 6000).toFixed(1));-->
<!--    // gl.uniform1f(uniforms.u_scroll_progress,  1.6); //1紫 2绿 3蓝 4-->
<!--    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);-->
<!--    requestAnimationFrame(render);-->
<!--  }-->

<!--  function resizeCanvas() {-->
<!--    canvasEl.width = window.innerWidth;-->
<!--    canvasEl.height = window.innerHeight;-->
<!--    gl.uniform1f(uniforms.u_ratio, canvasEl.width / canvasEl.height);-->
<!--    gl.viewport(0, 0, canvasEl.width, canvasEl.height);-->
<!--  }-->

<!--  function setupEvents() {-->
<!--    window.addEventListener("pointermove", e => {-->
<!--      updateMousePosition(e.clientX, e.clientY);-->
<!--    });-->
<!--    window.addEventListener("touchmove", e => {-->
<!--      updateMousePosition(e.targetTouches[0].clientX, e.targetTouches[0].clientY);-->
<!--    });-->
<!--    window.addEventListener("click", e => {-->
<!--      updateMousePosition(e.clientX, e.clientY);-->
<!--    });-->

<!--    function updateMousePosition(eX, eY) {-->
<!--      pointer.tX = eX;-->
<!--      pointer.tY = eY;-->
<!--    }-->
<!--  }-->

<!--  onUnmounted(() => {-->
<!--    window.removeEventListener("pointermove", e => {-->
<!--    })-->
<!--    window.removeEventListener("click", e => {-->
<!--    })-->
<!--    window.removeEventListener("touchmove", e => {-->
<!--    })-->
<!--    window.removeEventListener("resize", resizeCanvas)-->
<!--  })-->
<!--}, 10)-->
<!--</script>-->

<!--<style lang="less" scoped>-->
<!--canvas#neuro {-->
<!--  position: fixed;-->
<!--  top: 0;-->
<!--  left: 0;-->
<!--  right: 0;-->
<!--  bottom: 0;-->
<!--  pointer-events: none;-->
<!--  opacity: .95;-->
<!--}-->

<!--.canvas-mask {-->
<!--  position: fixed;-->
<!--  top: 0;-->
<!--  left: 0;-->
<!--  right: 0;-->
<!--  bottom: 0;-->
<!--  z-index: 1;-->
<!--  background-color: #0a0b0e;-->
<!--  opacity: 0.5;-->
<!--}-->
<!--</style>-->