import { createApp } from "vue"
import ElementPlus from "element-plus"
import "element-plus/dist/index.css"
import "./style.css"
import "./theme" // 先于 App 应用主题，避免首屏闪烁
import App from "./App.vue"

createApp(App).use(ElementPlus).mount("#app")
