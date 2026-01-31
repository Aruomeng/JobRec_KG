<template>
  <div class="student-dashboard">
    <!-- 职业偏好筛选 -->
    <a-card class="filter-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :span="5">
          <a-select v-model:value="filters.city" placeholder="期望城市" style="width: 100%" size="large" allowClear
            :options="availableCities" />
        </a-col>
        <a-col :span="5">
          <a-select v-model:value="filters.salary" placeholder="期望薪资" style="width: 100%" size="large" allowClear>
            <a-select-option value="5000-10000">5K-10K</a-select-option>
            <a-select-option value="10000-20000">10K-20K</a-select-option>
            <a-select-option value="20000-30000">20K-30K</a-select-option>
            <a-select-option value="30000+">30K以上</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="5">
          <a-button type="primary" size="large" block @click="fetchPersonalizedJobs">
            <SearchOutlined /> 获取个性化推荐
          </a-button>
        </a-col>
        <a-col :span="4">
          <a-select v-model:value="recommendMode" size="large" style="width: 100%">
            <a-select-option value="kg">
              <BarChartOutlined /> 知识图谱
            </a-select-option>
            <a-select-option value="ai">
              <RobotOutlined /> AI推荐
            </a-select-option>
            <a-select-option value="hybrid">
              <ThunderboltOutlined /> 三层漏斗
            </a-select-option>
          </a-select>
        </a-col>
        <a-col :span="4">
          <a-button size="large" @click="showSkillDiagnosis" block>
            <ExperimentOutlined /> 技能诊断
          </a-button>
        </a-col>
      </a-row>

      <!-- 高级设置行 -->
      <a-row style="margin-top: 16px" v-if="recommendMode === 'hybrid'">
        <a-col :span="24" style="text-align: right">
          <a-switch v-model:checked="insightMode" checked-children="开启洞察" un-checked-children="洞察模式" />
          <span style="margin-left: 8px; color: #666; font-size: 12px">Beta: 显示AI推理路径</span>
        </a-col>
      </a-row>
    </a-card>

    <!-- Tab切换 -->
    <a-tabs v-model:activeKey="activeTab" size="large" style="margin-bottom: 16px">
      <a-tab-pane key="hot"><template #tab>
          <FireOutlined /> 热门推荐
        </template></a-tab-pane>
      <a-tab-pane key="personalized" :disabled="!userProfile.skills?.length"><template #tab>
          <AimOutlined /> 为你推荐
        </template></a-tab-pane>
    </a-tabs>

    <!-- 推荐结果 -->
    <a-spin :spinning="loading">
      <div class="job-grid">
        <div v-for="(job, index) in paginatedJobs" :key="job.job_id" class="job-card-modern"
          :style="{ animationDelay: `${index * 0.05}s` }" @click="goToDetail(job)">
          <!-- 卡片头部：职位名称和匹配度 -->
          <div class="job-card-header">
            <div class="job-header-content">
              <h3 class="job-title-modern">{{ formatTitle(job.title) }}</h3>
              <div class="job-company-modern">
                <BankOutlined class="company-icon" />
                {{ job.company || '未知公司' }}
              </div>
            </div>
            <!-- 匹配度环形图 -->
            <div class="match-ring" v-if="job.match_score">
              <a-progress type="circle" :percent="Math.round((job.match_rate || 0) * 100)" :width="56" :stroke-width="8"
                :stroke-color="getScoreGradient(job.match_score)">
                <template #format="percent">
                  <span class="match-percent">{{ percent }}</span>
                </template>
              </a-progress>
            </div>
          </div>

          <!-- 薪资突出显示 -->
          <div class="salary-highlight">
            <span class="salary-amount">{{ formatSalary(job.salary) }}</span>
            <span class="salary-unit" v-if="job.salary && job.salary !== '面议'">/月</span>
          </div>

          <!-- 职位元信息标签 -->
          <div class="job-meta-tags">
            <span class="meta-tag location" v-if="job.city">
              <EnvironmentOutlined class="tag-icon" />{{ job.city }}
            </span>
            <span class="meta-tag education" v-if="job.education">
              <BookOutlined class="tag-icon" />{{ job.education }}
            </span>
            <span class="meta-tag industry" v-if="job.industry">
              <AppstoreOutlined class="tag-icon" />{{ job.industry }}
            </span>
          </div>

          <!-- 技能标签区域 -->
          <div class="skill-section" v-if="job.required_skills?.length">
            <div class="skill-label">技能要求</div>
            <div class="skill-tags-modern">
              <a-tag v-for="skill in job.required_skills.slice(0, 4)" :key="skill"
                :class="['skill-tag', job.matched_skills?.includes(skill) ? 'matched' : 'unmatched']">
                <span class="skill-check" v-if="job.matched_skills?.includes(skill)">✓</span>
                {{ skill }}
              </a-tag>
              <a-tag v-if="job.required_skills.length > 4" class="skill-tag more">
                +{{ job.required_skills.length - 4 }}
              </a-tag>
            </div>
          </div>

          <!-- 推荐理由 -->
          <div class="job-reason-modern" v-if="job.explanation">
            <BulbOutlined class="reason-icon" />
            <div class="reason-text">{{ job.explanation }}</div>
          </div>

          <!-- 底部操作区 -->
          <div class="job-card-footer">
            <span class="view-detail">查看详情 →</span>
          </div>
        </div>
      </div>

      <a-empty v-if="!loading && displayJobs.length === 0" description="暂无推荐，请完善个人信息获取个性化推荐" />

      <!-- 分页组件 -->
      <div class="pagination-container" v-if="displayJobs.length > 0">
        <a-pagination v-model:current="currentPage" v-model:pageSize="pageSize" :total="displayJobs.length"
          :pageSizeOptions="['12', '24', '48', '96']" show-size-changer show-quick-jumper
          :show-total="total => `共 ${total} 个职位`" @change="window.scrollTo({ top: 0, behavior: 'smooth' })" />
      </div>
    </a-spin>

    <!-- 登录弹窗 -->
    <a-modal v-model:open="showLoginModal" :footer="null" width="400px">
      <template #title>
        <KeyOutlined /> 学生登录
      </template>
      <a-form :model="loginForm" layout="vertical" @finish="handleLogin">
        <a-alert message="未登录仅可使用 AI/KG 推荐，登录后解锁漏斗推荐！" type="info" show-icon style="margin-bottom: 24px" />

        <a-form-item label="用户名 / 手机号" name="username" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="loginForm.username" placeholder="请输入您的昵称或手机号" size="large">
            <template #prefix>
              <UserOutlined />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="loginForm.password" placeholder="请输入密码（新用户将自动注册）" size="large">
            <template #prefix>
              <LockOutlined />
            </template>
          </a-input-password>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" block size="large" :loading="loginLoading">
            立即登录 / 注册
          </a-button>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 简历上传弹窗 -->
    <a-modal v-model:open="showResumeUpload" :footer="null">
      <template #title>
        <FileTextOutlined /> 上传简历 (支持PDF/Word)
      </template>
      <a-upload-dragger name="file" :multiple="false" :customRequest="handleResumeUpload" accept=".pdf,.docx,.doc,.txt">
        <p class="ant-upload-drag-icon">
          <inbox-outlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p class="ant-upload-hint">支持解析简历中的技能关键词，自动匹配推荐</p>
      </a-upload-dragger>
    </a-modal>

    <!-- 技能诊断弹窗 - 紧凑布局 -->
    <a-modal v-model:open="diagnosisVisible" title="" width="1000px" :footer="null" :body-style="{ padding: '0' }"
      class="diagnosis-modal" centered>
      <div v-if="diagnosis" class="diagnosis-compact">
        <!-- 顶部条：职位+匹配度+统计数字 -->
        <div class="diag-header">
          <div class="diag-title">
            <span class="position">{{ diagnosis.expected_position || '未设置' }}</span>
            <span class="edu">{{ diagnosis.education }} · {{ diagnosis.major }}</span>
          </div>
          <div class="diag-match-wrapper">
            <a-progress type="circle" :percent="diagnosis.position_analysis?.match_rate || 0" :size="80"
              :stroke-width="8" :trail-color="'rgba(255,255,255,0.25)'"
              :stroke-color="{ '0%': '#22C55E', '100%': '#06B6D4' }">
              <template #format="percent">
                <div class="match-ring-inner">
                  <span class="match-num">{{ percent }}</span>
                  <span class="match-unit">%</span>
                </div>
              </template>
            </a-progress>
            <div class="match-label">匹配度</div>
          </div>
          <div class="diag-stats">
            <div class="stat"><span class="n green">{{ diagnosis.skills_analysis?.all_skills?.length || 0 }}</span><span
                class="l">总技能</span></div>
            <div class="stat"><span class="n blue">{{ diagnosis.position_analysis?.matched_skills?.length || 0
                }}</span><span class="l">已匹配</span></div>
            <div class="stat"><span class="n orange">{{ diagnosis.position_analysis?.missing_skills?.length || 0
                }}</span><span class="l">待学习</span></div>
            <div class="stat"><span class="n purple">{{ diagnosis.market_analysis?.market_match_rate || 0
                }}%</span><span class="l">市场</span></div>
          </div>
        </div>

        <!-- 主体：三列布局 -->
        <div class="diag-body">
          <!-- 左列：雷达图+同行对比 -->
          <div class="col col-left">
            <div class="card">
              <div class="card-title">
                <PieChartOutlined /> 技能分布
              </div>
              <div style="height: 180px;">
                <v-chart :option="skillRadarOption" autoresize style="width: 100%; height: 100%;" />
              </div>
            </div>
            <div class="card">
              <div class="card-title">
                <TeamOutlined /> 同行对比
              </div>
              <div class="peer-row">
                <div class="peer-item">
                  <a-progress type="circle"
                    :percent="Math.min(100, ((diagnosis.skills_analysis?.all_skills?.length || 0) / Math.max(1, diagnosis.peer_comparison?.avg_skills_count || 1)) * 100)"
                    :size="48" :stroke-width="6" stroke-color="#1890ff">
                    <template #format><span class="peer-n">{{ diagnosis.skills_analysis?.all_skills?.length || 0
                        }}</span></template>
                  </a-progress>
                  <span class="peer-l">您</span>
                </div>
                <span class="vs">VS</span>
                <div class="peer-item">
                  <a-progress type="circle" :percent="100" :size="48" :stroke-width="6" stroke-color="#722ed1">
                    <template #format><span class="peer-n">{{ diagnosis.peer_comparison?.avg_skills_count || 0
                        }}</span></template>
                  </a-progress>
                  <span class="peer-l">同行</span>
                </div>
              </div>
              <div class="peer-tags">
                <a-tag v-for="skill in diagnosis.peer_comparison?.top_skills_in_peers?.slice(0, 4)" :key="skill"
                  color="purple" size="small">{{ skill }}</a-tag>
              </div>
            </div>
          </div>

          <!-- 中列：技能匹配 -->
          <div class="col col-mid">
            <div class="card full">
              <div class="card-title">
                <AimOutlined /> 技能匹配
              </div>
              <div class="skill-section matched">
                <div class="skill-head">
                  <CheckCircleOutlined /> 已掌握 <span class="cnt">{{ diagnosis.position_analysis?.matched_skills?.length
                    || 0
                  }}</span>
                </div>
                <div class="tags">
                  <span v-for="skill in diagnosis.position_analysis?.matched_skills?.slice(0, 10)" :key="skill"
                    class="tag green">{{ skill }}</span>
                  <span v-if="(diagnosis.position_analysis?.matched_skills?.length || 0) > 10" class="tag more">+{{
                    diagnosis.position_analysis.matched_skills.length - 10 }}</span>
                </div>
              </div>
              <div class="skill-section missing">
                <div class="skill-head">
                  <BookOutlined /> 待学习 <span class="cnt">{{ diagnosis.position_analysis?.missing_skills?.length
                    || 0
                  }}</span>
                </div>
                <div class="tags">
                  <span v-for="skill in diagnosis.position_analysis?.missing_skills?.slice(0, 10)" :key="skill"
                    class="tag orange">{{ skill }}</span>
                  <span v-if="(diagnosis.position_analysis?.missing_skills?.length || 0) > 10" class="tag more">+{{
                    diagnosis.position_analysis.missing_skills.length - 10 }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 右列：课程推荐+建议 -->
          <div class="col col-right">
            <div class="card">
              <div class="card-title">
                <BookOutlined /> 推荐课程
              </div>
              <div class="course-list">
                <div v-for="course in diagnosis.recommended_courses?.slice(0, 3)" :key="course.name"
                  class="course-item">
                  <span class="c-name">{{ course.name }}</span>
                  <a-tag v-for="s in course.covers?.slice(0, 1)" :key="s" size="small" color="blue">{{ s }}</a-tag>
                </div>
                <div v-if="!diagnosis.recommended_courses?.length" class="course-empty">
                  <TrophyOutlined /> 技能完备
                </div>
              </div>
            </div>
            <div class="card">
              <div class="card-title">
                <BulbOutlined /> 诊断建议
              </div>
              <div class="advice">
                <div v-for="(s, i) in diagnosis.diagnosis?.suggestions?.slice(0, 2)" :key="i" class="advice-item">• {{ s
                  }}
                </div>
                <div v-if="!diagnosis.diagnosis?.suggestions?.length" class="advice-item success">
                  <TrophyOutlined /> 继续保持!
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
defineOptions({
  name: 'StudentDashboard'
})

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message, notification } from 'ant-design-vue'
import { InboxOutlined, UserOutlined, LockOutlined, SearchOutlined, BarChartOutlined, RobotOutlined, ThunderboltOutlined, ExperimentOutlined, BankOutlined, EnvironmentOutlined, BookOutlined, AppstoreOutlined, BulbOutlined, FireOutlined, AimOutlined, CheckCircleOutlined, EditOutlined, PieChartOutlined, CheckOutlined, TeamOutlined, TrophyOutlined, KeyOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import { studentApi, commonApi } from '@/api'
import { useUserStore } from '@/stores/user'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, RadarComponent } from 'echarts/components'

