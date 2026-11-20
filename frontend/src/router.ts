import { createRouter, createWebHistory } from "vue-router"

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "overview", component: () => import("./views/OverviewView.vue") },
    { path: "/rack/:id", name: "rack", component: () => import("./views/RackView.vue") },
    { path: "/rack", redirect: "/" },
  ],
})
