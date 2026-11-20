<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import { apiGet } from "../api"

interface DashCell { device_id: number; asset_no: string; status: string }
interface DashRack {
  id: number; location_code: string; name: string; total_u: number
  used_u: Record<string, number>
  load_ratio: number; load_ratio_is_estimate: boolean
  power: Record<string, number>; weight: Record<string, number>
  warnings: string[]; status: "ok" | "warn" | "alert"
}
interface DashRoom { id: number; code: string; name: string; racks: DashRack[] }
interface Dashboard {
  summary: {
    room_count: number; rack_count: number; device_count: number
    avg_load_ratio: number; alert_rack_count: number
  }
  rooms: DashRoom[]
}

const router = useRouter()
const data = ref<Dashboard | null>(null)
const error = ref("")
const filterAlert = ref(false)
let timer: number | undefined

async function load() {
  try {
    data.value = await apiGet<Dashboard>("/api/racks/dashboard/")
    error.value = ""
  } catch (e: any) {
    error.value = e.message || "加载总览失败"
  }
}

onMounted(async () => {
  await load()
  timer = window.setInterval(load, 30000) // 30s 轮询
})
onUnmounted(() => window.clearInterval(timer))

const visibleRooms = computed(() => {
  if (!data.value) return []
  if (!filterAlert.value) return data.value.rooms
  return data.value.rooms
    .map((r) => ({ ...r, racks: r.racks.filter((k) => k.status !== "ok") }))
    .filter((r) => r.racks.length > 0)
})

function openRack(id: number) {
  router.push(`/rack/${id}`)
}

function pct(rack: DashRack, face: "A" | "B"): number {
  const used = rack.used_u?.[face] ?? 0
  return rack.total_u > 0 ? Math.round((used / rack.total_u) * 100) : 0
}
function ratioPct(rack: DashRack): number {
  return Math.round(Number(rack.load_ratio || 0) * 100)
}
function fmtPwr(rack: DashRack): string {
  return `${Number(rack.power?.used_w ?? 0).toLocaleString()} / ${Number(rack.power?.rated_w ?? 0).toLocaleString()} W`
}
function fmtWgt(rack: DashRack): string {
  return `${Number(rack.weight?.used_kg ?? 0).toLocaleString()} / ${Number(rack.weight?.max_kg ?? 0).toLocaleString()} kg`
}
</script>

<template>
  <div class="overview">
    <!-- 顶部汇总条 -->
    <header class="summary panel rise">
      <div class="brand">
        <span class="brand-mark"></span>
        <div>
          <h1>机房总览大屏</h1>
          <p class="brand-sub">OVERVIEW · 30S REFRESH</p>
        </div>
      </div>
      <div v-if="data" class="stats">
        <div class="stat"><span class="stat-num mono">{{ data.summary.room_count }}</span><span class="stat-label">机房</span></div>
        <div class="stat"><span class="stat-num mono">{{ data.summary.rack_count }}</span><span class="stat-label">机柜</span></div>
        <div class="stat"><span class="stat-num mono">{{ data.summary.device_count }}</span><span class="stat-label">在用设备</span></div>
        <div class="stat"><span class="stat-num mono">{{ Math.round(Number(data.summary.avg_load_ratio) * 100) }}%</span><span class="stat-label">平均负载</span></div>
        <button class="stat stat-alert" :class="{ active: filterAlert }"
                @click="filterAlert = !filterAlert"
                :title="filterAlert ? '点击取消告警过滤' : '点击只看告警机柜'">
          <span class="stat-num mono">{{ data.summary.alert_rack_count }}</span>
          <span class="stat-label">{{ filterAlert ? "过滤中" : "告警机柜" }}</span>
        </button>
      </div>
    </header>

    <div v-if="error" class="panel empty rise rise-1">
      <el-empty :description="error">
        <el-button type="primary" @click="load">重试</el-button>
      </el-empty>
    </div>

    <div v-else-if="!data" class="panel empty rise rise-1">
      <el-skeleton :rows="6" animated />
    </div>

    <el-empty v-else-if="visibleRooms.length === 0" description="暂无数据"
              class="panel empty rise rise-1" />

    <!-- 机房分组 × 机柜竖条矩阵 -->
    <section v-for="room in visibleRooms" :key="room.id" class="room rise">
      <div class="room-head">
        <span class="room-badge mono">{{ room.code }}</span>
        <span class="room-name">{{ room.name }}</span>
        <span class="room-count mono">{{ room.racks.length }} 柜</span>
      </div>
      <div class="rack-grid">
        <el-tooltip v-for="rack in room.racks" :key="rack.id" placement="top" :show-after="120">
          <template #content>
            <div class="tip mono">
              <div class="tip-title">{{ rack.location_code }}（{{ rack.name }}）</div>
              <div>U 位 A/B：{{ rack.used_u?.A ?? 0 }} / {{ rack.used_u?.B ?? 0 }}（{{ rack.total_u }}U）</div>
              <div>负载率：{{ ratioPct(rack) }}%{{ rack.load_ratio_is_estimate ? "（估算）" : "" }}</div>
              <div>功率：{{ fmtPwr(rack) }}</div>
              <div>承重：{{ fmtWgt(rack) }}</div>
              <div v-if="rack.warnings.length" class="tip-warn">⚠ {{ rack.warnings.join("；") }}</div>
            </div>
          </template>
          <button class="rack-bar" :class="rack.status" @click="openRack(rack.id)">
            <span class="bar-status mono">{{ rack.status.toUpperCase() }}</span>
            <div class="bar-faces">
              <div class="bar-face">
                <div class="bar-fill" :style="{ height: pct(rack, 'A') + '%' }"></div>
                <span class="bar-face-tag mono">A</span>
              </div>
              <div class="bar-face">
                <div class="bar-fill" :style="{ height: pct(rack, 'B') + '%' }"></div>
                <span class="bar-face-tag mono">B</span>
              </div>
            </div>
            <span class="bar-code mono">{{ rack.location_code }}</span>
            <span class="bar-ratio mono">{{ ratioPct(rack) }}%</span>
          </button>
        </el-tooltip>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overview {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 20px 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ---------- 汇总条 ---------- */
.summary { display: flex; align-items: center; padding: 16px 22px; gap: 20px; flex-wrap: wrap; }
.brand { display: flex; align-items: center; gap: 14px; }
.brand-mark {
  width: 12px; height: 40px; border-radius: 3px;
  background: linear-gradient(180deg, var(--cyan), transparent);
  box-shadow: 0 0 12px rgba(45, 212, 191, 0.5);
}
h1 { margin: 0; font-size: 18px; font-weight: 700; }
.brand-sub {
  margin: 2px 0 0; font-family: var(--mono);
  font-size: 10px; letter-spacing: 0.35em; color: var(--t-low);
}
.stats { margin-left: auto; display: flex; gap: 10px; flex-wrap: wrap; }
.stat {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 8px 18px; border-radius: 8px;
  background: var(--bg-2); border: 1px solid var(--line);
  color: inherit; font: inherit; cursor: default;
}
.stat-num { font-size: 20px; font-weight: 600; color: var(--cyan); }
.stat-label { font-size: 11px; color: var(--t-low); }
.stat-alert { cursor: pointer; border-color: rgba(248, 113, 113, 0.4); transition: all 0.15s; }
.stat-alert .stat-num { color: var(--red); }
.stat-alert:hover, .stat-alert.active { background: rgba(248, 113, 113, 0.12); }

/* ---------- 机房分组 ---------- */
.room-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.room-badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 10px; border-radius: 6px;
  background: var(--cyan-dim); border: 1px solid var(--cyan-line);
  color: var(--cyan); font-weight: 600; font-size: 12px;
}
.room-name { font-weight: 500; color: var(--t-hi); }
.room-count { margin-left: auto; color: var(--t-low); font-size: 12px; }

