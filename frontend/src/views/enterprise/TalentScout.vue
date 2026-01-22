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
      width="800px"
      :footer="null"
    >
      <div v-if="currentCandidate" style="padding: 10px;">
        <!-- 顶部：基础信息 + 匹配度环形图 -->
        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
          <!-- 左侧：基础信息卡片 -->
          <div style="flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 18px; color: white;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <div style="font-size: 22px; font-weight: 600; margin-bottom: 8px;">{{ currentCandidate.name }}</div>
                <div style="opacity: 0.9; font-size: 13px; margin-bottom: 4px;">🆔 {{ currentCandidate.student_id }}</div>
                <div style="opacity: 0.9; font-size: 13px; margin-bottom: 4px;">🎓 {{ currentCandidate.education }} · {{ currentCandidate.major }}</div>
              </div>
              <!-- 匹配度环形图 -->
              <div style="width: 90px; height: 90px;">
                <v-chart :option="matchRingOption" autoresize style="width: 100%; height: 100%;" />
              </div>
            </div>
          </div>
          
          <!-- 右侧：统计数据 -->
          <div style="display: flex; flex-direction: column; gap: 8px; width: 140px;">
            <div style="background: #f6ffed; border-radius: 8px; padding: 12px; text-align: center; flex: 1;">
              <div style="font-size: 24px; font-weight: 700; color: #52c41a;">{{ currentCandidate.matched_skills?.length || 0 }}</div>
              <div style="font-size: 11px; color: #666;">匹配技能数</div>
            </div>
            <div style="background: #e6f7ff; border-radius: 8px; padding: 12px; text-align: center; flex: 1;">
              <div style="font-size: 24px; font-weight: 700; color: #1890ff;">{{ skillCategories.length }}</div>
              <div style="font-size: 11px; color: #666;">技能类别</div>
            </div>
          </div>
        </div>
        
        <!-- 中部：技能雷达图 + 技能条形图 -->
        <a-row :gutter="16">
          <a-col :span="12">
            <a-card size="small" title="📈 技能分类分布">
              <div style="height: 220px;">
                <v-chart :option="radarOption" autoresize style="width: 100%; height: 100%;" />
              </div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card size="small" title="🏆 技能匹配详情">
              <div style="height: 220px;">
                <v-chart :option="barOption" autoresize style="width: 100%; height: 100%;" />
              </div>
            </a-card>
          </a-col>
        </a-row>
        
        <!-- 底部：技能标签云 -->
        <a-card size="small" title="✨ 匹配技能一览" style="margin-top: 12px;">
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <a-tag 
              v-for="(skill, index) in currentCandidate.matched_skills" 
              :key="skill" 
              :color="getSkillTagColor(index)"
              style="margin: 0; font-size: 13px; padding: 4px 10px;"
            >
              {{ skill }}
            </a-tag>
            <span v-if="!currentCandidate.matched_skills?.length" style="color: #999;">暂无匹配技能</span>
          </div>
        </a-card>
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
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, RadarChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, RadarComponent, GridComponent } from 'echarts/components'

// 注册 ECharts 组件
use([CanvasRenderer, PieChart, RadarChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, RadarComponent, GridComponent])

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
  { title: '能力图 ', key: 'radar', width: 110 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' }
]

// 技能分类映射
const skillCategoryMap = {
  '编程语言': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'ruby', 'php', 'swift', 'kotlin', 'rust', 'typescript', 'scala', 'c语言', 'shell', 'sql'],
  '前端技术': ['vue', 'react', 'angular', 'html', 'css', 'webpack', 'node', 'jquery', 'bootstrap', 'typescript'],
  '后端技术': ['spring', 'django', 'flask', 'express', 'mybatis', 'hibernate', 'redis', 'nginx', 'docker', 'kubernetes'],
  '数据技术': ['mysql', 'mongodb', 'postgresql', 'oracle', 'elasticsearch', 'hbase', 'hive', 'spark', 'hadoop', 'flink'],
  '人工智能': ['机器学习', '深度学习', 'tensorflow', 'pytorch', 'keras', 'nlp', '自然语言', '计算机视觉', 'opencv', '神经网络']
}

