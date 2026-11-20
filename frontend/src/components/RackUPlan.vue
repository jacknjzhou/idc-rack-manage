<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { apiGet } from "../api"

const props = defineProps<{ rackId: number }>()
const emit = defineEmits<{ (e: "pick", v: { face: string; u: number }): void }>()

const uplan = ref<Record<string, any[]>>({ A: [], B: [] })
const usage = ref<any>({})
const loaded = ref(false)

const load = async () => {
  uplan.value = await apiGet(`/api/racks/${props.rackId}/uplan/`)
  usage.value = await apiGet(`/api/racks/${props.rackId}/usage/`)
  loaded.value = true
}
onMounted(load)

const cells = (face: string) =>
  [...(uplan.value[face] || [])]
    .map((c, i) => ({ u: i + 1, c }))
    .reverse()

const loadPct = computed(() =>
  Math.min(100, Math.round(Number(usage.value.load_ratio || 0) * 100))
)

const loadColor = computed(() => {
  const p = loadPct.value
  if (p >= 90) return "var(--red)"
  if (p >= 70) return "var(--amber)"
  return "var(--cyan)"
})
</script>

<template>
  <div v-if="loaded" class="rack-uplan">
    <!-- 仪表行：四块指标 -->
    <div class="gauges">
      <div class="panel gauge rise rise-1">
        <div class="gauge-label">负载率</div>
        <el-progress type="dashboard" :percentage="loadPct" :color="loadColor"
                     :width="88" :stroke-width="8" :gap-width="6">
          <span class="mono gauge-big" :style="{ color: loadColor }">{{ loadPct }}%</span>
        </el-progress>
        <div class="gauge-sub mono">
          {{ usage.load_ratio_is_estimate ? "估算值" : "实际电表" }}
        </div>
      </div>

      <div class="panel gauge rise rise-2">
        <div class="gauge-label">剩余 U 位（A / B 面）</div>
        <div class="gauge-num mono">
          <span class="hi">{{ usage.remaining_u_by_face?.A ?? "-" }}</span>
          <span class="sep">/</span>
          <span class="hi">{{ usage.remaining_u_by_face?.B ?? "-" }}</span>
        </div>
        <div class="gauge-sub">
          已用 <span class="mono">{{ usage.used_u_by_face?.A ?? 0 }}</span> /
          <span class="mono">{{ usage.used_u_by_face?.B ?? 0 }}</span>
        </div>
      </div>

      <div class="panel gauge rise rise-3">
        <div class="gauge-label">剩余功率</div>
        <div class="gauge-num mono hi">
          {{ Number(usage.remaining_power_w ?? 0).toLocaleString() }}<small> W</small>
        </div>
        <div class="gauge-sub">
          已用 <span class="mono">{{ Number(usage.used_power_w ?? 0).toLocaleString() }} W</span>
        </div>
      </div>

      <div class="panel gauge rise rise-4">
        <div class="gauge-label">剩余承重</div>
        <div class="gauge-num mono hi">
          {{ Number(usage.remaining_weight_kg ?? 0).toLocaleString() }}<small> kg</small>
        </div>
        <div class="gauge-sub">
          已用 <span class="mono">{{ Number(usage.used_weight_kg ?? 0).toLocaleString() }} kg</span>
        </div>
      </div>
    </div>

    <!-- 告警条 -->
    <div v-for="(w, i) in usage.warnings || []" :key="i" class="warn-alert rise">
      <span class="warn-icon">▲</span>
      <span>{{ w }}</span>
    </div>

    <!-- U 位图：A/B 两面并列 -->
    <div class="faces">
      <div v-for="face in ['A', 'B']" :key="face" class="panel face rise rise-2">
        <div class="face-head">
          <span class="face-badge mono">{{ face }}</span>
          <span class="face-title">{{ face }} 面视图</span>
          <span class="face-legend">
            <i class="dot free" />空闲
            <i class="dot used" />在用
            <i class="dot reserved" />预留
          </span>
        </div>
        <div class="grid">
          <div v-for="row in cells(face)" :key="row.u" class="u-cell"
               :class="row.c ? (row.c.status === 'reserved' ? 'reserved' : 'used') : 'free'"
               @click="emit('pick', { face, u: row.u })">
            <span class="u-no mono">{{ row.u }}U</span>
            <span v-if="row.c" class="u-asset mono">{{ row.c.asset_no }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="skeleton-wrap">
    <el-skeleton :rows="8" animated />
  </div>
</template>

<style scoped>
.rack-uplan { display: flex; flex-direction: column; gap: 16px; }

/* ---------- 仪表行 ---------- */
.gauges {
  display: grid;
  grid-template-columns: 140px repeat(3, 1fr);
  gap: 12px;
}
.gauge { padding: 16px 18px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.gauge-label { color: var(--t-low); font-size: 12px; letter-spacing: 0.08em; }
.gauge-big { font-size: 20px; font-weight: 600; }
.gauge-num { font-size: 26px; font-weight: 600; color: var(--t-hi); }
.gauge-num small { font-size: 13px; color: var(--t-low); margin-left: 2px; }
.gauge-sub { color: var(--t-mid); font-size: 12px; }
.hi { color: var(--cyan); }
.sep { color: var(--t-low); margin: 0 8px; }

/* ---------- 告警 ---------- */
.warn-alert {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px;
  border-radius: 8px;
  background: var(--amber-dim);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: var(--amber);
  font-size: 13px;
}
.warn-icon { font-size: 10px; }

/* ---------- 双面 U 位图 ---------- */
.faces { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.face { padding: 16px; }
.face-head {
  display: flex; align-items: center; gap: 10px;
  padding-bottom: 12px; margin-bottom: 12px;
  border-bottom: 1px dashed var(--line-bright);
}
.face-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 6px;
  background: var(--cyan-dim); border: 1px solid var(--cyan-line);
  color: var(--cyan); font-weight: 600;
}
.face-title { font-weight: 500; color: var(--t-hi); }
.face-legend { margin-left: auto; color: var(--t-mid); font-size: 12px; display: flex; align-items: center; gap: 6px; }
.dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; margin-left: 10px; }
.dot.free { background: var(--bg-3); border: 1px solid var(--line-bright); }
.dot.used { background: var(--cyan); }
.dot.reserved { background: var(--amber); }

/* U 位格子 */
.grid { display: grid; grid-template-columns: 1fr; gap: 3px; max-height: 560px; overflow-y: auto; padding-right: 4px; }
.u-cell {
  display: flex; align-items: center; gap: 10px;
  padding: 5px 12px; border-radius: 5px; cursor: pointer;
  border: 1px solid var(--line);
  background: var(--bg-3);
  transition: all 0.15s ease;
  min-height: 30px;
}
.u-no { color: var(--t-low); font-size: 11px; width: 34px; flex-shrink: 0; }
.u-asset { color: var(--t-hi); font-size: 12px; }
.u-cell.free:hover { background: var(--cyan-dim); border-color: var(--cyan-line); }
.u-cell.used {
  background: linear-gradient(90deg, rgba(45, 212, 191, 0.16), rgba(45, 212, 191, 0.05));
  border-color: var(--cyan-line);
  box-shadow: inset 3px 0 0 var(--cyan);
}
.u-cell.used .u-asset, .u-cell.used .u-no { color: var(--cyan); }
.u-cell.reserved {
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.16), rgba(245, 158, 11, 0.05));
  border-color: rgba(245, 158, 11, 0.4);
  box-shadow: inset 3px 0 0 var(--amber);
}
.u-cell.reserved .u-asset, .u-cell.reserved .u-no { color: var(--amber); }

/* 进场：格子级联浮入 */
.u-cell { animation: rise 0.4s cubic-bezier(0.22, 1, 0.36, 1) both; }
.u-cell:nth-child(1) { animation-delay: 0.05s; }

/* 滚动条 */
.grid::-webkit-scrollbar { width: 6px; }
.grid::-webkit-scrollbar-thumb { background: var(--line-bright); border-radius: 3px; }
.grid::-webkit-scrollbar-track { background: transparent; }

.skeleton-wrap { padding: 24px; }

@media (max-width: 900px) {
  .gauges { grid-template-columns: 1fr 1fr; }
  .faces { grid-template-columns: 1fr; }
}
</style>
