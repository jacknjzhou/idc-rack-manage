import { describe, it, expect, beforeEach, vi } from "vitest"

// jsdom 支持 matchMedia stub
const listeners: (() => void)[] = []
let dark = true
vi.stubGlobal("matchMedia", vi.fn().mockImplementation(() => ({
  matches: dark,
  addEventListener: (_: string, fn: () => void) => listeners.push(fn),
  removeEventListener: (_: string, fn: () => void) => {
    const i = listeners.indexOf(fn)
    if (i >= 0) listeners.splice(i, 1)
  }
})))

const { setThemeMode, themeMode, resetThemeForTest } = await import("../theme")

describe("theme", () => {
  beforeEach(() => {
    dark = true
    resetThemeForTest()
  })

  it("默认 system 模式，解析为 dark", () => {
    expect(themeMode.value).toBe("system")
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark")
  })

  it("切换 light", () => {
    setThemeMode("light")
    expect(themeMode.value).toBe("light")
    expect(document.documentElement.getAttribute("data-theme")).toBe("light")
    expect(localStorage.getItem("idc-theme")).toBe("light")
  })

  it("切换 dark", () => {
    setThemeMode("dark")
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark")
    expect(localStorage.getItem("idc-theme")).toBe("dark")
  })

  it("system 模式跟随系统亮色变化", () => {
    setThemeMode("system")
    dark = false
    listeners.forEach((fn) => fn())
    expect(document.documentElement.getAttribute("data-theme")).toBe("light")
  })

  it("非 system 模式不受系统变化影响", () => {
    setThemeMode("light")
    dark = false
    listeners.forEach((fn) => fn())
    expect(document.documentElement.getAttribute("data-theme")).toBe("light")
  })
})