// 注册 ECharts 组件
use([CanvasRenderer, RadarChart, TitleComponent, TooltipComponent, RadarComponent])

const router = useRouter()
const userStore = useUserStore()

// 用户资料 - 从 Pinia store 获取
const userProfile = ref({ ...userStore.userProfile })

// 监听 store 变化同步到本地 ref
watch(() => userStore.userProfile, (newVal) => {
  userProfile.value = { ...newVal }
}, { deep: true })

const isLoggedIn = computed(() => userStore.isLoggedIn)


const showResumeUpload = ref(false)
const showLoginModal = ref(false)
const loginLoading = ref(false)
const loginForm = ref({ username: '', password: '' })

const profileForm = ref({
  name: userProfile.value.name || '',
  student_id: userProfile.value.student_id || '',
  education: userProfile.value.education || '',
  major: userProfile.value.major || '',
  skills: userProfile.value.skills || [],
  courses: userProfile.value.courses || [],  // 已选课程
  expectedJob: userProfile.value.expectedJob || ''
})

const handleLogin = async (values) => {
  loginLoading.value = true
  try {
    const { data } = await studentApi.login(values.username, values.password)
    if (data.code === 200) {
      message.success('登录成功')
      const userData = data.data

      // 安全获取本地 array，防止 undefined
      const localSkills = Array.isArray(userProfile.value.skills) ? userProfile.value.skills : []
      const localCourses = Array.isArray(userProfile.value.courses) ? userProfile.value.courses : []

      const remoteSkills = Array.isArray(userData.skills) ? userData.skills : []
      const remoteCourses = Array.isArray(userData.courses) ? userData.courses : []

      // 合并技能和课程 (服务器数据优先，但也保留本地未同步的可能数据)
      const mergedSkills = Array.from(new Set([...localSkills, ...remoteSkills]))
      const mergedCourses = Array.from(new Set([...localCourses, ...remoteCourses]))

      // 更新用户信息（包括所有后端返回的字段）
      userProfile.value = {
        ...userProfile.value,
        student_id: userData.student_id,
        name: userData.name,
        education: userData.education || userProfile.value.education,
        major: userData.major || userProfile.value.major,
        expectedJob: userData.expected_position || userProfile.value.expectedJob,  // 后端用 expected_position
        skills: mergedSkills,
        courses: mergedCourses
      }

      // 更新本地存储
      localStorage.setItem('userProfile', JSON.stringify(userProfile.value))

      // 更新表单
      profileForm.value.student_id = userData.student_id
      profileForm.value.name = userData.name
      profileForm.value.education = userData.education || ''
      profileForm.value.major = userData.major || ''
      profileForm.value.expectedJob = userData.expected_position || ''
      profileForm.value.skills = mergedSkills
      profileForm.value.courses = mergedCourses

      showLoginModal.value = false

    }
  } catch (e) {
    message.error('登录失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loginLoading.value = false
  }
}

const logout = () => {
  userStore.logout()
  message.success('已退出登录')
  window.location.reload()
}

const useModel = ref(false)
const recommendMode = ref('kg') // kg, ai, hybrid
const insightMode = ref(false) // 洞察模式开关
const resumeLoading = ref(false)

// 课程相关
const courseOptions = ref([])
const coursesLoading = ref(false)

// 常用技能选项
const commonSkills = [
  { value: 'Python', label: 'Python' },
  { value: 'Java', label: 'Java' },
  { value: 'JavaScript', label: 'JavaScript' },
  { value: 'Vue', label: 'Vue' },
  { value: 'React', label: 'React' },
  { value: 'SQL', label: 'SQL' },
  { value: '机器学习', label: '机器学习' },
  { value: '数据分析', label: '数据分析' }
]

// 筛选条件
const filters = ref({
  city: null,
  salary: null
})

// 数据状态
const activeTab = ref('hot')
const loading = ref(false)
const hotJobs = ref([])
const personalizedJobs = ref([])
const diagnosisVisible = ref(false)
const diagnosis = ref(null)
const diagnosisTab = ref('skills') // 诊断弹窗 Tab: skills, peers, courses

// 分页状态
const currentPage = ref(1)
const pageSize = ref(12)

// 监听Tab切换，重置分页
watch(activeTab, () => {
  currentPage.value = 1
})

// 计算属性
const displayJobs = computed(() => {
  const jobs = activeTab.value === 'hot' ? hotJobs.value : personalizedJobs.value
  return jobs
})

const paginatedJobs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return displayJobs.value.slice(start, end)
})

