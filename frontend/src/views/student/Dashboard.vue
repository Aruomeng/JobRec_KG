<template>
  <div class="student-dashboard">
    <!-- 欢迎横幅 -->
    <a-page-header
      title="🎓 智途 AI"
      sub-title="大学生职业规划与智能推荐系统"
      :style="{ background: 'white', borderRadius: '8px', marginBottom: '24px' }"
    >
      <template #extra>
        <div v-if="isLoggedIn" style="display: flex; align-items: center; gap: 12px">
           <a-tag color="blue">
             🆔 {{ userProfile.student_id }}
           </a-tag>
           <span style="font-weight: 500">{{ userProfile.name }}</span>
           <a-button type="link" size="small" @click="showProfileModal = true">编辑资料</a-button>
           <a-button type="link" size="small" @click="logout" danger>退出</a-button>
        </div>
        <div v-else style="display: flex; align-items: center; gap: 12px">
           <a-button @click="showProfileModal = true">
             ✏️ 完善资料
           </a-button>
           <a-button type="primary" @click="showLoginModal = true">
             🚀 登录
           </a-button>
        </div>
      </template>
    </a-page-header>

    
    <!-- 职业偏好筛选 -->
    <a-card class="filter-card" :bordered="false">
      <a-row :gutter="16" align="middle">
        <a-col :span="5">
          <a-select 
            v-model:value="filters.city" 
            placeholder="期望城市" 
            style="width: 100%" 
            size="large"
            allowClear
            :options="availableCities"
          />
        </a-col>
        <a-col :span="5">
          <a-select 
            v-model:value="filters.salary" 
            placeholder="期望薪资" 
            style="width: 100%" 
            size="large"
            allowClear
          >
            <a-select-option value="5000-10000">5K-10K</a-select-option>
            <a-select-option value="10000-20000">10K-20K</a-select-option>
            <a-select-option value="20000-30000">20K-30K</a-select-option>
            <a-select-option value="30000+">30K以上</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="5">
          <a-button type="primary" size="large" block @click="fetchPersonalizedJobs">
            🔍 获取个性化推荐
          </a-button>
        </a-col>
        <a-col :span="4">
          <a-select 
            v-model:value="recommendMode" 
            size="large"
            style="width: 100%"
          >
            <a-select-option value="kg">📊 知识图谱</a-select-option>
            <a-select-option value="ai">🤖 AI推荐</a-select-option>
            <a-select-option value="hybrid">🔮 三层漏斗</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="4">
          <a-button size="large" @click="showSkillDiagnosis" block>
            🔬 技能诊断
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
      <a-tab-pane key="hot" tab="🔥 热门推荐" />
      <a-tab-pane key="personalized" tab="🎯 为你推荐" :disabled="!userProfile.skills?.length" />
    </a-tabs>
    
    <!-- 推荐结果 -->
    <a-spin :spinning="loading">
      <div class="job-grid">
        <div 
          v-for="(job, index) in paginatedJobs" 
          :key="job.job_id"
          class="job-card-modern"
          :style="{ animationDelay: `${index * 0.05}s` }"
          @click="goToDetail(job)"
        >
          <!-- 卡片头部：职位名称和匹配度 -->
          <div class="job-card-header">
            <div class="job-header-content">
              <h3 class="job-title-modern">{{ formatTitle(job.title) }}</h3>
              <div class="job-company-modern">
                <span class="company-icon">🏢</span>
                {{ job.company || '未知公司' }}
              </div>
            </div>
            <!-- 匹配度环形图 -->
            <div class="match-ring" v-if="job.match_score">
              <a-progress 
                type="circle" 
                :percent="Math.round((job.match_rate || 0) * 100)" 
                :width="56"
                :stroke-width="8"
                :stroke-color="getScoreGradient(job.match_score)"
              >
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
              <span class="tag-icon">📍</span>{{ job.city }}
            </span>
            <span class="meta-tag education" v-if="job.education">
              <span class="tag-icon">🎓</span>{{ job.education }}
            </span>
            <span class="meta-tag industry" v-if="job.industry">
              <span class="tag-icon">🏭</span>{{ job.industry }}
            </span>
          </div>
          
          <!-- 技能标签区域 -->
          <div class="skill-section" v-if="job.required_skills?.length">
            <div class="skill-label">技能要求</div>
            <div class="skill-tags-modern">
              <a-tag 
                v-for="skill in job.required_skills.slice(0, 4)" 
                :key="skill" 
                :class="['skill-tag', job.matched_skills?.includes(skill) ? 'matched' : 'unmatched']"
              >
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
            <div class="reason-icon">💡</div>
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
        <a-pagination
          v-model:current="currentPage"
          v-model:pageSize="pageSize"
          :total="displayJobs.length"
          :pageSizeOptions="['12', '24', '48', '96']"
          show-size-changer
          show-quick-jumper
          :show-total="total => `共 ${total} 个职位`"
          @change="window.scrollTo({ top: 0, behavior: 'smooth' })"
        />
      </div>
    </a-spin>
    
    <!-- 登录弹窗 -->
    <a-modal
      v-model:open="showLoginModal"
      title="🔑 学生登录"
      :footer="null"
      width="400px"
    >
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

    <!-- 个人信息弹窗 -->
    <a-modal 
      v-model:open="showProfileModal" 
      title="✏️ 完善个人信息"
      width="800px"
      @ok="saveProfile"
    >
      <a-form layout="vertical">
        <!-- 第一行：基础信息 -->
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="姓名">
              <a-input v-model:value="profileForm.name" placeholder="请输入您的姓名" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="学历">
              <a-select v-model:value="profileForm.education" placeholder="请选择学历">
                <a-select-option value="专科">专科</a-select-option>
                <a-select-option value="本科">本科</a-select-option>
                <a-select-option value="硕士">硕士</a-select-option>
                <a-select-option value="博士">博士</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="学生ID (系统自动生成)">
               <a-input v-model:value="profileForm.student_id" disabled />
            </a-form-item>
          </a-col>
        </a-row>
        
        <!-- 第二行：专业和期望职位 -->
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="专业">
              <a-input v-model:value="profileForm.major" placeholder="如：计算机科学与技术" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="期望职位">
              <a-input v-model:value="profileForm.expectedJob" placeholder="如：前端工程师" />
            </a-form-item>
          </a-col>
        </a-row>
        
        <!-- 第三行：技能 (全宽) -->
        <a-form-item label="掌握的技能（多选，输入并回车添加）">
          <a-select 
            v-model:value="profileForm.skills" 
            mode="tags" 
            placeholder="输入并回车添加技能"
            :options="commonSkills"
          />
        </a-form-item>
        
        <!-- 第四行：已修课程 (全宽) - 仅登录用户可见 -->
        <a-form-item v-if="isLoggedIn" label="已修课程（用于三层漏斗推荐）">
          <a-select 
            v-model:value="profileForm.courses" 
            mode="multiple" 
            placeholder="选择已修课程，获得更精准的推荐"
            :options="courseOptions"
            :loading="coursesLoading"
            show-search
            :filter-option="filterCourse"
            style="width: 100%"
          >
            <template #option="{ value, label, skills }">
              <div>
                <span>{{ label }}</span>
                <span style="color: #999; font-size: 12px; margin-left: 8px">{{ skills?.join(', ') }}</span>
              </div>
            </template>
          </a-select>
          <div style="margin-top: 8px; color: #666; font-size: 12px">
            已选 {{ profileForm.courses?.length || 0 }} 门课程
          </div>
        </a-form-item>
        <a-alert 
          v-else 
          type="info" 
          show-icon
          message="登录后可选择已修课程，解锁「三层漏斗」推荐模式"
          style="margin-bottom: 16px"
        />
      </a-form>
    </a-modal>

    <!-- 简历上传弹窗 -->
    <a-modal
      v-model:open="showResumeUpload"
      title="📄 上传简历 (支持PDF/Word)"
      :footer="null"
    >
      <a-upload-dragger
        name="file"
        :multiple="false"
        :customRequest="handleResumeUpload"
        accept=".pdf,.docx,.doc,.txt"
      >
        <p class="ant-upload-drag-icon">
          <inbox-outlined />
        </p>
        <p class="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p class="ant-upload-hint">支持解析简历中的技能关键词，自动匹配推荐</p>
      </a-upload-dragger>
    </a-modal>
    
    <!-- 技能诊断弹窗 -->
    <a-modal 
      v-model:open="diagnosisVisible" 
      title=""
      width="980px"
      :footer="null"
      :body-style="{ padding: '0' }"
      class="diagnosis-modal"
    >
      <div v-if="diagnosis" class="diagnosis-container">
        <!-- 顶部渐变头部：左侧信息 + 右侧田字形统计 -->
        <div class="diagnosis-header-compact">
          <!-- 左侧：期望职业 + 匹配度 -->
          <div class="header-left">
            <div class="expect-job-compact">
              <span class="label">期望职业</span>
              <span class="value">{{ diagnosis.expected_position || '未设置' }}</span>
              <span class="user-info" v-if="diagnosis.major">{{ diagnosis.education }} · {{ diagnosis.major }}</span>
            </div>
            <div class="match-circle-compact">
              <a-progress 
                type="circle" 
                :percent="diagnosis.position_analysis?.match_rate || 0"
                :size="100"
                :stroke-width="10"
                :stroke-color="getMatchGradientDiagnosis(diagnosis.position_analysis?.match_rate || 0)"
              >
                <template #format="percent">
                  <div class="match-inner-compact">
                    <span class="match-num">{{ percent }}</span>
                    <span class="match-unit">%</span>
                  </div>
                </template>
              </a-progress>
              <div class="match-label-compact">匹配度</div>
            </div>
          </div>
          
          <!-- 右侧：田字形统计卡片 -->
          <div class="stats-grid">
            <div class="stat-mini green">
              <span class="stat-num">{{ diagnosis.skills_analysis?.all_skills?.length || 0 }}</span>
              <span class="stat-label">总技能</span>
            </div>
            <div class="stat-mini blue">
              <span class="stat-num">{{ diagnosis.position_analysis?.matched_skills?.length || 0 }}</span>
              <span class="stat-label">已匹配</span>
            </div>
            <div class="stat-mini red">
              <span class="stat-num">{{ diagnosis.position_analysis?.missing_skills?.length || 0 }}</span>
              <span class="stat-label">待学习</span>
            </div>
            <div class="stat-mini orange">
              <span class="stat-num">{{ diagnosis.market_analysis?.market_match_rate || 0 }}%</span>
              <span class="stat-label">市场</span>
            </div>
          </div>
        </div>
        
        <!-- 主体区域 -->
        <div class="diagnosis-body">
          <a-row :gutter="16">
            <!-- 左侧：技能分布雷达图 -->
            <a-col :span="10">
              <div class="section-card">
                <div class="section-title">📊 技能分布</div>
                <div class="skill-chart-area" style="height: 200px;">
                  <v-chart :option="skillRadarOption" autoresize style="width: 100%; height: 100%;" />
                </div>
              </div>
            </a-col>
            
            <!-- 右侧：技能匹配详情 -->
            <a-col :span="14">
              <div class="section-card">
                <div class="section-title">🎯 技能匹配详情</div>
                <div class="skill-match-grid">
                  <div class="skill-group matched">
                    <div class="group-header">
                      <span class="icon">✅</span>
                      <span class="text">已掌握技能</span>
                      <span class="count">{{ diagnosis.position_analysis?.matched_skills?.length || 0 }}</span>
                    </div>
                    <div class="skill-tags">
                      <span v-for="skill in diagnosis.position_analysis?.matched_skills?.slice(0, 8)" :key="skill" class="skill-tag matched">
                        {{ skill }}
                      </span>
                      <span v-if="(diagnosis.position_analysis?.matched_skills?.length || 0) > 8" class="skill-tag more">
                        +{{ diagnosis.position_analysis.matched_skills.length - 8 }}
                      </span>
                      <span v-if="!diagnosis.position_analysis?.matched_skills?.length" class="empty-text">暂无匹配技能</span>
                    </div>
                  </div>
                  <div class="skill-group missing">
                    <div class="group-header">
                      <span class="icon">📚</span>
                      <span class="text">待学习技能</span>
                      <span class="count">{{ diagnosis.position_analysis?.missing_skills?.length || 0 }}</span>
                    </div>
                    <div class="skill-tags">
                      <span v-for="skill in diagnosis.position_analysis?.missing_skills?.slice(0, 8)" :key="skill" class="skill-tag missing">
                        {{ skill }}
                      </span>
                      <span v-if="(diagnosis.position_analysis?.missing_skills?.length || 0) > 8" class="skill-tag more">
                        +{{ diagnosis.position_analysis.missing_skills.length - 8 }}
                      </span>
                      <span v-if="!diagnosis.position_analysis?.missing_skills?.length" class="empty-text success">🎉 完美匹配</span>
                    </div>
                  </div>
                </div>
              </div>
            </a-col>
          </a-row>
          
          <!-- 同行对比与课程推荐 -->
          <a-row :gutter="16" style="margin-top: 16px;">
            <!-- 同行对比 -->
            <a-col :span="10">
              <div class="section-card">
                <div class="section-title">👥 同行对比</div>
                <div class="peer-compare">
                  <div class="compare-item">
                    <div class="compare-ring">
                      <a-progress type="circle" :percent="Math.min(100, ((diagnosis.skills_analysis?.all_skills?.length || 0) / Math.max(1, diagnosis.peer_comparison?.avg_skills_count || 1)) * 100)" :size="60" :stroke-width="8" stroke-color="#1890ff">
                        <template #format>
                          <span style="font-size: 16px; font-weight: 600;">{{ diagnosis.skills_analysis?.all_skills?.length || 0 }}</span>
                        </template>
                      </a-progress>
                    </div>
                    <div class="compare-label">您的技能</div>
                  </div>
                  <div class="compare-vs">VS</div>
                  <div class="compare-item">
                    <div class="compare-ring">
                      <a-progress type="circle" :percent="100" :size="60" :stroke-width="8" stroke-color="#722ed1">
                        <template #format>
                          <span style="font-size: 16px; font-weight: 600;">{{ diagnosis.peer_comparison?.avg_skills_count || 0 }}</span>
                        </template>
                      </a-progress>
                    </div>
                    <div class="compare-label">同行平均</div>
                  </div>
                </div>
                <div class="peer-skills">
                  <div class="peer-skills-label">同行热门技能：</div>
                  <div class="peer-skills-tags">
                    <a-tag v-for="skill in diagnosis.peer_comparison?.top_skills_in_peers?.slice(0, 5)" :key="skill" color="purple" size="small">{{ skill }}</a-tag>
                  </div>
                </div>
              </div>
            </a-col>
            
            <!-- 推荐课程 -->
            <a-col :span="14">
              <div class="section-card">
                <div class="section-title">📚 推荐课程</div>
                <div class="course-grid">
                  <div v-for="course in diagnosis.recommended_courses?.slice(0, 4)" :key="course.name" class="course-card">
                    <div class="course-name">{{ course.name }}</div>
                    <div class="course-skills">
                      <a-tag v-for="skill in course.covers?.slice(0, 2)" :key="skill" color="blue" size="small">{{ skill }}</a-tag>
                    </div>
                  </div>
                  <div v-if="!diagnosis.recommended_courses?.length" class="course-empty">
                    🎉 您已掌握核心技能
                  </div>
                </div>
              </div>
            </a-col>
          </a-row>
        </div>
        
        <!-- 底部诊断结论 -->
        <div class="diagnosis-footer">
          <a-alert :message="diagnosis.diagnosis?.overall" :type="diagnosis.position_analysis?.match_rate >= 50 ? 'success' : 'info'" show-icon style="margin-bottom: 12px;" />
          <div class="conclusion-grid">
            <div class="conclusion-item strengths">
              <div class="conclusion-title">💪 您的优势</div>
              <div v-for="(s, i) in diagnosis.diagnosis?.strengths?.slice(0, 2)" :key="i" class="conclusion-text">• {{ s }}</div>
            </div>
            <div class="conclusion-item suggestions">
              <div class="conclusion-title">📝 提升建议</div>
              <div v-for="(s, i) in diagnosis.diagnosis?.suggestions?.slice(0, 2)" :key="i" class="conclusion-text">• {{ s }}</div>
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

