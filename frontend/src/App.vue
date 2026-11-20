<script setup lang="ts">
import ThemeSwitcher from "./components/ThemeSwitcher.vue"
import TopNav from "./components/TopNav.vue"
</script>

<template>
  <div class="app-shell">
    <TopNav />
    <ThemeSwitcher />
    <router-view />
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; }
</style>