// 技能分类分布（用于诊断报告图表）
const skillCategories = computed(() => {
  if (!diagnosis.value) return []

  // 使用用户技能进行分类
  const allSkills = diagnosis.value.skills_analysis?.all_skills || []
  const userSkillsList = allSkills.filter(s => typeof s === 'string')

  if (userSkillsList.length === 0) return []

  // 定义技能分类
  const categories = {
    '编程语言': { keywords: ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'ruby', 'php', 'swift', 'kotlin', 'rust', 'typescript', 'scala', 'c语言', 'shell'], color: '#1890ff', count: 0 },
    '框架技术': { keywords: ['vue', 'react', 'angular', 'spring', 'django', 'flask', 'node', 'express', 'mybatis', 'hibernate', 'bootstrap', 'jquery', 'tensorflow', 'pytorch', 'keras'], color: '#52c41a', count: 0 },
    '数据库': { keywords: ['mysql', 'mongodb', 'redis', 'postgresql', 'oracle', 'sql', 'elasticsearch', 'hbase', 'sqlite', 'hive', 'spark'], color: '#722ed1', count: 0 },
    '工具平台': { keywords: ['git', 'docker', 'kubernetes', 'linux', 'jenkins', 'nginx', 'aws', 'azure', 'maven', 'gradle', 'webpack', 'vscode', 'idea'], color: '#fa8c16', count: 0 }
  }

  // 将用户技能分类
  for (const skill of userSkillsList) {
    if (!skill) continue
    const skillLower = skill.toLowerCase()
    for (const catInfo of Object.values(categories)) {
      if (catInfo.keywords.some(kw => skillLower.includes(kw))) {
        catInfo.count++
        break
      }
    }
  }

  // 构建结果 - 显示用户掌握技能的分类比例
  const totalUserSkills = userSkillsList.length
  return Object.entries(categories)
    .map(([name, info]) => ({
      name,
      count: info.count,
      total: totalUserSkills,
      percent: Math.round(info.count / totalUserSkills * 100),
      color: info.color
    }))
    .filter(cat => cat.count > 0) // 只显示有技能的分类
    .slice(0, 4)
})