/* ---------- 机柜竖条矩阵 ---------- */
.rack-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
  gap: 12px;
}
.rack-bar {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 10px 6px 8px; border-radius: 8px;
  background: var(--bg-2); border: 1px solid var(--line);
  color: inherit; font: inherit; cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.rack-bar:hover { transform: translateY(-3px); border-color: var(--cyan-line); }
.rack-bar.warn { border-color: rgba(245, 158, 11, 0.6); }
.rack-bar.alert {
  border-color: rgba(248, 113, 113, 0.8);
  animation: breath 1.6s ease-in-out infinite;
}
@keyframes breath {
  0%, 100% { box-shadow: 0 0 0 rgba(248, 113, 113, 0); }
  50% { box-shadow: 0 0 14px rgba(248, 113, 113, 0.55); }
}
.bar-status {
  font-size: 10px; letter-spacing: 0.1em; color: var(--t-low);
}
.rack-bar.warn .bar-status { color: var(--amber); }
.rack-bar.alert .bar-status { color: var(--red); }

.bar-faces { display: flex; gap: 8px; height: 120px; }
.bar-face {
  position: relative; width: 22px; height: 100%;
  background: var(--bg-3); border: 1px solid var(--line);
  border-radius: 4px; overflow: hidden;
  display: flex; align-items: flex-end; justify-content: center;
}
.bar-fill {
  width: 100%;
  background: linear-gradient(180deg, var(--cyan), rgba(45, 212, 191, 0.35));
  transition: height 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}
.rack-bar.warn .bar-fill { background: linear-gradient(180deg, var(--amber), rgba(245, 158, 11, 0.35)); }
.rack-bar.alert .bar-fill { background: linear-gradient(180deg, var(--red), rgba(248, 113, 113, 0.35)); }
.bar-face-tag {
  position: absolute; top: 3px; left: 0; right: 0; text-align: center;
  font-size: 9px; color: var(--t-low); z-index: 1;
}
.bar-code { font-size: 11px; color: var(--t-hi); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-ratio { font-size: 10px; color: var(--t-mid); }

/* ---------- tooltip 内容 ---------- */
.tip { font-size: 12px; line-height: 1.8; }
.tip-title { font-weight: 600; color: var(--cyan); }
.tip-warn { color: var(--red); }

.empty { padding: 48px; }

@media (max-width: 700px) {
  .summary { flex-direction: column; align-items: stretch; }
  .stats { margin-left: 0; }
}
</style>