// 技能分类计算
const skillCategories = computed(() => {
  if (!currentCandidate.value?.matched_skills) return []
  
  const skills = currentCandidate.value.matched_skills
  const categories = {}
  
  for (const skill of skills) {
    if (!skill) continue
    const skillLower = skill.toLowerCase()
    let matched = false
    
    for (const [category, keywords] of Object.entries(skillCategoryMap)) {
      if (keywords.some(kw => skillLower.includes(kw) || kw.includes(skillLower))) {
        categories[category] = (categories[category] || 0) + 1
        matched = true
        break
      }
    }
    
    if (!matched) {
      categories['其他技能'] = (categories['其他技能'] || 0) + 1
    }
  }
  
  return Object.entries(categories).map(([name, count]) => ({ name, count }))
})

// 匹配度环形图配置
const matchRingOption = computed(() => {
  const percent = Math.round((currentCandidate.value?.match_score || 0) * 100)
  return {
    series: [{
      type: 'pie',
      radius: ['65%', '85%'],
      center: ['50%', '50%'],
      silent: true,
      label: {
        show: true,
        position: 'center',
        formatter: `${percent}%`,
        fontSize: 18,
        fontWeight: 'bold',
        color: '#fff'
      },
      data: [
        { value: percent, itemStyle: { color: percent >= 70 ? '#52c41a' : percent >= 50 ? '#1890ff' : '#faad14' } },
        { value: 100 - percent, itemStyle: { color: 'rgba(255,255,255,0.2)' } }
      ]
    }]
  }
})

// 雷达图配置
const radarOption = computed(() => {
  const categories = skillCategories.value
  if (categories.length === 0) {
    return {
      title: { text: '暂无技能数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    }
  }
  
  const maxCount = Math.max(...categories.map(c => c.count), 3)
  
  return {
    tooltip: { trigger: 'item' },
    radar: {
      indicator: categories.map(c => ({ name: c.name, max: maxCount })),
      radius: '65%',
      axisName: { color: '#666', fontSize: 11 },
      splitArea: { areaStyle: { color: ['#f0f5ff', '#e6f7ff', '#f6ffed', '#fff7e6'] } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: categories.map(c => c.count),
        name: '技能分布',
        areaStyle: { color: 'rgba(102, 126, 234, 0.4)' },
        lineStyle: { color: '#667eea', width: 2 },
        itemStyle: { color: '#667eea' }
      }]
    }]
  }
})

// 条形图配置
const barOption = computed(() => {
  const skills = currentCandidate.value?.matched_skills || []
  const displaySkills = skills.slice(0, 8)
  
  if (displaySkills.length === 0) {
    return {
      title: { text: '暂无技能数据', left: 'center', top: 'center', textStyle: { color: '#999', fontSize: 14 } }
    }
  }
  
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '10%', top: '5%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      data: displaySkills.reverse(),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#333', fontSize: 11 }
    },
    series: [{
      type: 'bar',
      data: displaySkills.map((_, i) => ({
        value: displaySkills.length - i,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' }
            ]
          },
          borderRadius: [0, 4, 4, 0]
        }
      })),
      barWidth: 14,
      label: { show: true, position: 'right', color: '#666', fontSize: 10, formatter: '{c}' }
    }]
  }
})

const getScoreColor = (score) => {
  if (score >= 0.8) return '#52c41a'
  if (score >= 0.6) return '#1890ff'
  return '#faad14'
}

// 技能标签颜色
const skillTagColors = ['green', 'blue', 'purple', 'cyan', 'orange', 'magenta', 'volcano', 'geekblue']
const getSkillTagColor = (index) => skillTagColors[index % skillTagColors.length]

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

