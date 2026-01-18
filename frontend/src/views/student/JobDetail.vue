<template>
  <div class="job-detail">
    <!-- 页面头部 -->
    <a-page-header 
      @back="() => $router.back()"
      :style="{ background: 'white', borderRadius: '8px', marginBottom: '24px' }"
    >
      <template #title>
        <span class="job-header-title">{{ jobData.title || '职位详情' }}</span>
      </template>
      <template #subTitle>
        <a-space>
          <span>{{ jobData.company }}</span>
          <a-divider type="vertical" v-if="jobData.city" />
          <span v-if="jobData.city">📍 {{ jobData.city }}</span>
        </a-space>
      </template>
      <template #extra>
        <a-tag color="green" size="large" style="font-size: 16px; padding: 6px 12px">
          💰 {{ formatSalary(jobData.salary) }}
        </a-tag>
      </template>
    </a-page-header>
    
    <a-spin :spinning="loading">
      <a-row :gutter="24">
        <!-- 左侧主要内容 -->
        <a-col :span="16">
          <!-- 基本信息卡片 -->
          <a-card title="📋 职位信息" class="info-card" style="margin-bottom: 24px">
            <a-descriptions :column="2" bordered>
              <a-descriptions-item label="职位名称">
                {{ jobData.title }}
              </a-descriptions-item>
              <a-descriptions-item label="所属公司">
                {{ jobData.company }}
              </a-descriptions-item>
              <a-descriptions-item label="工作地点">
                {{ jobData.city || '不限' }}
              </a-descriptions-item>
              <a-descriptions-item label="所属行业">
                {{ jobData.industry || '不限' }}
              </a-descriptions-item>
              <a-descriptions-item label="学历要求">
                <a-tag :color="getEducationColor(jobData.education)">
                  {{ jobData.education || '不限' }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="工作经验">
                {{ jobData.experience || '不限' }}
              </a-descriptions-item>
              <a-descriptions-item label="薪资范围" :span="2">
                <span class="salary-text">{{ formatSalary(jobData.salary) }}</span>
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
          
          <!-- 技能要求 -->
          <a-card title="🎯 技能要求" class="info-card" style="margin-bottom: 24px">
            <div class="skill-tags-large">
              <a-tag 
                v-for="skill in jobData.required_skills" 
                :key="skill"
                color="blue"
                style="font-size: 14px; padding: 4px 12px; margin: 6px"
              >
                {{ skill }}
              </a-tag>
              <a-empty v-if="!jobData.required_skills?.length" description="暂无技能要求" />
            </div>
          </a-card>
          
          <!-- 职位描述 -->
          <a-card title="📝 职位描述" class="info-card" style="margin-bottom: 24px">
            <div class="job-description" v-html="formatDescription(jobData.description)"></div>
          </a-card>
          
          <!-- 福利待遇 -->
          <a-card title="🎁 福利待遇" class="info-card" style="margin-bottom: 24px" v-if="jobData.benefits">
            <div class="benefits">
              {{ jobData.benefits }}
            </div>
          </a-card>
          
          <!-- 职位知识图谱 (最底部) -->
          <a-card title="🕸️ 职位知识图谱 (可交互)" class="info-card" style="margin-bottom: 24px">
            <div id="graph-container" ref="graphContainer" style="width: 100%; height: 500px; background: #fafafa; border-radius: 8px;"></div>
            <!-- 完整图例 -->
            <div class="graph-legend" style="margin-top: 16px; display: flex; justify-content: center; gap: 12px; font-size: 12px; color: #555; flex-wrap: wrap;">
              <span><span style="display:inline-block;width:12px;height:12px;background:#1890ff;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>本职位</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#52c41a;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>已匹配技能</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#d9d9d9;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>未掌握技能</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#faad14;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>公司</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#722ed1;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>城市</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#13c2c2;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>行业</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#fa541c;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>薪资</span>
              <span><span style="display:inline-block;width:12px;height:12px;background:#eb2f96;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>学历</span>
            </div>
          </a-card>
        </a-col>
        
        <!-- 右侧操作 -->
        <a-col :span="8">
          <!-- 快速操作 -->
          <a-card title="⚡ 快速操作" style="margin-bottom: 24px">
            <a-space direction="vertical" style="width: 100%">
              <a-button type="primary" block size="large" @click="applyJob">
                📤 投递简历
              </a-button>
              <a-button block size="large" @click="planCourse">
                📚 制定学习计划
              </a-button>
              <a-button block @click="saveJob">
                ⭐ 收藏职位
              </a-button>
            </a-space>
          </a-card>
          
          <!-- 匹配分析 -->
          <a-card title="📊 匹配分析" style="margin-bottom: 24px">
            <div class="match-analysis">
              <a-progress 
                :percent="matchPercent" 
                :stroke-color="getScoreColor(matchPercent / 100)"
                :format="() => `${matchPercent}%`"
                :size="120"
                type="circle"
              />
              <p style="text-align: center; margin-top: 16px; color: #666">
                综合匹配度
              </p>
              <a-divider />
              <p style="font-size: 13px; color: #999">
                基于您的技能与该职位要求的匹配程度计算
              </p>
            </div>
          </a-card>
          
          <!-- 相关课程推荐 -->
          <a-card title="📖 推荐学习">
            <a-list 
              :data-source="relatedCourses"
              size="small"
            >
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>{{ item.name }}</template>
                    <template #description>
                      <div>覆盖技能: {{ item.skills?.join(', ') }}</div>
                      <div v-if="item.reason" style="color: #fa8c16; font-size: 12px;">📌 {{ item.reason }}</div>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
              <template #empty>
                <div style="text-align: center; color: #999; padding: 16px;">
                  🎉 您已掌握该职位所需的核心技能！
                </div>
              </template>
            </a-list>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
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
  '计算机网络': { name: '计算机网络原理', skills: ['TCP/IP', 'HTTP'] },
  '前端开发': { name: '前端工程化实践', skills: ['Webpack', 'Vite', '前端优化'] },
  '后端开发': { name: '后端架构设计', skills: ['微服务', 'API设计'] },
  'mybatis': { name: 'MyBatis持久层框架', skills: ['MyBatis', 'ORM'] },
  'postgresql': { name: 'PostgreSQL数据库', skills: ['PostgreSQL', 'SQL'] },
  'mongodb': { name: 'MongoDB实战', skills: ['MongoDB', 'NoSQL'] },
}

