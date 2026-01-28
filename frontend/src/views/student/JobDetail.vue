<template>
  <div class="job-detail">
    <!-- 沉浸式头部 -->
    <div class="detail-header">
      <div class="header-bg"></div>
      <div class="header-content">
        <a-button type="text" class="back-btn" @click="() => $router.back()">
          ← 返回
        </a-button>
        <div class="header-main">
          <div class="header-left">
            <h1 class="job-title">{{ jobData.title || '职位详情' }}</h1>
            <div class="company-info">
              <span class="company-name">
                <BankOutlined /> {{ jobData.company }}
              </span>
              <span class="divider" v-if="jobData.city">|</span>
              <span class="city" v-if="jobData.city">
                <EnvironmentOutlined /> {{ jobData.city }}
              </span>
            </div>
          </div>
          <div class="header-right">
            <div class="salary-box">
              <span class="salary-label">薪资</span>
              <span class="salary-value">{{ formatSalary(jobData.salary) }}</span>
            </div>
          </div>
        </div>

        <!-- 快速标签 -->
        <div class="quick-tags">
          <span class="quick-tag education" v-if="jobData.education">
            <BookOutlined /> {{ jobData.education }}
          </span>
          <span class="quick-tag experience" v-if="jobData.experience">
            <ClockCircleOutlined /> {{ jobData.experience }}
          </span>
          <span class="quick-tag industry" v-if="jobData.industry">
            <AppstoreOutlined /> {{ jobData.industry }}
          </span>
        </div>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div class="detail-body">
        <a-row :gutter="24">
          <!-- 左侧主要内容 -->
          <a-col :span="16">
            <!-- 技能匹配分析卡片 -->
            <div class="content-card skill-match-card">
              <div class="card-header">
                <AimOutlined class="card-icon" />
                <span class="card-title">技能匹配分析</span>
              </div>
              <div class="skill-match-content">
                <div class="match-overview">
                  <div class="match-circle-wrapper">
                    <a-progress type="circle" :percent="matchPercent" :stroke-color="getMatchGradient(matchPercent)"
                      :width="100" :stroke-width="10">
                      <template #format="percent">
                        <div class="match-circle-inner">
                          <span class="match-num">{{ percent }}</span>
                          <span class="match-unit">%</span>
                        </div>
                      </template>
                    </a-progress>
                    <div class="match-label">综合匹配度</div>
                  </div>
                  <div class="match-stats">
                    <div class="stat-item">
                      <span class="stat-value matched">{{ matchedSkillCount }}</span>
                      <span class="stat-label">已匹配技能</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-value unmatched">{{ unmatchedSkillCount }}</span>
                      <span class="stat-label">待提升技能</span>
                    </div>
                  </div>
                </div>

                <!-- 技能标签展示 -->
                <div class="skill-tags-section">
                  <div class="skill-group" v-if="matchedSkills.length">
                    <div class="group-label">
                      <CheckCircleOutlined /> 已掌握技能
                    </div>
                    <div class="skill-tags">
                      <span v-for="skill in matchedSkills" :key="skill" class="skill-tag matched">
                        {{ skill }}
                      </span>
                    </div>
                  </div>
                  <div class="skill-group" v-if="unmatchedSkills.length">
                    <div class="group-label">
                      <ReadOutlined /> 待提升技能
                    </div>
                    <div class="skill-tags">
                      <span v-for="skill in unmatchedSkills" :key="skill" class="skill-tag unmatched">
                        {{ skill }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 职位描述卡片 -->
            <div class="content-card">
              <div class="card-header">
                <FileTextOutlined class="card-icon" />
                <span class="card-title">职位描述</span>
              </div>
              <div class="description-content" v-html="formatDescription(jobData.description)"></div>
              <a-empty v-if="!jobData.description" description="暂无职位描述" />
            </div>

            <!-- 福利待遇卡片 -->
            <div class="content-card" v-if="jobData.benefits">
              <div class="card-header">
                <GiftOutlined class="card-icon" />
                <span class="card-title">福利待遇</span>
              </div>
              <div class="benefits-content">{{ jobData.benefits }}</div>
            </div>

            <!-- 职位知识图谱 -->
            <div class="content-card">
              <div class="card-header">
                <DeploymentUnitOutlined class="card-icon" />
                <span class="card-title">职位知识图谱</span>
                <span class="card-badge">可交互</span>
              </div>
              <div id="graph-container" ref="graphContainer" class="graph-area"></div>
              <div class="graph-legend">
                <span class="legend-item"><span class="dot job"></span>本职位</span>
                <span class="legend-item"><span class="dot matched"></span>已匹配技能</span>
                <span class="legend-item"><span class="dot unmatched"></span>未掌握技能</span>
                <span class="legend-item"><span class="dot company"></span>公司</span>
                <span class="legend-item"><span class="dot city"></span>城市</span>
                <span class="legend-item"><span class="dot industry"></span>行业</span>
              </div>
            </div>
          </a-col>

          <!-- 右侧操作栏 -->
          <a-col :span="8">
            <!-- 快速操作卡片 -->
            <div class="action-card">
              <a-button type="primary" block size="large" class="action-btn primary" @click="applyJob">
                <SendOutlined /> 投递简历
              </a-button>
              <a-button block size="large" class="action-btn secondary" @click="planCourse">
                <ReadOutlined /> 制定学习计划
              </a-button>
              <a-button block class="action-btn ghost" @click="saveJob">
                <StarOutlined /> 收藏职位
              </a-button>
            </div>

            <!-- 职位信息卡片 -->
            <div class="info-card">
              <div class="info-header">
                <ProfileOutlined /> 职位信息
              </div>
              <div class="info-list">
                <div class="info-item">
                  <span class="info-label">学历要求</span>
                  <span class="info-value">
                    <a-tag :color="getEducationColor(jobData.education)">
                      {{ jobData.education || '不限' }}
                    </a-tag>
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">工作经验</span>
                  <span class="info-value">{{ jobData.experience || '不限' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">所属行业</span>
                  <span class="info-value">{{ jobData.industry || '不限' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">工作地点</span>
                  <span class="info-value">{{ jobData.city || '不限' }}</span>
                </div>
              </div>
            </div>

            <!-- 推荐学习卡片 -->
            <div class="learn-card" v-if="relatedCourses.length">
              <div class="learn-header">
                <ReadOutlined class="learn-icon" />
                <span class="learn-title">推荐学习</span>
              </div>
              <div class="course-list">
                <div v-for="course in relatedCourses" :key="course.name" class="course-item">
                  <div class="course-name">{{ course.name }}</div>
                  <div class="course-skills">覆盖: {{ course.skills?.join(', ') }}</div>
                  <div class="course-reason" v-if="course.reason">
                    <PushpinOutlined /> {{ course.reason }}
                  </div>
                </div>
              </div>
            </div>
            <div class="learn-card congrats" v-else>
              <TrophyOutlined class="congrats-icon" />
              <div class="congrats-text">您已掌握该职位所需的核心技能！</div>
            </div>
          </a-col>
        </a-row>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { BankOutlined, EnvironmentOutlined, BookOutlined, ClockCircleOutlined, AppstoreOutlined, AimOutlined, FileTextOutlined, GiftOutlined, DeploymentUnitOutlined, SendOutlined, StarOutlined, ProfileOutlined, ReadOutlined, PushpinOutlined, TrophyOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { studentApi } from '@/api'
import G6 from '@antv/g6'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const jobData = ref({})
const matchPercent = ref(20)

// 技能到推荐课程的映射
const skillToCourse = {
  'python': { name: 'Python高级编程', skills: ['Python', '算法'] },
  'java': { name: 'Java核心技术', skills: ['Java', 'JVM', '多线程'] },
  'javascript': { name: 'JavaScript全栈开发', skills: ['JavaScript', 'ES6', 'Node.js'] },
  'vue': { name: 'Vue3实战开发', skills: ['Vue', '前端工程化'] },
  'react': { name: 'React高级进阶', skills: ['React', 'Redux', 'Hooks'] },
  'spring': { name: 'Spring Boot实战', skills: ['Spring', 'Spring Boot', 'Spring Cloud'] },
  'mysql': { name: 'MySQL数据库原理', skills: ['MySQL', 'SQL优化'] },
  'redis': { name: 'Redis缓存架构', skills: ['Redis', '缓存设计'] },
  'docker': { name: 'Docker容器技术', skills: ['Docker', 'K8s'] },
  'linux': { name: 'Linux系统管理', skills: ['Linux', 'Shell'] },
  'git': { name: 'Git版本控制', skills: ['Git', 'GitFlow'] },
  '机器学习': { name: '机器学习入门', skills: ['机器学习', 'Python'] },
  '深度学习': { name: '深度学习实战', skills: ['深度学习', 'TensorFlow', 'PyTorch'] },
  '算法': { name: '数据结构与算法', skills: ['数据结构', '算法'] },
}

// 用户技能
const userSkills = computed(() => {
  const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
  return (userProfile.skills || []).map(s => s.toLowerCase())
})

// 匹配的技能
const matchedSkills = computed(() => {
  const required = jobData.value.required_skills || []
  return required.filter(skill =>
    userSkills.value.some(us =>
      skill.toLowerCase().includes(us) || us.includes(skill.toLowerCase())
    )
  )
})

// 未匹配的技能
const unmatchedSkills = computed(() => {
  const required = jobData.value.required_skills || []
  return required.filter(skill => !matchedSkills.value.includes(skill))
})

const matchedSkillCount = computed(() => matchedSkills.value.length)
const unmatchedSkillCount = computed(() => unmatchedSkills.value.length)

// 动态生成推荐课程
const relatedCourses = computed(() => {
  const courses = []
  const addedCourses = new Set()

  for (const skill of unmatchedSkills.value) {
    const skillLower = skill.toLowerCase()
    for (const [key, course] of Object.entries(skillToCourse)) {
      if (skillLower.includes(key) || key.includes(skillLower)) {
        if (!addedCourses.has(course.name)) {
          courses.push({ ...course, reason: `补充技能: ${skill}` })
          addedCourses.add(course.name)
        }
        break
      }
    }
  }
  return courses.slice(0, 4)
})

const decodedJobId = computed(() => {
  try {
    return decodeURIComponent(route.params.id)
  } catch {
    return route.params.id
  }
})

// 工具函数
const formatSalary = (salary) => {
  if (!salary || salary === 'nan' || salary === 'NaN' || salary === '面议') return '面议'
  return salary
}

const formatDescription = (text) => {
  if (!text) return ''
  return text
    .replace(/(\d+\.)/g, '<br/><br/>$1')
    .replace(/([；。])/g, '$1<br/>')
    .replace(/(<br\/>)+/g, '<br/>')
}

const getMatchGradient = (percent) => {
  if (percent >= 70) return { '0%': '#52c41a', '100%': '#13c2c2' }
  if (percent >= 50) return { '0%': '#1890ff', '100%': '#722ed1' }
  if (percent >= 30) return { '0%': '#faad14', '100%': '#fa8c16' }
  return { '0%': '#ff4d4f', '100%': '#f5222d' }
}

const getEducationColor = (edu) => {
  if (edu === '博士') return 'red'
  if (edu === '硕士') return 'orange'
  if (edu === '本科') return 'blue'
  return 'default'
}

// 获取职位详情
const fetchJobDetail = async () => {
  loading.value = true
  try {
    const { data } = await studentApi.getJobDetail(decodedJobId.value)

    // 处理城市显示
    let displayCity = ''
    const cities = data.cities || []
    const queryCity = route.query.city

    if (queryCity && cities.includes(queryCity)) {
      displayCity = queryCity
    } else if (cities.length > 0) {
      const textToSearch = (data.title + (data.description || '')).substring(0, 200)
      const inferredCity = cities.find(city => textToSearch.includes(city))
      displayCity = inferredCity || cities[0]
      if (!inferredCity && cities.length > 1) {
        displayCity += ` 等${cities.length}个地点`
      }
    } else {
      displayCity = '地点不限'
    }

    jobData.value = { ...data, city: displayCity, raw_cities: data.cities }

    // 计算匹配度
    const routeMatchRate = route.query.matchRate
    if (routeMatchRate !== undefined && routeMatchRate !== null) {
      matchPercent.value = Math.round(parseFloat(routeMatchRate) * 100)
    } else {
      const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
      if (userProfile.skills && data.required_skills) {
        const userSkillSet = new Set(userProfile.skills)
        const matched = data.required_skills.filter(s => userSkillSet.has(s))
        matchPercent.value = Math.round((matched.length / Math.max(data.required_skills.length, 1)) * 100)
      }
    }

    // 获取知识图谱
    try {
      const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
      const userSkillsList = userProfile.skills || []
      const { data: graphData } = await studentApi.getJobGraph(decodedJobId.value, userSkillsList, displayCity)
      if (graphData?.nodes?.length > 0) {
        initGraph(graphData)
      }
    } catch (graphErr) {
      console.error("加载图谱失败", graphErr)
    }
  } catch (error) {
    console.error('获取职位详情失败', error)
    jobData.value = {
      title: route.query.title || '未知职位',
      salary: route.query.salary,
      company: route.query.company || '未知公司',
      city: route.query.city || '未知地点',
      required_skills: []
    }
  } finally {
    loading.value = false
  }
}

// 图谱实例
let graph = null
const graphContainer = ref(null)

const initGraph = (data) => {
  if (graph) graph.destroy()
  if (!graphContainer.value) return

  const width = graphContainer.value.scrollWidth || 600
  const height = graphContainer.value.scrollHeight || 400

  const nodeColors = {
    'Job': { fill: '#1890ff', stroke: '#096dd9' },
    'SkillMatched': { fill: '#52c41a', stroke: '#237804' },
    'SkillUnmatched': { fill: '#d9d9d9', stroke: '#8c8c8c' },
    'Course': { fill: '#faad14', stroke: '#d48806' },
    'City': { fill: '#722ed1', stroke: '#531dab' },
    'Industry': { fill: '#13c2c2', stroke: '#08979c' },
    'Company': { fill: '#fa541c', stroke: '#d4380d' }
  }

  const processedNodes = data.nodes.map(node => {
    const nodeType = node.label
    let colorKey = nodeType
    if (nodeType === 'Skill') {
      colorKey = node.matched ? 'SkillMatched' : 'SkillUnmatched'
    }
    const colors = nodeColors[colorKey] || nodeColors['SkillUnmatched']
    const displayName = node.name?.length > 15 ? node.name.substring(0, 15) + '...' : node.name || node.id

    return {
      ...node,
      label: displayName,
      nodeType: nodeType,
      size: nodeType === 'Job' ? 60 : 40,
      style: { fill: colors.fill, stroke: colors.stroke, lineWidth: 2 },
      labelCfg: {
        style: { fill: '#333', fontSize: nodeType === 'Job' ? 14 : 12, fontWeight: nodeType === 'Job' ? 'bold' : 'normal' },
        position: 'bottom'
      }
    }
  })

  const edgeTypeLabels = { 'REQUIRES': '需要', 'LOCATED_IN': '位于', 'BELONGS_TO': '所属', 'TEACHES': '教授', 'OFFERED_BY': '提供者' }

  const processedEdges = data.edges.map(edge => ({
    ...edge,
    label: edgeTypeLabels[edge.type] || edge.type,
    style: { stroke: '#aaa', lineWidth: 1.5, endArrow: { path: G6.Arrow.triangle(6, 8, 0), fill: '#aaa' } }
  }))

  graph = new G6.Graph({
    container: graphContainer.value,
    width,
    height,
    modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'activate-relations'] },
    layout: { type: 'force', preventOverlap: true, nodeSpacing: 50, linkDistance: 180, nodeStrength: -120, edgeStrength: 0.2 },
    defaultEdge: { type: 'quadratic', labelCfg: { autoRotate: true, style: { fill: '#666', fontSize: 10 } } }
  })

  graph.data({ nodes: processedNodes, edges: processedEdges })
  graph.render()
}

onUnmounted(() => { if (graph) graph.destroy() })

const applyJob = () => message.success('已记录您的投递意向！HR将尽快与您联系')
const planCourse = () => message.info('正在为您生成个性化学习计划...')
const saveJob = () => message.success('职位已收藏')

onMounted(() => {
  window.scrollTo(0, 0)
  fetchJobDetail()
})
</script>

<style scoped>
.job-detail {
  max-width: 1400px;
  margin: 0 auto;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 沉浸式头部 */
.detail-header {
  position: relative;
  padding: 24px 32px 32px;
  margin-bottom: 24px;
}

.header-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 0 0 24px 24px;
}

.header-content {
  position: relative;
  z-index: 1;
}

.back-btn {
  color: white !important;
  margin-bottom: 16px;
  padding: 0;
  font-size: 14px;
}

.back-btn:hover {
  opacity: 0.8;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.header-left {
  flex: 1;
}

.job-title {
  color: white;
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 12px 0;
}

.company-info {
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.divider {
  opacity: 0.5;
}

.salary-box {
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 12px 20px;
  text-align: center;
}

.salary-label {
  display: block;
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  margin-bottom: 4px;
}

.salary-value {
  color: white;
  font-size: 22px;
  font-weight: 700;
}

.quick-tags {
  display: flex;
  gap: 10px;
}

.quick-tag {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
}

/* 主体内容 */
.detail-body {
  padding: 0 24px 32px;
}

/* 内容卡片 */
.content-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.card-icon {
  font-size: 20px;
}

.card-title {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a1a;
}

.card-badge {
  margin-left: auto;
  background: #e6f7ff;
  color: #1890ff;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

/* 技能匹配卡片 */
.skill-match-card {
  border: 2px solid #f0f0f0;
}

.match-overview {
  display: flex;
  align-items: center;
  gap: 40px;
  margin-bottom: 24px;
}

.match-circle-wrapper {
  text-align: center;
}

.match-circle-inner {
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.match-num {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
}

.match-unit {
  font-size: 14px;
  color: #666;
}

.match-label {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

.match-stats {
  display: flex;
  gap: 32px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
}

.stat-value.matched {
  color: #52c41a;
}

.stat-value.unmatched {
  color: #faad14;
}

.stat-label {
  font-size: 13px;
  color: #666;
}

/* 技能标签区域 */
.skill-tags-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skill-group {
  padding: 16px;
  background: #fafafa;
  border-radius: 10px;
}

.group-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 10px;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-tag {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
}

.skill-tag.matched {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
  color: white;
}

.skill-tag.unmatched {
  background: #f0f0f0;
  color: #666;
}

/* 职位描述 */
.description-content {
  line-height: 1.8;
  color: #333;
  font-size: 14px;
}

.benefits-content {
  line-height: 1.8;
  color: #666;
}

/* 知识图谱 */
.graph-area {
  width: 100%;
  height: 400px;
  background: #fafafa;
  border-radius: 10px;
}

.graph-legend {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.job {
  background: #1890ff;
}

.dot.matched {
  background: #52c41a;
}

.dot.unmatched {
  background: #d9d9d9;
}

.dot.company {
  background: #fa541c;
}

.dot.city {
  background: #722ed1;
}

.dot.industry {
  background: #13c2c2;
}

/* 右侧操作卡片 */
.action-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn.primary {
  background: linear-gradient(135deg, #1890ff 0%, #722ed1 100%);
  border: none;
  height: 48px;
  font-size: 16px;
}

.action-btn.secondary {
  background: #f5f5f5;
  border: none;
  color: #333;
  height: 44px;
}

.action-btn.ghost {
  border: 1px solid #d9d9d9;
  color: #666;
}

/* 职位信息卡片 */
.info-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.info-header {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1a1a1a;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  color: #999;
  font-size: 13px;
}

.info-value {
  color: #333;
  font-size: 13px;
}

/* 推荐学习卡片 */
.learn-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.learn-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.learn-icon {
  font-size: 18px;
}

.learn-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.course-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.course-skills {
  font-size: 12px;
  color: #666;
}

.course-reason {
  font-size: 12px;
  color: #fa8c16;
  margin-top: 4px;
}

/* 恭喜卡片 */
.learn-card.congrats {
  text-align: center;
  background: linear-gradient(135deg, #f6ffed 0%, #e6f7ff 100%);
}

.congrats-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.congrats-text {
  color: #52c41a;
  font-weight: 500;
}
</style>