// 技能雷达图配置
const skillRadarOption = computed(() => {
  const cats = skillCategories.value
  if (!cats.length) {
    return {
      radar: { indicator: [{ name: '暂无数据', max: 100 }] },
      series: [{ type: 'radar', data: [{ value: [0] }] }]
    }
  }

  return {
    tooltip: {},
    radar: {
      indicator: cats.map(c => ({ name: c.name, max: 100 })),
      radius: '65%',
      splitNumber: 4,
      axisName: { color: '#333', fontSize: 12 },
      splitArea: { areaStyle: { color: ['rgba(102, 126, 234, 0.1)', 'rgba(102, 126, 234, 0.2)'] } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: cats.map(c => c.percent),
        name: '技能分布',
        areaStyle: { color: 'rgba(102, 126, 234, 0.4)' },
        lineStyle: { color: '#667eea', width: 2 },
        itemStyle: { color: '#667eea' }
      }]
    }]
  }
})

// 诊断匹配度渐变色
const getMatchGradientDiagnosis = (percent) => {
  if (percent >= 70) return { '0%': '#52c41a', '100%': '#13c2c2' }
  if (percent >= 50) return { '0%': '#1890ff', '100%': '#722ed1' }
  if (percent >= 30) return { '0%': '#faad14', '100%': '#fa8c16' }
  return { '0%': '#ff4d4f', '100%': '#f5222d' }
}

