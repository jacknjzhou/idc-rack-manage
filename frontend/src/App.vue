<script setup lang="ts">
import RackView from "./views/RackView.vue"
import ThemeSwitcher from "./components/ThemeSwitcher.vue"
</script>

<template>
  <div class="app-shell">
    <ThemeSwitcher />
    <RackView />
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; }
</style>
