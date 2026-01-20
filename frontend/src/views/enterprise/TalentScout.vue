<template>
  <div class="enterprise-portal">
    <!-- 页面标题 -->
    <a-page-header 
      title="🎯 智能人才召回" 
      sub-title="根据职位要求，快速匹配最佳候选人"
      :style="{ background: 'white', marginBottom: '24px', borderRadius: '8px' }"
    />
    
    <!-- 搜索区域 -->
    <a-card class="search-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :span="10">
          <a-input-search
            v-model:value="jobId"
            placeholder="输入职位ID、技能关键词（如Python、Java）"
            enter-button="搜索人才"
            size="large"
            @search="scoutTalents"
          >
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input-search>
        </a-col>
        <a-col :span="4">
          <a-select v-model:value="educationFilter" placeholder="学历筛选" style="width: 100%" size="large" allowClear>
            <a-select-option value="本科">本科</a-select-option>
            <a-select-option value="硕士">硕士</a-select-option>
            <a-select-option value="博士">博士</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="4">
          <a-select v-model:value="topK" style="width: 100%" size="large">
            <a-select-option :value="10">Top 10</a-select-option>
            <a-select-option :value="20">Top 20</a-select-option>
            <a-select-option :value="50">Top 50</a-select-option>
          </a-select>
        </a-col>
      </a-row>
    </a-card>
    
    <!-- 候选人列表 -->
    <a-spin :spinning="loading">
      <a-table 
        :columns="columns" 
        :data-source="paginatedCandidates" 
        :row-key="record => record.student_id"
        :pagination="false"
        :scroll="{ x: 1200 }"
        bordered
      >
        <!-- 匹配度 -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'match_score'">
            <div style="display: flex; align-items: center; justify-content: center;">
              <a-progress 
                :percent="Math.round(record.match_score * 100)" 
                :stroke-color="getScoreColor(record.match_score)"
                :show-info="true"
                style="width: 100px; margin: 0;"
              />
            </div>
          </template>
          
          <!-- 雷达图 -->
          <template v-else-if="column.key === 'radar'">
            <a-button size="small" type="primary" ghost @click="showRadar(record)">
              查看能力图
            </a-button>
          </template>
          
          <!-- 技能 -->
          <template v-else-if="column.key === 'skills'">
            <div style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              <a-tag v-for="skill in record.matched_skills.slice(0, 3)" :key="skill" color="green">
                {{ skill }}
              </a-tag>
              <a-tag v-if="record.matched_skills.length > 3" color="blue">
                +{{ record.matched_skills.length - 3 }}
              </a-tag>
            </div>
          </template>
          
          <!-- 操作 -->
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="primary" size="small" @click="xrayResume(record)">
                简历透视
              </a-button>
              <a-button size="small">联系</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
      
      <!-- 分页组件 -->
      <div class="pagination-container" v-if="candidates.length > 0">
        <a-pagination
          v-model:current="currentPage"
          v-model:pageSize="pageSize"
          :total="candidates.length"
          :pageSizeOptions="['10', '20', '50']"
          show-size-changer
          show-quick-jumper
          :show-total="total => `共 ${total} 名候选人`"
        />
      </div>
    </a-spin>
    
    <!-- 能力图弹窗 -->
    <a-modal 
      v-model:open="radarVisible" 
      :title="`📊 ${currentCandidate?.name || ''} 的能力分析`"
      width="600px"
      :footer="null"
    >
      <div v-if="currentCandidate" style="padding: 14px;">
        <a-descriptions :column="4" bordered size="small">
          <a-descriptions-item label="学生ID">{{ currentCandidate.student_id }}</a-descriptions-item>
          <a-descriptions-item label="姓名">{{ currentCandidate.name }}</a-descriptions-item>
          <a-descriptions-item label="专业" :span="2">{{ currentCandidate.major }}</a-descriptions-item>
          <a-descriptions-item label="学历" :span="2">{{ currentCandidate.education }}</a-descriptions-item>
          <a-descriptions-item label="匹配度" :span="2">
            <a-progress :percent="Math.round(currentCandidate.match_score * 100)" :stroke-color="getScoreColor(currentCandidate.match_score)" />
          </a-descriptions-item>
        </a-descriptions>
        
        <a-divider>匹配技能</a-divider>
        <div>
          <a-tag v-for="skill in currentCandidate.matched_skills" :key="skill" color="green" style="margin: 4px;">
            {{ skill }}
          </a-tag>
        </div>
      </div>
    </a-modal>
    
    <!-- 简历透视弹窗 -->
    <a-modal 
      v-model:open="xrayVisible" 
      title="🔬 简历透视分析"
      width="800px"
      :footer="null"
    >
      <div v-if="resumeInsight">
        <a-row :gutter="24">
          <a-col :span="12">
            <a-card title="匹配技能" size="small">
              <a-tag v-for="skill in resumeInsight.matched_skills" :key="skill" color="green">
                {{ skill }}
              </a-tag>
              <a-empty v-if="!resumeInsight.matched_skills?.length" description="无匹配技能" />
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="缺失技能" size="small">
              <a-tag v-for="skill in resumeInsight.missing_skills" :key="skill" color="red">
                {{ skill }}
              </a-tag>
              <a-empty v-if="!resumeInsight.missing_skills?.length" description="无缺失技能" />
            </a-card>
          </a-col>
        </a-row>
        
        <a-statistic 
          title="技能匹配率" 
          :value="Math.round((resumeInsight.match_rate || 0) * 100)" 
          suffix="%" 
          style="margin-top: 16px; text-align: center;"
        />
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import { enterpriseApi } from '@/api'