const getScoreColor = (score) => {
  if (score >= 0.8) return '#52c41a'
  if (score >= 0.6) return '#1890ff'
  if (score >= 0.4) return '#faad14'
  return '#ff4d4f'
}

// 匹配度渐变色
const getScoreGradient = (score) => {
  if (score >= 0.7) return { '0%': '#52c41a', '100%': '#13c2c2' }
  if (score >= 0.5) return { '0%': '#1890ff', '100%': '#722ed1' }
  if (score >= 0.3) return { '0%': '#faad14', '100%': '#fa8c16' }
  return { '0%': '#ff4d4f', '100%': '#f5222d' }
}

const formatSalary = (salary) => {
  if (!salary || salary === 'nan' || salary === 'NaN') return '面议'
  return salary
}

// 格式化职位标题，去除括号及其内容
const formatTitle = (title) => {
  if (!title) return '未知职位'
  // 移除中英文圆括号、方括号及其内容
  return title
    .replace(/[\(（][^\)）]*[\)）]/g, '')  // 圆括号
    .replace(/[\[【][^\]】]*[\]】]/g, '')  // 方括号
    .trim()
}

const availableCities = ref([])

// 方法
const fetchCities = async () => {
  try {
    const { data } = await commonApi.getCities()
    if (data.cities) {
      availableCities.value = data.cities.map(c => ({ value: c, label: c }))
    }
  } catch (e) {
    console.error('获取城市失败', e)
    // 默认
    availableCities.value = [
      { value: '北京', label: '北京' },
      { value: '上海', label: '上海' },
      { value: '广州', label: '广州' },
      { value: '深圳', label: '深圳' },
      { value: '杭州', label: '杭州' }
    ]
  }
}

const fetchHotJobs = async () => {
  loading.value = true
  currentPage.value = 1 // 重置分页
  try {
    // 调用后端获取热门职位
    const { data } = await studentApi.getHotJobs(20)
    hotJobs.value = data.jobs || []
  } catch (error) {
    // 使用备选方案：获取一个示例学生的推荐
    try {
      const { data } = await studentApi.recommendJobs('STU0001', 20)
      hotJobs.value = data.recommendations || []
    } catch (e) {
      console.error('获取热门职位失败', e)
    }
  } finally {
    loading.value = false
  }
}
// ... (rest of methods)

// 监听推荐模式，未登录时拦截漏斗模式
watch(recommendMode, (newMode) => {
  if (newMode === 'hybrid' && !isLoggedIn.value) {
    message.warning('三层漏斗推荐仅对登录用户开放，请先登录！')
    showLoginModal.value = true
    // 延迟重置为 KG 模式，避免 UI 直接切换显示未授权内容
    setTimeout(() => {
      recommendMode.value = 'kg'
    }, 100)
  }
})

// 加载可选课程列表（根据专业）
const fetchCourses = async (major = null) => {
  coursesLoading.value = true
  try {
    const { data } = await studentApi.getCourses(major)
    courseOptions.value = (data.courses || []).map(c => ({
      value: c.name,
      label: c.name,
      skills: c.skills
    }))
  } catch (e) {
    console.error('获取课程列表失败', e)
  } finally {
    coursesLoading.value = false
  }
}

// 监听专业变化，自动加载相关课程
watch(() => profileForm.value.major, (newMajor) => {
  if (newMajor) {
    fetchCourses(newMajor)
  }
}, { immediate: false })

