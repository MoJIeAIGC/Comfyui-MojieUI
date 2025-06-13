<template>
  <div class="test-cursor" @mousemove="mousemove" @mouseleave="mouseleave">
    <div class="custom-cursor123"></div>
  </div>
</template>
<script setup>
const mousemove = (e) => {
  const cursor = document.querySelector('.custom-cursor123')
  cursor.style.display = `block`
  cursor.style.left = `${e.clientX -32}px`
  cursor.style.top = `${e.clientY -32}px`
}
const mouseleave = (e) => {
  const cursor = document.querySelector('.custom-cursor123')
  cursor.style.display = `none`
}
</script>

<style scoped>
.test-cursor{
  height: 100vh;
}
.custom-cursor123 {
  position: fixed;
  pointer-events: none;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  cursor: none;
  background-color: rgba(42,86,145,.4);
  z-index: 999999999999;
}
</style>