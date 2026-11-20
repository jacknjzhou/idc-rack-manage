<script setup lang="ts">
import { themeMode, setThemeMode, type ThemeMode } from "../theme"

const options: { value: ThemeMode; label: string; icon: string }[] = [
  { value: "light", label: "明亮", icon: "☀" },
  { value: "dark", label: "暗色", icon: "☾" },
  { value: "system", label: "跟随系统", icon: "◐" },
]
</script>

<template>
  <div class="theme-switch" role="radiogroup" aria-label="主题模式">
    <button v-for="o in options" :key="o.value" class="theme-btn"
            :class="{ active: themeMode === o.value }"
            role="radio" :aria-checked="themeMode === o.value"
            :title="o.label" @click="setThemeMode(o.value)">
      <span class="icon">{{ o.icon }}</span>
      <span class="text">{{ o.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.theme-switch {
  position: fixed;
  top: 14px;
  right: 16px;
  z-index: 100;
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 999px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  box-shadow: var(--panel-shadow);
}
.theme-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--t-mid);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.theme-btn:hover { color: var(--t-hi); }
.theme-btn.active {
  background: var(--cyan-dim);
  color: var(--cyan);
  font-weight: 500;
}
.icon { font-size: 13px; line-height: 1; }
@media (max-width: 560px) {
  .theme-btn .text { display: none; }
  .theme-btn { padding: 5px 9px; }
}
</style>