// 课程搜索过滤
const filterCourse = (input, option) => {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

// 刷新用户数据（从后端获取最新技能和课程）
const refreshUserData = async () => {
  if (!isLoggedIn.value || !userProfile.value.student_id) return

  try {
    const { data } = await studentApi.getProfile(userProfile.value.student_id)
    if (data.code === 200) {
      const userData = data.data
      const remoteSkills = Array.isArray(userData.skills) ? userData.skills : []
      const remoteCourses = Array.isArray(userData.courses) ? userData.courses : []

      // 使用后端数据更新（后端数据为准）
      userProfile.value.skills = remoteSkills
      userProfile.value.courses = remoteCourses
      profileForm.value.skills = remoteSkills
      profileForm.value.courses = remoteCourses

      // 更新 localStorage
      localStorage.setItem('userProfile', JSON.stringify(userProfile.value))
      console.log('用户数据已刷新，技能数量:', remoteSkills.length, '课程数量:', remoteCourses.length)
    }
  } catch (e) {
    console.log('刷新用户数据失败:', e.message)
  }
}


// 生命周期
onMounted(() => {
  fetchCities()
  fetchHotJobs()
  // 加载课程时使用当前专业（如果有）
  fetchCourses(profileForm.value.major || null)
  // 如果已登录，刷新用户数据
  if (isLoggedIn.value) {
    refreshUserData()
  }
})
const fetchPersonalizedJobs = async () => {
  // 如果是 KG/AI 模式但未登录，需要提示完善信息（至少有技能）
  // 如果是 Hybrid 模式，必须登录

  if (recommendMode.value === 'hybrid' && !isLoggedIn.value) {
    showLoginModal.value = true
    return
  }

  if (!userProfile.value.skills?.length) {
    message.warning('请先完善个人信息，添加您的技能')
    router.push('/student/center')
    return
  }

  loading.value = true
  activeTab.value = 'personalized'
  currentPage.value = 1 // 重置分页

  try {
    let response
    const payload = {
      skills: userProfile.value.skills,
      city: filters.value.city,
      salary: filters.value.salary,
      top_k: 500,
      student_id: userProfile.value.student_id // 可能是空或登录ID
    }

    if (recommendMode.value === 'hybrid') {
      // 三层漏斗混合推荐 (使用位置参数调用)
      response = await studentApi.hybridRecommend(
        userProfile.value.student_id, // studentId
        500, // finalK - 返回所有匹配度>=30%的结果
        500, // recallK (default)
        50, // rankK (default)
        null, // weights (default)
        filters.value.city, // city
        filters.value.salary, // salary
        insightMode.value // includeInsight
      )

      notification.success({
        message: '三层漏斗推荐完成',
        description: `Layer1召回 → Layer2深度精排 → Layer3神经符号融合。已为您精选 ${response.data.recommendations?.length || 0} 个最优匹配。`,
        placement: 'topRight',
        duration: 5
      })
    } else if (recommendMode.value === 'ai') {
      // AI 推荐模式
      response = await studentApi.recommendBySkills(
        payload.skills,
        payload.top_k,
        payload.city,
        payload.student_id,
        true // useModel
      )

      const data = response.data
      if (data.algorithm && data.algorithm.includes('Deep Learning')) {
        notification.info({
          message: 'AI 深度学习推荐已启用',
          description: '正在使用 GraphSAGE 模型为您计算职位匹配度',
          placement: 'bottomRight',
          duration: 3
        })
      }
    } else {
      // KG 模式 (默认)
      response = await studentApi.recommendBySkills(
        payload.skills,
        payload.top_k,
        payload.city,
        payload.student_id,
        false // useModel
      )
    }

    personalizedJobs.value = response.data.recommendations || []

    if (personalizedJobs.value.length === 0) {
      message.info('暂时没有匹配的职位，请尝试调整技能或筛选条件')
    }
  } catch (error) {
    console.error('获取推荐失败', error)
    const errorMsg = error.response?.data?.detail || error.message || '未知错误'

    if (errorMsg.includes("无嵌入")) {
      message.warn("您的学习记录较少，正在启用冷启动策略...")
      // 冷启动重试或提示
    } else {
      message.error(`推荐失败: ${errorMsg}`)
    }
  } finally {
    loading.value = false
  }
}

const showSkillDiagnosis = async () => {
  if (!userProfile.value.skills?.length) {
    message.warning('请先完善个人信息')
    router.push('/student/center')
    return
  }

  try {
    // 使用当前用户的student_id和技能列表
    const studentId = userProfile.value.student_id || 'anonymous'
    const skills = userProfile.value.skills || []
    const { data } = await studentApi.diagnoseSkills(studentId, skills)
    diagnosis.value = data
    diagnosisVisible.value = true
  } catch (error) {
    console.error('技能诊断失败:', error)
    message.error('获取诊断失败')
  }
}

const saveProfile = async () => {
  userProfile.value = { ...profileForm.value }
  // 使用 store 更新用户资料
  userStore.updateProfile(userProfile.value)
  message.success('个人信息已保存')

  // 同步完整档案到后端 (Major, Expected Position, Skills, Courses)
  try {
    await studentApi.updateProfile({
      student_id: userProfile.value.student_id,
      name: userProfile.value.name,
      education: userProfile.value.education,
      major: userProfile.value.major,
      expected_position: userProfile.value.expectedJob, // 注意字段映射
      skills: userProfile.value.skills,
      courses: userProfile.value.courses // 添加课程
    })
    console.log('完整档案同步成功')
  } catch (e) {
    console.error('档案同步失败:', e)
    // 不阻断流程，仅记录
  }

}

const handleResumeUpload = async (options) => {
  const { file, onSuccess, onError } = options
  const formData = new FormData()
  formData.append('file', file)

  try {
    resumeLoading.value = true
    const { data } = await studentApi.uploadResume(formData)
    if (data.skills && data.skills.length > 0) {
      // 合并技能
      const newSkills = new Set([...profileForm.value.skills, ...data.skills])
      profileForm.value.skills = Array.from(newSkills)

      // 更新用户资料
      userProfile.value.skills = profileForm.value.skills
      localStorage.setItem('userProfile', JSON.stringify(userProfile.value))

      message.success(`解析成功！提取到 ${data.skills.length} 个技能`)
      showResumeUpload.value = false
      router.push('/student/center') // 跳转到个人中心确认资料
      if (onSuccess) onSuccess(data)
    } else {
      message.warning('未能识别出有效技能，请手动添加')
      if (onSuccess) onSuccess(data)
    }
  } catch (err) {
    if (onError) onError(err)
    message.error('上传失败')
  } finally {
    resumeLoading.value = false
  }
}

const goToDetail = (job) => {
  const jobId = encodeURIComponent(job.job_id)
  router.push({
    name: 'jobDetail',
    params: { id: jobId },
    query: {
      title: job.title,
      salary: job.salary,
      company: job.company,
      city: job.city,
      // 传递推荐数据
      matchRate: job.match_rate || 0,
      matchedSkills: JSON.stringify(job.matched_skills || []),
      recommendMode: recommendMode.value
    }
  })
}

// 生命周期
onMounted(() => {
  fetchHotJobs()
})
</script>

<style scoped>
.student-dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 16px;
}

