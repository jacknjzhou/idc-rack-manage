<script setup lang="ts">
import { ref, onMounted } from "vue"
import { apiGet } from "../api"
const props = defineProps<{ rackId: number }>()
const emit = defineEmits<{ (e: "pick", v: { face: string; u: number }): void }>()
const uplan = ref<Record<string, any[]>>({ A: [], B: [] })
const usage = ref<any>({})
onMounted(async () => {
  uplan.value = await apiGet(`/api/racks/${props.rackId}/uplan/`)
  usage.value = await apiGet(`/api/racks/${props.rackId}/usage/`)
})
const cells = (face: string) => [...(uplan.value[face] || [])].map((c, i) => ({ u: i + 1, c })).reverse()
</script>

<template>
  <div class="rack-uplan">
    <div class="summary">
      <span>剩余U：A {{ usage.remaining_u_by_face?.A }} / B {{ usage.remaining_u_by_face?.B }}</span>
      <span>剩余功率：{{ usage.remaining_power_w }} W</span>
      <span>剩余承重：{{ usage.remaining_weight_kg }} kg</span>
      <span v-for="w in usage.warnings || []" class="warn">{{ w }}</span>
    </div>
    <div v-for="face in ['A','B']" :key="face" class="face">
      <h4>{{ face }} 面</h4>
      <div class="grid">
        <div v-for="row in cells(face)" :key="row.u" class="u-cell"
             :class="row.c ? (row.c.status === 'reserved' ? 'reserved' : 'used') : 'free'"
             @click="emit('pick', { face, u: row.u })">
          <small>{{ row.u }}U</small>
          <span v-if="row.c">{{ row.c.asset_no }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr; gap: 2px; max-width: 320px; }
.u-cell { border: 1px solid #ccc; padding: 4px 8px; cursor: pointer; display: flex; gap: 8px; }
.u-cell.used { background: #409eff; color: #fff; }
.u-cell.reserved { background: #e6a23c; color: #fff; }
.u-cell.free:hover { background: #f0f9ff; }
.warn { color: #f56c6c; margin-left: 8px; }
</style>