// 动态生成推荐课程（根据用户缺失的技能）
const relatedCourses = computed(() => {
  const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
  const userSkillsRaw = userProfile.skills || []
  const userSkillsLower = userSkillsRaw.map(s => s.toLowerCase())
  const requiredSkills = jobData.value.required_skills || []
  
  // 模糊匹配函数
  const isSkillMatched = (requiredSkill) => {
    const reqLower = requiredSkill.toLowerCase()
    return userSkillsLower.some(userSkill => 
      reqLower === userSkill || 
      reqLower.includes(userSkill) || 
      userSkill.includes(reqLower)
    )
  }
  
  // 找出用户缺失的技能（使用模糊匹配）
  const missingSkills = requiredSkills.filter(skill => !isSkillMatched(skill))
  
  // 根据缺失技能推荐课程
  const courses = []
  const addedCourses = new Set()
  
  for (const skill of missingSkills) {
    const skillLower = skill.toLowerCase()
    // 查找匹配的课程
    for (const [key, course] of Object.entries(skillToCourse)) {
      if (skillLower.includes(key) || key.includes(skillLower)) {
        if (!addedCourses.has(course.name)) {
          courses.push({
            ...course,
            reason: `补充技能: ${skill}`
          })
          addedCourses.add(course.name)
        }
        break
      }
    }
  }
  
  // 如果没有匹配到，提供通用推荐
  if (courses.length === 0 && requiredSkills.length > 0) {
    courses.push(
      { name: '职业技能提升', skills: requiredSkills.slice(0, 3), reason: '该职位核心技能' }
    )
  }
  
  return courses.slice(0, 5)  // 最多显示5个
})

const decodedJobId = computed(() => {
  try {
    return decodeURIComponent(route.params.id)
  } catch {
    return route.params.id
  }
})

const formatSalary = (salary) => {
  if (!salary || salary === 'nan' || salary === 'NaN' || salary === '面议') return '面议'
  return salary
}