/* 主题按钮 - 紫蓝色 */
:deep(.ant-btn-primary) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.35);
  transition: all 0.25s ease;
}

:deep(.ant-btn-primary:hover) {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%) !important;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.45);
  transform: translateY(-1px);
}

.filter-card {
  margin-bottom: 24px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.1);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(102, 126, 234, 0.08);
}

/* 岗位卡片网格 */
.job-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

/* 现代化岗位卡片 - Design System */
.job-card-modern {
  background: white;
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.25s ease-out;
  border: 1px solid rgba(3, 105, 161, 0.08);
  box-shadow: 0 2px 12px rgba(3, 105, 161, 0.06);
  animation: fadeInUp 0.4s ease-out forwards;
  opacity: 0;
  position: relative;
  overflow: hidden;
}

.job-card-modern::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.job-card-modern:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(3, 105, 161, 0.15);
  border-color: rgba(14, 165, 233, 0.3);
}

.job-card-modern:hover::before {
  transform: scaleX(1);
}

/* 卡片头部 */
.job-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.job-header-content {
  flex: 1;
  padding-right: 12px;
}

.job-title-modern {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.job-company-modern {
  font-size: 14px;
  color: #666;
  display: flex;
  align-items: center;
  gap: 4px;
}

.company-icon {
  font-size: 12px;
}

/* 匹配度环形图 */
.match-ring {
  flex-shrink: 0;
}

.match-percent {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}

/* 薪资突出显示 */
.salary-highlight {
  margin-bottom: 12px;
}

.salary-amount {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.salary-unit {
  font-size: 13px;
  color: #999;
  margin-left: 2px;
}

/* 职位元信息标签 */
.job-meta-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  color: #64748B;
  background: #F8FAFC;
  transition: all 0.2s ease-out;
}

.meta-tag:hover {
  transform: translateY(-1px);
}

.meta-tag.location {
  background: linear-gradient(135deg, #E0F2FE 0%, #BAE6FD 100%);
  color: #0369A1;
}

.meta-tag.education {
  background: linear-gradient(135deg, #F3E8FF 0%, #E9D5FF 100%);
  color: #7C3AED;
}

.meta-tag.industry {
  background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
  color: #D97706;
}

.tag-icon {
  font-size: 11px;
}

/* 技能区域 */
.skill-section {
  margin-bottom: 14px;
}

.skill-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.skill-tags-modern {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  border-radius: 4px !important;
  font-size: 12px !important;
  padding: 2px 8px !important;
  margin: 0 !important;
  border: none !important;
}

.skill-tag.matched {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%) !important;
  color: white !important;
}

.skill-tag.unmatched {
  background: #f0f0f0 !important;
  color: #666 !important;
}

.skill-tag.more {
  background: #e6f7ff !important;
  color: #1890ff !important;
}

.skill-check {
  margin-right: 2px;
}

/* 推荐理由 */
.job-reason-modern {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f0f7ff 0%, #f6ffed 100%);
  border-radius: 8px;
  margin-bottom: 12px;
}

.reason-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.reason-text {
  font-size: 13px;
  color: #555;
  line-height: 1.5;
}

/* 底部操作区 */
.job-card-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}

.view-detail {
  font-size: 13px;
  color: #1890ff;
  font-weight: 500;
  transition: all 0.2s;
}

.job-card-modern:hover .view-detail {
  color: #722ed1;
  transform: translateX(4px);
}

/* 分页容器 */
.pagination-container {
  margin-top: 32px;
  display: flex;
  justify-content: center;
  padding-bottom: 24px;
}

/* 保留旧样式兼容 */
.job-card {
  border-radius: 12px;
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
}

.job-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}

/* ========== 技能诊断弹窗样式 - 紧凑三列布局 ========== */
:deep(.diagnosis-modal .ant-modal-content) {
  border-radius: 12px;
  overflow: hidden;
  padding: 0;
}

:deep(.diagnosis-modal .ant-modal-body) {
  padding: 0;
}

:deep(.diagnosis-modal .ant-modal-close) {
  top: 12px;
  right: 12px;
  color: white;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: all 0.25s ease;
  z-index: 10;
}

