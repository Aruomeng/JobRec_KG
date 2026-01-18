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
            placeholder="输入职位ID或关键词"
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
        :data-source="candidates" 
        :row-key="record => record.student_id"
        :pagination="{ pageSize: 10 }"
      >
        <!-- 匹配度 -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'match_score'">
            <a-progress 
              :percent="Math.round(record.match_score * 100)" 
              :size="80"
              :stroke-color="getScoreColor(record.match_score)"
            />
          </template>
          
          <!-- 雷达图 -->
          <template v-else-if="column.key === 'radar'">
            <a-button size="small" @click="showRadar(record)">
              查看能力图
            </a-button>
          </template>
          
          <!-- 技能 -->
          <template v-else-if="column.key === 'skills'">
            <a-tag v-for="skill in record.matched_skills" :key="skill" color="green">
              {{ skill }}
            </a-tag>
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
    </a-spin>
    
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
            <a-card title="显性技能" size="small">
              <a-tag v-for="skill in resumeInsight.explicit_skills" :key="skill" color="blue">
                {{ skill }}
              </a-tag>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="隐性技能（AI推断）" size="small">
              <a-tag v-for="skill in resumeInsight.implicit_skills" :key="skill" color="purple">
                {{ skill }}
              </a-tag>
            </a-card>
          </a-col>
        </a-row>
        
        <a-divider>技能来源追溯</a-divider>
        
        <a-list 
          :data-source="resumeInsight.skill_sources"
          size="small"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-tag :color="item.type === 'explicit' ? 'blue' : 'purple'">
                {{ item.skill }}
              </a-tag>
              <span>← {{ item.source }}</span>
              <template #extra>
                <a-tag v-if="item.type === 'implicit'" color="gold">AI推断</a-tag>
              </template>
            </a-list-item>
          </template>
        </a-list>
        
        <a-statistic 
          title="整体匹配度" 
          :value="Math.round(resumeInsight.overall_fit * 100)" 
          suffix="%" 
          style="margin-top: 16px"
        />
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref } from 'vue'
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

const columns = [
  { title: '学生ID', dataIndex: 'student_id', key: 'student_id' },
  { title: '姓名', dataIndex: 'name', key: 'name' },
  { title: '专业', dataIndex: 'major', key: 'major' },
  { title: '学历', dataIndex: 'education', key: 'education' },
  { title: '匹配度', key: 'match_score', width: 150 },
  { title: '匹配技能', key: 'skills' },
  { title: '能力图', key: 'radar', width: 100 },
  { title: '操作', key: 'action', width: 180 }
]

const getScoreColor = (score) => {
  if (score >= 0.8) return '#52c41a'
  if (score >= 0.6) return '#1890ff'
  return '#faad14'
}

const scoutTalents = async () => {
  if (!jobId.value) {
    message.warning('请输入职位ID')
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
    message.error('搜索失败')
  } finally {
    loading.value = false
  }
}

const showRadar = (record) => {
  message.info(`查看 ${record.name} 的能力雷达图`)
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
</style>
