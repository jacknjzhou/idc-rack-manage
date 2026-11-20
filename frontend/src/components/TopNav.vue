<script setup lang="ts">
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { apiGet } from "../api"
import { onMounted, ref } from "vue"

interface RackItem { id: number; location_code: string; name: string }

const route = useRoute()
const router = useRouter()

const racks = ref<RackItem[]>([])
onMounted(async () => {
  try {
    const r = await apiGet<any>("/api/racks/")
    racks.value = r.results ?? r
  } catch { /* 静默：导航机柜下拉失败不影响主页面 */ }
})

const currentRackId = computed(() => {
  const id = Number(route.params.id)
  return Number.isFinite(id) && id > 0 ? id : null
})
const currentRack = computed(() =>
  racks.value.find((r) => r.id === currentRackId.value) || null)

function onPick(id: number) {
  if (id) router.push(`/rack/${id}`)
}
</script>

<template>
  <nav class="topnav" aria-label="主导航">
    <div class="nav-inner">
      <!-- 品牌区（点击回大屏） -->
      <router-link to="/" class="brand" title="返回总览大屏">
        <span class="brand-mark"></span>
        <span class="brand-text">
          <span class="brand-name">IDC 机柜管理</span>
          <span class="brand-sub mono">RACK · POWER · CAPACITY</span>
        </span>
      </router-link>

      <!-- 主导航：大屏 / 机柜详情 -->
      <div class="nav-links">
        <router-link to="/" class="nav-link" :class="{ active: route.name === 'overview' }">
          <span class="nav-glyph">▦</span> 总览大屏
        </router-link>

        <div class="nav-link rack-nav" :class="{ active: route.name === 'rack' }">
          <span class="nav-glyph">▤</span> 机柜详情
          <el-select v-if="racks.length" class="rack-select"
                     :model-value="currentRackId" placeholder="选择机柜…"
                     size="small" @change="onPick">
            <el-option v-for="r in racks" :key="r.id" :value="r.id"
                       :label="`${r.location_code}（${r.name}）`" />
          </el-select>
          <span v-else-if="currentRackId" class="rack-fallback mono">
            #{{ currentRackId }}
          </span>
        </div>
      </div>

      <div class="nav-spacer"></div>
    </div>
  </nav>
</template>

<style scoped>
.topnav {
  position: sticky;
  top: 0;
  z-index: 90;
  background: color-mix(in srgb, var(--bg-1) 88%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}
.nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 20px;
  height: 54px;
  display: flex;
  align-items: center;
  gap: 26px;
}

/* ---------- 品牌 ---------- */
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  text-decoration: none;
  color: inherit;
}
.brand-mark {
  width: 10px; height: 30px; border-radius: 3px;
  background: linear-gradient(180deg, var(--cyan), transparent);
  box-shadow: 0 0 10px rgba(45, 212, 191, 0.5);
  transition: box-shadow 0.2s ease;
}
.brand:hover .brand-mark { box-shadow: 0 0 16px rgba(45, 212, 191, 0.85); }
.brand-text { display: flex; flex-direction: column; }
.brand-name { font-size: 14px; font-weight: 700; color: var(--t-hi); letter-spacing: 0.02em; }
.brand-sub {
  font-size: 8px; letter-spacing: 0.3em; color: var(--t-low);
  font-family: var(--mono);
}

/* ---------- 导航链接 ---------- */
.nav-links { display: flex; align-items: center; gap: 6px; }
.nav-link {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--t-mid);
  text-decoration: none;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  position: relative;
}
.nav-link:hover { color: var(--t-hi); background: var(--bg-2); }
.nav-link.active {
  color: var(--cyan);
  background: var(--cyan-dim);
  border-color: var(--cyan-line);
  font-weight: 500;
}
.nav-glyph { font-size: 13px; line-height: 1; opacity: 0.85; }

/* 机柜详情项内嵌下拉 */
.rack-nav { cursor: default; }
.rack-select { width: 210px; margin-left: 4px; }
.rack-nav :deep(.el-select__wrapper) {
  background: var(--bg-3);
  box-shadow: 0 0 0 1px var(--line) inset;
  min-height: 26px;
  font-size: 12px;
}
.rack-nav :deep(.el-select__wrapper.is-hovered),
.rack-nav :deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--cyan-line) inset;
}
.rack-fallback { color: var(--t-low); font-size: 12px; }

.nav-spacer { flex: 1; }

@media (max-width: 700px) {
  .nav-inner { gap: 12px; padding: 0 14px; }
  .brand-sub { display: none; }
  .rack-select { width: 150px; }
}
</style>
