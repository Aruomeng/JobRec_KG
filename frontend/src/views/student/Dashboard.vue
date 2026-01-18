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
        <a-card 
          v-for="(job, index) in paginatedJobs" 
          :key="job.job_id"
          class="job-card hover-card"
          :style="{ animationDelay: `${index * 0.05}s` }"
          hoverable
          @click="goToDetail(job)"
        >
          <!-- 匹配度分数 -->
          <div class="match-score" v-if="job.match_score">
            <a-progress 
              type="circle" 
              :percent="Math.round((job.match_rate || 0) * 100)" 
              :width="50"
              :stroke-color="getScoreColor(job.match_score)"
            />
          </div>
          
          <!-- 职位信息 -->
          <div class="job-info">
            <h3 class="job-title">{{ formatTitle(job.title) }}</h3>
            <p class="job-salary">💰 {{ formatSalary(job.salary) }}</p>
            <p class="job-company">🏢 {{ job.company || '未知公司' }}</p>
            <div class="job-meta">
              <span v-if="job.city">📍 {{ job.city }}</span>
              <a-divider type="vertical" v-if="job.city && job.education" />
              <span v-if="job.education">🎓 {{ job.education }}</span>
            </div>
          </div>
          
          <!-- 技能标签 (显示职位要求的技能) -->
          <div class="skill-tags" v-if="job.required_skills?.length">
            <a-tag 
              v-for="skill in job.required_skills.slice(0, 5)" 
              :key="skill" 
              :color="job.matched_skills?.includes(skill) ? 'success' : 'blue'"
            >
              <template v-if="job.matched_skills?.includes(skill)">✓ </template>{{ skill }}
            </a-tag>
            <a-tag v-if="job.required_skills.length > 5" color="default">
              +{{ job.required_skills.length - 5 }}
            </a-tag>
          </div>
          
          <!-- 推荐理由 -->
          <div class="job-reason" v-if="job.explanation">
            {{ job.explanation }}
          </div>
          
          <!-- 洞察模式: 推理路径 (Beta) -->
          <div v-if="job.insight?.skill_paths?.length" style="margin-top: 12px; background: #f0f7ff; padding: 8px; border-radius: 4px; border: 1px dashed #91caff;">
            <div style="font-size: 12px; font-weight: bold; color: #1890ff; margin-bottom: 4px;">
              🎯 洞察模式：AI推理路径
            </div>
            <div v-for="(path, idx) in job.insight.skill_paths" :key="idx" style="font-size: 12px; margin-bottom: 2px;">
              <span style="color: #666;">您掌握的</span>
              <template v-if="path.direct_match">
                <span style="font-weight: bold; color: #52c41a;">直接技能</span>
              </template>
              <template v-else>
                 课程 <span style="font-weight: bold; color: #722ed1;">{{ path.sources.join(', ') }}</span>
              </template>
              <span style="color: #666;"> -> 赋予了技能 </span>
              <a-tag color="blue" style="margin: 0 4px">{{ path.skill }}</a-tag>
              <span style="color: #666;"> -> 匹配职位需求</span>
            </div>
          </div>
        </a-card>
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
      title="🔬 技能诊断报告"
      width="920px"
      :footer="null"
      :body-style="{ padding: '18px' }"
    >
      <div v-if="diagnosis">
        <!-- 顶部：紧凑横向布局 -->
        <div style="display: flex; gap: 12px; margin-bottom: 16px; height: 150px;">
          <!-- 左侧：期望职业 -->
          <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; padding: 14px; color: white; width: 140px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 14px; opacity: 0.9;">期望职业</div>
            <div style="font-size: 22px; font-weight: 600; margin-top: 4px;">{{ diagnosis.expected_position || '未设置' }}</div>
            <div v-if="diagnosis.major" style="font-size: 10px; opacity: 0.9; margin-top: 26px;">
              {{ diagnosis.education }} · {{ diagnosis.major }}
            </div>
          </div>
          
          <!-- 中间：匹配度环形图（放大） -->
          <div style="display: flex; align-items: center; justify-content: center; width: 120px;">
            <a-progress 
              type="circle" 
              :percent="diagnosis.position_analysis?.match_rate || 0"
              :size="100"
              :stroke-width="10"
              :stroke-color="{ '0%': '#667eea', '100%': '#52c41a' }"
            >
              <template #format="percent">
                <span style="font-size: 22px; font-weight: 700;">{{ percent }}%</span>
                <div style="font-size: 10px; color: #666;">匹配度</div>
              </template>
            </a-progress>
          </div>
          
          <!-- 统计数据：竖直排列 -->
          <div style="display: flex; flex-direction: column; justify-content: space-between; gap: 4px; width: 70px;">
            <div style="text-align: center; padding: 4px 8px; background: #f6ffed; border-radius: 6px; flex: 1; display: flex; flex-direction: column; justify-content: center;">
              <div style="font-size: 16px; font-weight: 700; color: #52c41a;">{{ diagnosis.skills_analysis?.all_skills?.length || 0 }}</div>
              <div style="font-size: 9px; color: #666;">总技能</div>
            </div>
            <div style="text-align: center; padding: 4px 8px; background: #e6f7ff; border-radius: 6px; flex: 1; display: flex; flex-direction: column; justify-content: center;">
              <div style="font-size: 16px; font-weight: 700; color: #1890ff;">{{ diagnosis.position_analysis?.matched_skills?.length || 0 }}</div>
              <div style="font-size: 9px; color: #666;">已匹配</div>
            </div>
            <div style="text-align: center; padding: 4px 8px; background: #fff1f0; border-radius: 6px; flex: 1; display: flex; flex-direction: column; justify-content: center;">
              <div style="font-size: 16px; font-weight: 700; color: #f5222d;">{{ diagnosis.position_analysis?.missing_skills?.length || 0 }}</div>
              <div style="font-size: 9px; color: #666;">待学习</div>
            </div>
            <div style="text-align: center; padding: 4px 8px; background: #fff7e6; border-radius: 6px; flex: 1; display: flex; flex-direction: column; justify-content: center;">
              <div style="font-size: 14px; font-weight: 700; color: #fa8c16;">{{ diagnosis.market_analysis?.market_match_rate || 0 }}%</div>
              <div style="font-size: 9px; color: #666;">市场</div>
            </div>
          </div>
          
          <!-- 右侧：技能分类分布 -->
          <div style="background: #fafafa; border-radius: 8px; padding: 10px 12px; flex: 1;">
            <div style="font-size: 11px; color: #666; margin-bottom: 6px; font-weight: 500;">📊 技能分布</div>
            <div v-for="cat in skillCategories" :key="cat.name" style="margin-bottom: 4px;">
              <div style="display: flex; justify-content: space-between; font-size: 10px; color: #666;">
                <span>{{ cat.name }}</span>
                <span>{{ cat.count }}项</span>
              </div>
              <a-progress :percent="cat.percent" :show-info="false" :stroke-width="5" :stroke-color="cat.color" size="small" />
            </div>
            <div v-if="!skillCategories.length" style="text-align: center; color: #999; font-size: 10px; padding: 20px 0;">暂无分类数据</div>
          </div>
        </div>

        <!-- Tabs 切换详情 - 固定高度 -->
        <a-tabs v-model:activeKey="diagnosisTab" size="small">
          <!-- 技能分析 Tab -->
          <a-tab-pane key="skills" tab="📊 技能分析">
            <div style="height: 120px;">
              <a-row :gutter="12">
                <a-col :span="12">
                  <a-card size="small" style="height: 120px;">
                    <template #title><span style="color: #52c41a; font-size: 13px;">✅ 已掌握技能</span></template>
                    <div style="display: flex; flex-wrap: wrap; gap: 5px; max-height: 82px; overflow-y: auto;">
                      <a-tag v-for="skill in diagnosis.position_analysis?.matched_skills?.slice(0, 10)" :key="skill" color="success" size="small">{{ skill }}</a-tag>
                      <span v-if="!diagnosis.position_analysis?.matched_skills?.length" style="color: #999; font-size: 12px;">暂无匹配</span>
                    </div>
                  </a-card>
                </a-col>
                <a-col :span="12">
                  <a-card size="small" style="height: 120px;">
                    <template #title><span style="color: #f5222d; font-size: 13px;">❌ 技能缺口</span></template>
                    <div style="display: flex; flex-wrap: wrap; gap: 5px; max-height: 82px; overflow-y: auto;">
                      <a-tag v-for="skill in diagnosis.position_analysis?.missing_skills?.slice(0, 10)" :key="skill" color="error" size="small">{{ skill }}</a-tag>
                      <span v-if="!diagnosis.position_analysis?.missing_skills?.length" style="color: #52c41a; font-size: 12px;">🎉 完美匹配</span>
                    </div>
                  </a-card>
                </a-col>
              </a-row>
            </div>
          </a-tab-pane>

          <!-- 同行对比 Tab -->
          <a-tab-pane key="peers" tab="👥 同行对比">
            <div style="height: 120px; display: flex; align-items: center;">
              <a-row :gutter="20" align="middle" style="width: 100%;">
                <a-col :span="8" style="text-align: center;">
                  <a-progress type="circle" :percent="Math.min(100, (diagnosis.skills_analysis?.all_skills?.length || 0) / Math.max(1, diagnosis.peer_comparison?.avg_skills_count || 1) * 100)" :size="75" :stroke-width="8">
                    <template #format>
                      <span style="font-size: 18px; font-weight: 600;">{{ diagnosis.skills_analysis?.all_skills?.length || 0 }}</span>
                    </template>
                  </a-progress>
                  <div style="font-size: 12px; color: #666; margin-top: 4px;">您的技能</div>
                </a-col>
                <a-col :span="8" style="text-align: center;">
                  <a-progress type="circle" :percent="100" :size="75" :stroke-width="8" stroke-color="#722ed1">
                    <template #format>
                      <span style="font-size: 18px; font-weight: 600;">{{ diagnosis.peer_comparison?.avg_skills_count || 0 }}</span>
                    </template>
                  </a-progress>
                  <div style="font-size: 12px; color: #666; margin-top: 4px;">同行平均</div>
                </a-col>
                <a-col :span="8">
                  <div style="font-size: 12px; color: #666; margin-bottom: 6px; font-weight: 500;">同行热门技能</div>
                  <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                    <a-tag v-for="skill in diagnosis.peer_comparison?.top_skills_in_peers?.slice(0, 5)" :key="skill" color="purple" size="small">{{ skill }}</a-tag>
                  </div>
                </a-col>
              </a-row>
            </div>
          </a-tab-pane>

          <!-- 推荐课程 Tab -->
          <a-tab-pane key="courses" tab="📚 推荐课程">
            <div style="height: 120px;">
              <a-row :gutter="10">
                <a-col v-for="course in diagnosis.recommended_courses?.slice(0, 4)" :key="course.name" :span="6">
                  <a-card size="small" hoverable style="text-align: center; height: 100%;">
                    <div style="font-weight: 500; font-size: 12px; margin-bottom: 4px;">{{ course.name }}</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 2px; justify-content: center;">
                      <a-tag v-for="skill in course.covers?.slice(0, 2)" :key="skill" color="blue" size="small" style="font-size: 10px;">{{ skill }}</a-tag>
                    </div>
                  </a-card>
                </a-col>
                <a-col v-if="!diagnosis.recommended_courses?.length" :span="24">
                  <div style="text-align: center; color: #999; padding: 40px 0; font-size: 13px;">暂无推荐课程</div>
                </a-col>
              </a-row>
            </div>
          </a-tab-pane>


        </a-tabs>

        <!-- 底部：诊断结论 -->
        <a-card size="small" style="margin-top: 12px; background: #fafafa;">
          <a-row :gutter="16">
            <a-col :span="24">
              <a-alert :message="diagnosis.diagnosis?.overall" :type="diagnosis.position_analysis?.match_rate >= 50 ? 'success' : 'info'" show-icon style="margin-bottom: 10px;" />
            </a-col>
            <a-col :span="12">
              <div style="font-size: 13px; font-weight: 600; color: #52c41a; margin-bottom: 6px;">💪 您的优势</div>
              <div v-for="(s, i) in diagnosis.diagnosis?.strengths?.slice(0, 2)" :key="i" style="font-size: 12px; color: #333; margin-bottom: 3px;">• {{ s }}</div>
            </a-col>
            <a-col :span="12">
              <div style="font-size: 13px; font-weight: 600; color: #fa8c16; margin-bottom: 6px;">📝 提升建议</div>
              <div v-for="(s, i) in diagnosis.diagnosis?.suggestions?.slice(0, 2)" :key="i" style="font-size: 12px; color: #333; margin-bottom: 3px;">• {{ s }}</div>
            </a-col>
          </a-row>
        </a-card>
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