const jobId = ref('')
const topK = ref(20)
const educationFilter = ref(null)
const loading = ref(false)
const candidates = ref([])
const xrayVisible = ref(false)
const resumeInsight = ref(null)
const radarVisible = ref(false)
const currentCandidate = ref(null)

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)

const paginatedCandidates = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return candidates.value.slice(start, end)
})

const columns = [
  { title: '学生ID', dataIndex: 'student_id', key: 'student_id', width: 100, fixed: 'left' },
  { title: '姓名', dataIndex: 'name', key: 'name', width: 100 },
  { title: '专业', dataIndex: 'major', key: 'major', width: 150 },
  { title: '学历', dataIndex: 'education', key: 'education', width: 80 },
  { title: '匹配度', key: 'match_score', width: 150 },
  { title: '匹配技能', key: 'skills', width: 220 },
  { title: '能力图', key: 'radar', width: 110 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' }
]

const getScoreColor = (score) => {
  if (score >= 0.8) return '#52c41a'
  if (score >= 0.6) return '#1890ff'
  return '#faad14'
}

const scoutTalents = async () => {
  if (!jobId.value) {
    message.warning('请输入职位ID或技能关键词')
    return
  }
  
  loading.value = true
  try {
    const { data } = await enterpriseApi.scoutTalents(
      jobId.value, 
      topK.value, 
      educationFilter.value
    )
    candidates.value = data.candidates
    message.success(`找到 ${data.candidates.length} 名候选人`)
  } catch (error) {
    message.error('搜索失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const showRadar = (record) => {
  currentCandidate.value = record
  radarVisible.value = true
}

const xrayResume = async (record) => {
  try {
    const { data } = await enterpriseApi.xrayResume(record.student_id, jobId.value)
    resumeInsight.value = data
    xrayVisible.value = true
  } catch (error) {
    message.error('透视分析失败')
  }
}
</script>

<style scoped>
.enterprise-portal {
  max-width: 1400px;
  margin: 0 auto;
}

.search-card {
  margin-bottom: 24px;
  border-radius: 12px;
  border-left: 4px solid #722ed1;
}

:deep(.ant-table) {
  font-size: 13px;
}

:deep(.ant-table-thead > tr > th) {
  background: #fafafa;
  font-weight: 600;
  padding: 8px 12px !important;
}

:deep(.ant-table-tbody > tr > td) {
  padding: 8px 12px !important;
}

:deep(.ant-progress) {
  margin-bottom: 0 !important;
}

.pagination-container {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  padding-bottom: 16px;
}
</style>

