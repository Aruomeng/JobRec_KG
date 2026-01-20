<template>
  <div class="university-portal">
    <!-- 页面标题 -->
    <a-page-header 
      title="📊 技能供需Gap分析" 
      sub-title="课程供给 vs 市场需求全景透视"
      :style="{ background: 'white', marginBottom: '24px', borderRadius: '8px' }"
    />
    
    <!-- 统计卡片 -->
    <a-row :gutter="24" class="stat-cards">
      <a-col :span="6">
        <a-card class="stat-card stat-gap">
          <a-statistic 
            title="技能缺口数" 
            :value="gaps.length" 
            :value-style="{ color: '#fa8c16' }"
          >
            <template #suffix>项</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card stat-courses">
          <a-statistic 
            title="课程总数" 
            :value="courses.length"
            :value-style="{ color: '#1890ff' }"
          >
            <template #suffix>门</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card stat-high">
          <a-statistic 
            title="高关联课程" 
            :value="highRelevanceCourses"
            :value-style="{ color: '#52c41a' }"
          >
            <template #suffix>门</template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card stat-low">
          <a-statistic 
            title="低关联课程" 
            :value="lowRelevanceCourses"
            :value-style="{ color: '#ff4d4f' }"
          >
            <template #suffix>门</template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>
    
    <!-- Tab切换 -->
    <a-tabs v-model:activeKey="activeTab" size="large">
      <!-- Gap分析 -->
      <a-tab-pane key="gap" tab="🔥 技能缺口">
        <a-spin :spinning="loading">
          <a-table 
            :columns="gapColumns" 
            :data-source="gaps" 
            :row-key="record => record.skill"
            :pagination="{ pageSize: 15 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'gap_score'">
                <a-tag :color="getGapColor(record.gap_score)">
                  {{ record.gap_score.toFixed(1) }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-typography-text type="warning">{{ record.action }}</a-typography-text>
              </template>
            </template>
          </a-table>
        </a-spin>
      </a-tab-pane>
      
      <!-- 课程健康度 -->
      <a-tab-pane key="health" tab="📈 课程健康度">
        <a-spin :spinning="loading">
          <a-table 
            :columns="courseColumns" 
            :data-source="courses" 
            :row-key="record => record.name"
            :pagination="{ pageSize: 15 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'job_relevance'">
                <a-progress 
                  :percent="Math.round(record.job_relevance * 100)" 
                  :stroke-color="getRelevanceColor(record.job_relevance)"
                  :show-info="true"
                  style="width: 100px; margin: 0;"
                />
              </template>
              <template v-else-if="column.key === 'salary_impact'">
                <span :style="{ color: record.salary_impact >= 0 ? '#52c41a' : '#ff4d4f' }">
                  {{ record.salary_impact >= 0 ? '+' : '' }}{{ (record.salary_impact * 100).toFixed(0) }}%
                </span>
              </template>
              <template v-else-if="column.key === 'trend'">
                <a-tag :color="getTrendColor(record.trend)">
                  {{ record.trend }}
                </a-tag>
              </template>
            </template>
          </a-table>
        </a-spin>
      </a-tab-pane>
      
      <!-- 改革建议 -->
      <a-tab-pane key="reform" tab="💡 改革建议">
        <a-spin :spinning="loading">
          <div v-if="reformSuggestions">
            <a-alert 
              :message="reformSuggestions.summary" 
              type="warning" 
              show-icon 
              style="margin-bottom: 24px"
            />
            
            <a-row :gutter="24">
              <a-col :span="12">
                <a-card title="🔥 急需技能" size="small">
                  <a-list :data-source="reformSuggestions.urgent_skills" size="small">
                    <template #renderItem="{ item }">
                      <a-list-item>
                        <a-tag color="red">{{ item.skill }}</a-tag>
                        需求: {{ item.demand }} 职位
                      </a-list-item>
                    </template>
                  </a-list>
                </a-card>
              </a-col>
              <a-col :span="12">
                <a-card title="⚠️ 低效课程" size="small">
                  <a-list :data-source="reformSuggestions.low_relevance_courses" size="small">
                    <template #renderItem="{ item }">
                      <a-list-item>
                        {{ item.course }}
                        <a-tag color="orange">关联度 {{ (item.relevance * 100).toFixed(0) }}%</a-tag>
                      </a-list-item>
                    </template>
                  </a-list>
                </a-card>
              </a-col>
            </a-row>
          </div>
        </a-spin>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { universityApi } from '@/api'

const activeTab = ref('gap')
const loading = ref(false)
const gaps = ref([])
const courses = ref([])
const reformSuggestions = ref(null)

const gapColumns = [
  { title: '技能', dataIndex: 'skill', key: 'skill' },
  { title: '市场需求', dataIndex: 'market_demand', key: 'market_demand', sorter: (a, b) => b.market_demand - a.market_demand },
  { title: '课程供给', dataIndex: 'supply_courses', key: 'supply_courses' },
  { title: '缺口分数', key: 'gap_score', sorter: (a, b) => b.gap_score - a.gap_score },
  { title: '建议操作', key: 'action' }
]

const courseColumns = [
  { title: '课程名称', dataIndex: 'name', key: 'name' },
  { title: '选课人数', dataIndex: 'enrollment', key: 'enrollment', sorter: (a, b) => b.enrollment - a.enrollment },
  { title: '教授技能数', dataIndex: 'skill_count', key: 'skill_count' },
  { title: '就业关联度', key: 'job_relevance', width: 150, sorter: (a, b) => b.job_relevance - a.job_relevance },
  { title: '薪资贡献', key: 'salary_impact', sorter: (a, b) => b.salary_impact - a.salary_impact },
  { title: '趋势', key: 'trend' }
]

const highRelevanceCourses = computed(() => 
  courses.value.filter(c => c.job_relevance >= 0.7).length
)

const lowRelevanceCourses = computed(() => 
  courses.value.filter(c => c.job_relevance < 0.3).length
)

const getGapColor = (score) => {
  if (score >= 100) return 'red'
  if (score >= 50) return 'orange'
  return 'blue'
}

const getRelevanceColor = (relevance) => {
  if (relevance >= 0.7) return '#52c41a'
  if (relevance >= 0.4) return '#1890ff'
  return '#ff4d4f'
}

const getTrendColor = (trend) => {
  if (trend.includes('上升')) return 'green'
  if (trend.includes('下降')) return 'red'
  return 'blue'
}

const fetchData = async () => {
  loading.value = true
  try {
    const [gapRes, courseRes, reformRes] = await Promise.all([
      universityApi.analyzeSkillGap(20),
      universityApi.evaluateCourses(30),
      universityApi.getReformSuggestions()
    ])
    
    gaps.value = gapRes.data.gaps
    courses.value = courseRes.data.courses
    reformSuggestions.value = reformRes.data
    
    message.success('数据加载完成')
  } catch (error) {
    message.error('数据加载失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.university-portal {
  max-width: 1400px;
  margin: 0 auto;
}

.stat-cards {
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
  text-align: center;
}

.stat-gap { border-left: 4px solid #fa8c16; }
.stat-courses { border-left: 4px solid #1890ff; }
.stat-high { border-left: 4px solid #52c41a; }
.stat-low { border-left: 4px solid #ff4d4f; }

:deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

:deep(.ant-table-thead > tr > th) {
  padding: 8px 12px !important;
}

:deep(.ant-table-tbody > tr > td) {
  padding: 8px 12px !important;
}

:deep(.ant-progress) {
  margin-bottom: 0 !important;
}
</style>
