<script setup lang="ts">
import { ref, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { apiGet } from "../api"
import RackUPlan from "../components/RackUPlan.vue"

const route = useRoute()
const router = useRouter()

const racks = ref<any[]>([])
const rackId = ref<number | null>(null)
const currentRack = ref<any>(null)
const error = ref("")
const loading = ref(true)

// 同步路由 /rack/:id → 下拉选择
rackId.value = Number(route.params.id) || null

onMounted(async () => {
  try {
    const r = await apiGet<any>("/api/racks/")
    racks.value = r.results ?? r
    if (racks.value.length > 0) {
      if (!rackId.value || !racks.value.some((r) => r.id === rackId.value)) {
        // 无路由参数或参数无效 → 取第一台并回写 URL
        rackId.value = racks.value[0].id
        router.replace(`/rack/${rackId.value}`)
      }
      currentRack.value = racks.value.find((r) => r.id === rackId.value)
    } else {
      error.value = "暂无机柜数据。请先到 Django Admin（/admin/）创建机房和机柜。"
    }
  } catch (e: any) {
    error.value = e.message || "加载机柜列表失败"
  } finally {
    loading.value = false
  }
})

watch(() => route.params.id, (v) => {
  const id = Number(v) || null
  if (id && id !== rackId.value) rackId.value = id
})

function onRackChange(id: number) {
  rackId.value = id
  currentRack.value = racks.value.find((r) => r.id === id) || null
  // 下拉切换同步写 URL，刷新/分享不丢状态
  if (String(route.params.id) !== String(id)) router.replace(`/rack/${id}`)
}
</script>

<template>
  <div class="rack-view">
    <!-- 顶栏 -->
    <header class="topbar panel rise">
      <div class="brand">
        <span class="brand-mark"></span>
        <div>
          <h1>IDC 机柜管理</h1>
          <p class="brand-sub">RACK · POWER · CAPACITY</p>
        </div>
      </div>
      <div class="topbar-right">
        <el-select v-if="racks.length" v-model="rackId" class="rack-select"
                   size="large" @change="onRackChange">
          <el-option v-for="r in racks" :key="r.id" :value="r.id"
                     :label="`${r.location_code}（${r.name}）`" />
        </el-select>
        <el-link v-else-if="!loading" href="/admin/" target="_blank" type="primary">
          前往 Admin 建档
        </el-link>
        <el-tag v-if="currentRack" effect="dark" type="info" class="mono rack-meta">
          {{ currentRack.total_u }}U · {{ Number(currentRack.rated_power_kw) }}kW ·
          {{ Number(currentRack.max_weight_kg) }}kg
        </el-tag>
      </div>
    </header>

    <!-- 主区 -->
    <div v-if="loading" class="loading panel rise rise-1">
      <el-skeleton :rows="6" animated />
    </div>

    <el-empty v-else-if="error" :description="error" class="empty rise rise-1">
      <el-button type="primary" tag="a" href="/admin/" target="_blank">
        打开 Django Admin
      </el-button>
    </el-empty>

    <RackUPlan v-else-if="rackId" :key="rackId" :rack-id="rackId" />
  </div>
</template>

<style scoped>
.rack-view {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 20px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------- 顶栏 ---------- */
.topbar {
  display: flex;
  align-items: center;
  padding: 16px 22px;
  gap: 20px;
}
.brand { display: flex; align-items: center; gap: 14px; }
.brand-mark {
  width: 12px; height: 40px; border-radius: 3px;
  background: linear-gradient(180deg, var(--cyan), transparent);
  box-shadow: 0 0 12px rgba(45, 212, 191, 0.5);
}
h1 { margin: 0; font-size: 18px; font-weight: 700; letter-spacing: 0.02em; }
.brand-sub {
  margin: 2px 0 0;
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.35em;
  color: var(--t-low);
}
.topbar-right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.rack-select { width: 240px; }
.rack-meta { font-size: 12px; color: var(--t-mid); }

.loading, .empty { padding: 40px; }

@media (max-width: 700px) {
  .topbar { flex-direction: column; align-items: stretch; }
  .topbar-right { margin-left: 0; }
}
</style>