import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message, notification } from 'ant-design-vue'
import { InboxOutlined, UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { studentApi, commonApi } from '@/api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, RadarComponent } from 'echarts/components'

// 注册 ECharts 组件
use([CanvasRenderer, RadarChart, TitleComponent, TooltipComponent, RadarComponent])

const router = useRouter()

// 用户资料
const initialProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
// 确保 skills 和 courses 是数组
if (!Array.isArray(initialProfile.skills)) initialProfile.skills = []
if (!Array.isArray(initialProfile.courses)) initialProfile.courses = []

const userProfile = ref(initialProfile)

const isLoggedIn = computed(() => !!userProfile.value.student_id && userProfile.value.student_id !== 'STU0001')

const showProfileModal = ref(false)
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
  userProfile.value = {}
  localStorage.removeItem('userProfile')
  message.success('已退出登录')
  // 刷新页面或重置状态
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
    } catch(e) {
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
    message.warning('⚠️ 三层漏斗推荐仅对登录用户开放，请先登录！')
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
    showProfileModal.value = true
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
    showProfileModal.value = true
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
  localStorage.setItem('userProfile', JSON.stringify(userProfile.value))
  showProfileModal.value = false
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
      showProfileModal.value = true // 打开资料确认
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

.filter-card {
  margin-bottom: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* 岗位卡片网格 */
.job-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

/* 现代化岗位卡片 */
.job-card-modern {
  background: white;
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  animation: fadeInUp 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.job-card-modern:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.12);
  border-color: #1890ff;
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
  background: linear-gradient(135deg, #52c41a 0%, #13c2c2 100%);
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
  padding: 4px 10px;
  border-radius: 16px;
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
}

.meta-tag.location {
  background: #e6f7ff;
  color: #1890ff;
}

.meta-tag.education {
  background: #f9f0ff;
  color: #722ed1;
}

.meta-tag.industry {
  background: #fff7e6;
  color: #fa8c16;
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

/* ========== 技能诊断模态框样式 ========== */
:deep(.diagnosis-modal .ant-modal-content) {
  border-radius: 16px;
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
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.diagnosis-modal .ant-modal-close:hover) {
  background: rgba(255, 255, 255, 0.3);
}

.diagnosis-container {
  background: #f5f7fa;
  border-radius: 16px;
  overflow: hidden;
}

/* 紧凑头部：左侧信息+右侧田字形 */
.diagnosis-header-compact {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 16px 16px 0 0;
  gap: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 24px;
  color: white;
}

.expect-job-compact {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.expect-job-compact .label {
  font-size: 12px;
  opacity: 0.8;
}

.expect-job-compact .value {
  font-size: 22px;
  font-weight: 700;
}

.expect-job-compact .user-info {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 2px;
}

.match-circle-compact {
  text-align: center;
}

.match-inner-compact {
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.match-inner-compact .match-num {
  font-size: 26px;
  font-weight: 700;
  color: white;
}

.match-inner-compact .match-unit {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.match-label-compact {
  color: white;
  font-size: 11px;
  margin-top: 4px;
}

/* 田字形统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  width: 180px;
}

.stat-mini {
  padding: 10px 12px;
  border-radius: 8px;
  text-align: center;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
}

.stat-mini .stat-num {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: white;
}

.stat-mini .stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
}

.stat-mini.green { background: rgba(82, 196, 26, 0.3); }
.stat-mini.blue { background: rgba(24, 144, 255, 0.3); }
.stat-mini.red { background: rgba(245, 34, 45, 0.3); }
.stat-mini.orange { background: rgba(250, 140, 22, 0.3); }

/* 保留旧样式兼容 */
.match-circle-area {
  text-align: center;
}

.match-inner {
  display: flex;
  align-items: baseline;
  justify-content: center;
}

.match-inner .match-num {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
}

.match-inner .match-unit {
  font-size: 14px;
  color: #666;
}

.match-label {
  color: white;
  font-size: 12px;
  margin-top: 8px;
}

/* 统计卡片 */
.stats-row {
  display: flex;
  padding: 16px 24px;
  gap: 12px;
  background: white;
}

.stat-card {
  flex: 1;
  padding: 14px;
  border-radius: 10px;
  text-align: center;
}

.stat-card .stat-num {
  display: block;
  font-size: 24px;
  font-weight: 700;
}

.stat-card .stat-label {
  font-size: 12px;
  color: #666;
}

.stat-card.green {
  background: #f6ffed;
}
.stat-card.green .stat-num { color: #52c41a; }

.stat-card.blue {
  background: #e6f7ff;
}
.stat-card.blue .stat-num { color: #1890ff; }

.stat-card.red {
  background: #fff1f0;
}
.stat-card.red .stat-num { color: #f5222d; }

.stat-card.orange {
  background: #fff7e6;
}
.stat-card.orange .stat-num { color: #fa8c16; }

/* 主体区域 */
.diagnosis-body {
  padding: 16px 24px;
}

.section-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  height: 100%;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1a1a1a;
}

/* 技能匹配网格 */
.skill-match-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-group {
  padding: 12px;
  border-radius: 8px;
}

.skill-group.matched {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.skill-group.missing {
  background: #fff7e6;
  border: 1px solid #ffd591;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.group-header .icon {
  font-size: 14px;
}

.group-header .text {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.group-header .count {
  margin-left: auto;
  background: rgba(0,0,0,0.05);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  color: #666;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.skill-tag.matched {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
  color: white;
}

.skill-tag.missing {
  background: #ffd591;
  color: #874d00;
}

.skill-tag.more {
  background: #e6f7ff;
  color: #1890ff;
}

.empty-text {
  color: #999;
  font-size: 12px;
}

.empty-text.success {
  color: #52c41a;
}

/* 同行对比 */
.peer-compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 12px 0;
}

.compare-item {
  text-align: center;
}

.compare-label {
  font-size: 12px;
  color: #666;
  margin-top: 6px;
}

.compare-vs {
  font-size: 18px;
  font-weight: 700;
  color: #d9d9d9;
}

.peer-skills {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.peer-skills-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

.peer-skills-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 课程网格 */
.course-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.course-card {
  background: #fafafa;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.course-name {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
}

.course-skills {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.course-empty {
  grid-column: span 2;
  text-align: center;
  color: #52c41a;
  padding: 24px;
  font-size: 14px;
}

/* 底部诊断结论 */
.diagnosis-footer {
  padding: 16px 24px 24px;
  background: white;
}

.conclusion-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.conclusion-item {
  padding: 12px;
  border-radius: 8px;
}

.conclusion-item.strengths {
  background: #f6ffed;
}

.conclusion-item.suggestions {
  background: #fff7e6;
}

.conclusion-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

.strengths .conclusion-title {
  color: #52c41a;
}

.suggestions .conclusion-title {
  color: #fa8c16;
}

.conclusion-text {
  font-size: 12px;
  color: #333;
  margin-bottom: 4px;
}
</style>