:deep(.diagnosis-modal .ant-modal-close:hover) {
  background: rgba(0, 0, 0, 0.5);
  transform: scale(1.1);
}

/* ========== 技能诊断弹窗 - 全新设计 ========== */
.diagnosis-compact {
  background: linear-gradient(180deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 16px;
  overflow: hidden;
  animation: diagFadeIn 0.4s ease-out;
}

@keyframes diagFadeIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(10px);
  }

  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* 顶部条 - 玻璃拟态 */
.diag-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  position: relative;
  overflow: hidden;
}

.diag-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.08'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity: 0.3;
}

.diag-title {
  color: white;
  min-width: 140px;
  position: relative;
  z-index: 1;
}

.diag-title .position {
  display: block;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.diag-title .edu {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 4px;
  display: block;
}

.diag-match-wrapper {
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  animation: matchFadeIn 0.6s ease-out;
}

@keyframes matchFadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

.match-ring-inner {
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.match-ring-inner .match-num {
  font-size: 24px;
  font-weight: 800;
  color: white;
  line-height: 1;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.match-ring-inner .match-unit {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-left: 2px;
}

.match-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}

.diag-stats {
  display: flex;
  gap: 10px;
  margin-left: auto;
  position: relative;
  z-index: 1;
}

.diag-stats .stat {
  text-align: center;
  padding: 8px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
  cursor: default;
}

.diag-stats .stat:hover {
  transform: translateY(-3px);
  background: rgba(255, 255, 255, 0.35);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.diag-stats .n {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.diag-stats .n.green {
  color: #86efac;
}

.diag-stats .n.blue {
  color: #7dd3fc;
}

.diag-stats .n.orange {
  color: #fdba74;
}

.diag-stats .n.purple {
  color: #c4b5fd;
}

.diag-stats .l {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.9);
  margin-top: 2px;
  display: block;
}

/* 三列布局主体 */
.diag-body {
  display: flex;
  gap: 16px;
  padding: 16px;
  max-height: 480px;
  overflow-y: auto;
}

.col {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.col-left {
  width: 28%;
}

.col-mid {
  width: 38%;
}

.col-right {
  width: 34%;
}

/* 卡片 - 玻璃拟态 */
.card {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  padding: 14px;
  flex: 1;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 16px rgba(3, 105, 161, 0.08);
  transition: all 0.3s ease;
  animation: cardSlideUp 0.5s ease-out backwards;
}

.col-left .card:nth-child(1) {
  animation-delay: 0.1s;
}

.col-left .card:nth-child(2) {
  animation-delay: 0.2s;
}

.col-mid .card {
  animation-delay: 0.15s;
}

.col-right .card:nth-child(1) {
  animation-delay: 0.2s;
}

.col-right .card:nth-child(2) {
  animation-delay: 0.25s;
}

@keyframes cardSlideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(3, 105, 161, 0.15);
  border-color: rgba(14, 165, 233, 0.3);
}

.card.full {
  flex: 1;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #0369A1;
  display: flex;
  align-items: center;
  gap: 6px;
}

.card-title .anticon {
  color: #0EA5E9;
}

/* 同行对比 */
.peer-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 10px 0;
}

.peer-item {
  text-align: center;
  transition: transform 0.3s ease;
}

.peer-item:hover {
  transform: scale(1.08);
}

.peer-n {
  font-size: 16px;
  font-weight: 700;
}

.peer-l {
  font-size: 11px;
  color: #64748b;
  display: block;
  margin-top: 4px;
}

.vs {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 700;
  padding: 4px 8px;
  background: #f1f5f9;
  border-radius: 6px;
}

.peer-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  justify-content: center;
}

/* 技能匹配 */
.skill-section {
  padding: 12px;
  border-radius: 10px;
  margin-bottom: 10px;
  transition: all 0.3s ease;
}

.skill-section:hover {
  transform: scale(1.01);
}

.skill-section.matched {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.skill-section.missing {
  background: linear-gradient(135deg, #fff7ed 0%, #fed7aa 50%, #ffedd5 100%);
  border: 1px solid rgba(249, 115, 22, 0.2);
}

.skill-head {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 6px;
}

.skill-section.matched .skill-head {
  color: #166534;
}

.skill-section.missing .skill-head {
  color: #c2410c;
}

.skill-head .cnt {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 6px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.25s ease;
  cursor: default;
}

.tag:hover {
  transform: translateY(-2px) scale(1.05);
}

.tag.green {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
}

.tag.orange {
  background: linear-gradient(135deg, #fb923c 0%, #f97316 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3);
}

.tag.more {
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
}

/* 课程列表 */
.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  transition: all 0.25s ease;
  cursor: pointer;
}

.course-item:hover {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-color: #7dd3fc;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.15);
}

.c-name {
  font-size: 13px;
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
}

.course-empty {
  text-align: center;
  color: #22c55e;
  padding: 16px;
  font-size: 14px;
  font-weight: 500;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* 建议 */
.advice {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.advice-item {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border-left: 3px solid #0ea5e9;
  transition: all 0.25s ease;
}

.advice-item:hover {
  background: #e0f2fe;
  border-left-color: #0369A1;
  transform: translateX(4px);
}

.advice-item.success {
  color: #22c55e;
  text-align: center;
  padding: 14px;
  border-left: none;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
</style>
