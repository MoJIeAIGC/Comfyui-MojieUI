<script setup lang="ts">
import {useRoute} from "vue-router";

const route = useRoute()
</script>

<template>
<div style="flex: 1">
  场景：{{route.params.id}}
  <iframe frameborder="0" width="100%" height="100%" src="http://175.178.229.216:3000/preview/65e580a018e45d8b258bca72"></iframe>
</div>
</template>

<style scoped>

</style>