const getScoreColor = (score) => {
  if (score >= 0.8) return '#52c41a'
  if (score >= 0.6) return '#1890ff'
  if (score >= 0.4) return '#faad14'
  return '#ff4d4f'
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
}

.welcome-banner {
  background: linear-gradient(135deg, #1890ff 0%, #722ed1 100%);
  border-radius: 16px;
  padding: 40px;
  margin-bottom: 24px;
  color: white;
}

.welcome-content h1 {
  font-size: 28px;
  margin-bottom: 12px;
  color: white;
}

.welcome-content p {
  font-size: 16px;
  opacity: 0.9;
  margin-bottom: 20px;
}

.filter-card {
  margin-bottom: 24px;
  border-radius: 12px;
}

.job-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 24px;
}

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

.match-score {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
  background: white;
  border-radius: 8px; /* 方形带小圆角 */
  padding: 4px;
}

.job-info {
  margin-bottom: 12px;
}

.job-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1890ff;
  padding-right: 65px; /* 为圆环预留空间 */
  line-height: 1.4;
  word-break: break-word;
}

.job-salary {
  font-size: 16px;
  color: #52c41a;
  font-weight: 500;
  margin-bottom: 4px;
}

.job-company {
  color: #666;
  margin-bottom: 4px;
  font-size: 14px;
}

.job-meta {
  color: #999;
  font-size: 13px;
  margin-top: 4px;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.job-reason {
  font-size: 13px;
  color: #666;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  line-height: 1.5;
}

.pagination-container {
  margin-top: 32px;
  display: flex;
  justify-content: center;
  padding-bottom: 24px;
}
</style>