const formatDescription = (text) => {
  if (!text) return '暂无职位描述'
  return text
    // 将 "1.", "2." 等序号前添加换行 (如果是行首则不添加)
    .replace(/(\d+\.)/g, '<br/><br/>$1')
    // 替换中文顿号或分号分割的长句 (可选)
    .replace(/([；。])/g, '$1<br/>')
    // 保护 consecutive breaks
    .replace(/(<br\/>)+/g, '<br/>')
}

const getScoreColor = (score) => {
  if (score >= 0.8) return '#52c41a'
  if (score >= 0.6) return '#1890ff'
  if (score >= 0.4) return '#faad14'
  return '#ff4d4f'
}

const getEducationColor = (edu) => {
  if (edu === '博士') return 'red'
  if (edu === '硕士') return 'orange'
  if (edu === '本科') return 'blue'
  return 'default'
}

const fetchJobDetail = async () => {
  loading.value = true
  try {
    const { data } = await studentApi.getJobDetail(decodedJobId.value)
    
    // 处理城市显示逻辑
    // 处理城市显示逻辑
    let displayCity = ''
    const cities = data.cities || []
    const queryCity = route.query.city
    
    // 1. 优先使用查询参数中的城市（用户明确意图）
    if (queryCity && cities.includes(queryCity)) {
       displayCity = queryCity
    } 
    // 2. 尝试从标题或描述中推断（智能匹配）
    else if (cities.length > 0) {
      // 简单的文本匹配
      const textToSearch = (data.title + (data.description || '')).substring(0, 200) // 只搜前200字
      const inferredCity = cities.find(city => textToSearch.includes(city))
      
      if (inferredCity) {
        displayCity = inferredCity
      } else {
        // 3. 实在无法确定，显示第一个并提示多地
        displayCity = cities[0]
        if (cities.length > 1) {
           displayCity += ` 等${cities.length}个地点`
        }
      }
    } else {
      displayCity = '地点不限'
    }
    
    jobData.value = {
      ...data,
      city: displayCity, // 覆盖单一城市字段用于显示
      raw_cities: data.cities // 保留原始列表
    }
    
    const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
    
    // 计算匹配度：优先使用路由传递的分数（来自推荐结果）
    const routeMatchRate = route.query.matchRate
    if (routeMatchRate !== undefined && routeMatchRate !== null) {
      // 使用推荐系统计算的匹配度（已经是0-1范围的小数）
      matchPercent.value = Math.round(parseFloat(routeMatchRate) * 100)
    } else {
      // 备选：本地计算（基于 localStorage 中的用户技能）
      if (userProfile.skills && data.required_skills) {
        const userSkills = new Set(userProfile.skills)
        const matched = data.required_skills.filter(s => userSkills.has(s))
        matchPercent.value = Math.round((matched.length / Math.max(data.required_skills.length, 1)) * 100)
      }
    }

    // ================== 获取知识图谱数据 ==================
    try {
       const userSkillsList = userProfile.skills || []
       // 传递职位的城市给知识图谱（使用推荐列表中显示的城市）
       const displayCity = jobData.value.city || route.query.city || null
       const { data: graphData } = await studentApi.getJobGraph(decodedJobId.value, userSkillsList, displayCity)
       if (graphData && graphData.nodes && graphData.nodes.length > 0) {
           initGraph(graphData)
       }
    } catch (graphErr) {
       console.error("加载图谱失败", graphErr)
    }
  } catch (error) {
    console.error('获取职位详情失败', error)
    // 使用query中的备选数据
    jobData.value = {
      title: route.query.title || '未知职位',
      salary: route.query.salary,
      company: route.query.company || '未知公司',
      city: route.query.city || '未知地点',
      required_skills: []  // 不再硬编码，显示为空
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
  const height = graphContainer.value.scrollHeight || 500

  // 节点颜色映射
  const nodeColors = {
    'Job': { fill: '#1890ff', stroke: '#096dd9' },
    'Skill': { fill: '#52c41a', stroke: '#389e0d' },  // 默认技能颜色
    'SkillMatched': { fill: '#52c41a', stroke: '#237804' },  // 已匹配技能
    'SkillUnmatched': { fill: '#d9d9d9', stroke: '#8c8c8c' },  // 未匹配技能
    'Course': { fill: '#faad14', stroke: '#d48806' },
    'City': { fill: '#722ed1', stroke: '#531dab' },
    'Industry': { fill: '#13c2c2', stroke: '#08979c' },
    'Company': { fill: '#fa541c', stroke: '#d4380d' }
  }

  // 预处理节点数据，添加样式
  const processedNodes = data.nodes.map(node => {
    const nodeType = node.label  // 保存原始节点类型（Job, Skill, City等）
    let colorKey = nodeType
    
    // 技能节点根据是否匹配设置不同颜色
    if (nodeType === 'Skill') {
      colorKey = node.matched ? 'SkillMatched' : 'SkillUnmatched'
    }
    const colors = nodeColors[colorKey] || nodeColors['Skill']
    
    // 截断过长的名称
    const displayName = node.name && node.name.length > 15 
      ? node.name.substring(0, 15) + '...' 
      : node.name || node.id
    
    return {
      ...node,
      label: displayName,  // G6 使用 label 作为显示文本
      nodeType: nodeType,  // 保留原始节点类型
      size: nodeType === 'Job' ? 60 : 40,
      style: {
        fill: colors.fill,
        stroke: colors.stroke,
        lineWidth: 2
      },
      labelCfg: {
        style: {
          fill: '#333',
          fontSize: nodeType === 'Job' ? 14 : 12,
          fontWeight: nodeType === 'Job' ? 'bold' : 'normal'
        },
        position: 'bottom'
      }
    }
  })

  // 关系类型中文映射
  const edgeTypeLabels = {
    'REQUIRES': '需要',
    'LOCATED_IN': '位于',
    'BELONGS_TO': '所属行业',
    'TEACHES': '教授',
    'OFFERED_BY': '提供者'
  }

  // 预处理边数据
  const processedEdges = data.edges.map(edge => ({
    ...edge,
    label: edgeTypeLabels[edge.type] || edge.type,
    style: {
      stroke: '#aaa',
      lineWidth: 1.5,
      endArrow: {
        path: G6.Arrow.triangle(6, 8, 0),
        fill: '#aaa'
      }
    }
  }))

  graph = new G6.Graph({
    container: graphContainer.value,
    width,
    height,
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'activate-relations'],
    },
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeSpacing: 50,
      linkDistance: 180,
      nodeStrength: -120,
      edgeStrength: 0.2,
      collideStrength: 0.8
    },
    defaultEdge: {
      type: 'quadratic',
      labelCfg: {
        autoRotate: true,
        style: {
           fill: '#666',
           fontSize: 10
        }
      }
    }
  })

  graph.data({ nodes: processedNodes, edges: processedEdges })
  graph.render()
  
  // 窗口大小调整
  if (typeof window !== 'undefined') {
    window.onresize = () => {
      if (!graph || graph.get('destroyed')) return
      if (!graphContainer.value) return
      graph.changeSize(graphContainer.value.scrollWidth, graphContainer.value.scrollHeight)
    }
  }
}

onUnmounted(() => {
  if (graph) {
    graph.destroy()
  }
})

const applyJob = () => {
  message.success('已记录您的投递意向！HR将尽快与您联系')
}

const planCourse = () => {
  message.info('正在为您生成个性化学习计划...')
}

const saveJob = () => {
  message.success('职位已收藏')
}

onMounted(() => {
  // 重置滚动位置到顶部
  window.scrollTo(0, 0)
  fetchJobDetail()
})
</script>

<style scoped>
.job-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.job-header-title {
  font-size: 22px;
  font-weight: 600;
}

.info-card {
  border-radius: 12px;
}

.salary-text {
  font-size: 18px;
  font-weight: 600;
  color: #52c41a;
}

.skill-tags-large {
  padding: 8px 0;
}

.job-description {
  line-height: 1.8;
  white-space: pre-wrap;
  color: #333;
}

.benefits {
  line-height: 1.8;
  color: #666;
}

.match-analysis {
  text-align: center;
  padding: 16px;
}
</style>
