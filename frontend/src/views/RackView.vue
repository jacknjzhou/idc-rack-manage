<script setup lang="ts">
import RackUPlan from "../components/RackUPlan.vue"

const rackId = 1
</script>

<template>
  <div class="rack-view">
    <h2>机柜详情</h2>
    <RackUPlan :rack-id="rackId" />
  </div>
</template>
