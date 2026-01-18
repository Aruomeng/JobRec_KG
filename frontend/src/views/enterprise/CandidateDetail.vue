<template>
  <div class="candidate-detail">
    <a-page-header 
      title="候选人详情" 
      sub-title="简历透视分析"
      @back="() => $router.back()"
      :style="{ background: 'white', borderRadius: '8px' }"
    />
    
    <a-empty description="请从人才列表进入" />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
console.log('Candidate ID:', route.params.id)
</script>
