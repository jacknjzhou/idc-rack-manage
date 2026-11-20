// 主题切换：light / dark / system 三模式
// 实现：html[data-theme] 挂令牌；system 模式跟随 prefers-color-scheme 并监听变化
import { ref } from "vue"

export type ThemeMode = "light" | "dark" | "system"

const STORAGE_KEY = "idc-theme"

function systemDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
}

function resolve(mode: ThemeMode): "light" | "dark" {
  return mode === "system" ? (systemDark() ? "dark" : "light") : mode
}

function apply(mode: ThemeMode) {
  const root = document.documentElement
  root.setAttribute("data-theme", resolve(mode))
  // color-scheme 让浏览器原生控件（滚动条等）跟随主题
  root.style.colorScheme = resolve(mode)
}

function applyWithAnim(mode: ThemeMode) {
  const root = document.documentElement
  root.classList.add("theme-anim")
  apply(mode)
  window.setTimeout(() => root.classList.remove("theme-anim"), 300)
}

export const themeMode = ref<ThemeMode>(
  (localStorage.getItem(STORAGE_KEY) as ThemeMode) || "system"
)

export function setThemeMode(mode: ThemeMode) {
  themeMode.value = mode
  localStorage.setItem(STORAGE_KEY, mode)
  applyWithAnim(mode)
}

// system 模式下监听系统主题变化
const mq = window.matchMedia("(prefers-color-scheme: dark)")
mq.addEventListener("change", () => {
  if (themeMode.value === "system") apply("system")
})

// 启动即生效（早于首屏渲染）
apply(themeMode.value)

/** 供测试 / SSR 场景手动清理 */
export function resetThemeForTest() {
  localStorage.removeItem(STORAGE_KEY)
  themeMode.value = "system"
  apply("system")
}
