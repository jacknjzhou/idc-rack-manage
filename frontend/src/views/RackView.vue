<script setup lang="ts">
import { ref, onMounted } from "vue"
import { apiGet } from "../api"
import RackUPlan from "../components/RackUPlan.vue"

const racks = ref<any[]>([])
const rackId = ref<number | null>(null)
const error = ref("")
const loading = ref(true)

onMounted(async () => {
  try {
    const r = await apiGet<any>("/api/racks/")
    racks.value = r.results ?? r
    if (racks.value.length > 0) rackId.value = racks.value[0].id
    else error.value = "暂无机柜数据。请先到 Django Admin（/admin/）创建机房和机柜。"
  } catch (e: any) {
    error.value = e.message || "加载机柜列表失败"
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="rack-view">
    <h2>机柜详情</h2>
    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <template v-else>
      <label>
        选择机柜：
        <select v-model.number="rackId">
          <option v-for="r in racks" :key="r.id" :value="r.id">
            {{ r.location_code }}（{{ r.name }}）
          </option>
        </select>
      </label>
      <RackUPlan v-if="rackId" :rack-id="rackId" />
    </template>
  </div>
</template>

<style scoped>
.error { color: #f56c6c; }
label { display: block; margin-bottom: 12px; }
select { padding: 4px 8px; }
</style>
