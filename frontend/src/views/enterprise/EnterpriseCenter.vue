<template>
    <div class="enterprise-center">
        <a-layout class="center-layout">
            <!-- 固定左侧边栏 -->
            <a-layout-sider v-model:collapsed="collapsed" :trigger="null" collapsible class="fixed-sidebar" :width="160"
                :collapsed-width="56">
                <!-- Logo区域 -->
                <div class="sidebar-logo">
                    <div class="logo-content">
                        <BankOutlined class="logo-icon" />
                        <transition name="fade">
                            <span v-show="!collapsed" class="logo-text">企业中心</span>
                        </transition>
                    </div>
                </div>

                <!-- 菜单 -->
                <a-menu v-model:selectedKeys="selectedKeys" mode="inline" class="sidebar-menu"
                    :inline-collapsed="collapsed">
                    <a-menu-item key="profile">
                        <template #icon>
                            <IdcardOutlined />
                        </template>
                        <span>企业资料</span>
                    </a-menu-item>
                    <a-menu-item key="jobs">
                        <template #icon>
                            <FileTextOutlined />
                        </template>
                        <span>职位管理</span>
                    </a-menu-item>
                    <a-menu-item key="publish">
                        <template #icon>
                            <PlusCircleOutlined />
                        </template>
                        <span>发布职位</span>
                    </a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="talent" @click="$router.push('/enterprise')">
                        <template #icon>
                            <TeamOutlined />
                        </template>
                        <span>人才搜索</span>
                    </a-menu-item>
                </a-menu>

                <!-- 折叠按钮 -->
                <div class="collapse-trigger" @click="collapsed = !collapsed">
                    <MenuFoldOutlined v-if="!collapsed" />
                    <MenuUnfoldOutlined v-else />
                </div>
            </a-layout-sider>

            <!-- 右侧内容区 -->
            <a-layout class="content-wrapper" :style="{ marginLeft: collapsed ? '56px' : '160px' }">
                <a-layout-content class="main-content">

                    <!-- 企业资料 -->
                    <div v-show="selectedKeys[0] === 'profile'" class="page-container">
                        <div class="page-header">
                            <h1>
                                <IdcardOutlined /> 企业资料
                            </h1>
                            <p>管理您的企业基本信息</p>
                        </div>
                        <a-card class="content-card">
                            <a-form :model="profile" layout="vertical" @finish="saveProfile">
                                <a-row :gutter="24">
                                    <a-col :span="12">
                                        <a-form-item label="企业名称" required>
                                            <a-input v-model:value="profile.company_name" placeholder="请输入企业名称"
                                                size="large">
                                                <template #prefix>
                                                    <BankOutlined />
                                                </template>
                                            </a-input>
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="所属行业">
                                            <a-select v-model:value="profile.industry" placeholder="选择行业" size="large">
                                                <a-select-option value="互联网/IT">互联网/IT</a-select-option>
                                                <a-select-option value="金融">金融</a-select-option>
                                                <a-select-option value="教育">教育</a-select-option>
                                                <a-select-option value="医疗健康">医疗健康</a-select-option>
                                                <a-select-option value="制造业">制造业</a-select-option>
                                                <a-select-option value="电商/零售">电商/零售</a-select-option>
                                            </a-select>
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                                <a-row :gutter="24">
                                    <a-col :span="12">
                                        <a-form-item label="企业规模">
                                            <a-select v-model:value="profile.company_scale" placeholder="选择规模"
                                                size="large">
                                                <a-select-option value="20人以下">20人以下</a-select-option>
                                                <a-select-option value="20-99人">20-99人</a-select-option>
                                                <a-select-option value="100-499人">100-499人</a-select-option>
                                                <a-select-option value="500-999人">500-999人</a-select-option>
                                                <a-select-option value="1000人以上">1000人以上</a-select-option>
                                            </a-select>
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="所在城市">
                                            <a-input v-model:value="profile.city" placeholder="请输入城市" size="large">
                                                <template #prefix>
                                                    <EnvironmentOutlined />
                                                </template>
                                            </a-input>
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                                <a-form-item label="联系方式">
                                    <a-input v-model:value="profile.contact_info" placeholder="联系电话或邮箱" size="large">
                                        <template #prefix>
                                            <PhoneOutlined />
                                        </template>
                                    </a-input>
                                </a-form-item>
                                <a-form-item label="企业简介">
                                    <a-textarea v-model:value="profile.description" placeholder="介绍您的企业..." :rows="4" />
                                </a-form-item>
                                <a-form-item>
                                    <a-button type="primary" html-type="submit" :loading="saving" size="large">
                                        <SaveOutlined /> 保存资料
                                    </a-button>
                                </a-form-item>
                            </a-form>
                        </a-card>
                    </div>

                    <!-- 职位管理 -->
                    <div v-show="selectedKeys[0] === 'jobs'" class="page-container">
                        <div class="page-header">
                            <h1>
                                <FileTextOutlined /> 职位管理
                            </h1>
                            <p>管理您发布的所有职位</p>
                        </div>
                        <a-spin :spinning="loadingJobs">
                            <div v-if="jobs.length === 0" class="empty-box">
                                <a-empty description="暂无发布的职位">
                                    <a-button type="primary" @click="selectedKeys = ['publish']">
                                        <PlusOutlined /> 发布第一个职位
                                    </a-button>
                                </a-empty>
                            </div>
                            <div v-else class="jobs-grid">
                                <a-card v-for="job in jobs" :key="job.job_id" class="job-item" hoverable>
                                    <template #extra>
                                        <a-tag :color="job.status === 'active' ? 'success' : 'warning'">
                                            {{ job.status === 'active' ? '招聘中' : '已暂停' }}
                                        </a-tag>
                                    </template>
                                    <template #title>{{ job.title }}</template>
                                    <div class="job-info">
                                        <span>
                                            <DollarOutlined /> {{ job.salary }}
                                        </span>
                                        <span>
                                            <BookOutlined /> {{ job.education }}
                                        </span>
                                        <span>
                                            <ClockCircleOutlined /> {{ job.experience }}
                                        </span>
                                    </div>
                                    <div class="job-tags">
                                        <a-tag v-for="skill in job.skills.slice(0, 4)" :key="skill" color="magenta">{{
                                            skill
                                        }}</a-tag>
                                    </div>
                                    <template #actions>
                                        <a-tooltip title="编辑"><a-button type="text" @click="editJob(job)">
                                                <EditOutlined />
                                            </a-button></a-tooltip>
                                        <a-tooltip :title="job.status === 'active' ? '暂停' : '恢复'">
                                            <a-button type="text" @click="toggleJobStatus(job)">
                                                <PauseCircleOutlined v-if="job.status === 'active'" />
                                                <PlayCircleOutlined v-else />
                                            </a-button>
                                        </a-tooltip>
                                        <a-popconfirm title="确定删除此职位?" @confirm="deleteJob(job.job_id)">
                                            <a-tooltip title="删除"><a-button type="text" danger>
                                                    <DeleteOutlined />
                                                </a-button></a-tooltip>
                                        </a-popconfirm>
                                    </template>
                                </a-card>
                            </div>
                        </a-spin>
                    </div>

                    <!-- 发布职位 -->
                    <div v-show="selectedKeys[0] === 'publish'" class="page-container">
                        <div class="page-header">
                            <h1>
                                <PlusCircleOutlined /> {{ editingJob ? '编辑职位' : '发布新职位' }}
                            </h1>
                            <p>{{ editingJob ? '修改职位信息' : '填写职位详情发布到平台' }}</p>
                        </div>
                        <a-card class="content-card">
                            <a-form :model="jobForm" layout="vertical" @finish="saveJob">
                                <a-form-item label="职位名称" required>
                                    <a-input v-model:value="jobForm.title" placeholder="如: 前端开发工程师" size="large" />
                                </a-form-item>
                                <a-row :gutter="24">
                                    <a-col :span="12">
                                        <a-form-item label="学历要求">
                                            <a-select v-model:value="jobForm.education" size="large">
                                                <a-select-option value="不限">不限</a-select-option>
                                                <a-select-option value="大专">大专</a-select-option>
                                                <a-select-option value="本科">本科</a-select-option>
                                                <a-select-option value="硕士">硕士</a-select-option>
                                            </a-select>
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="经验要求">
                                            <a-select v-model:value="jobForm.experience" size="large">
                                                <a-select-option value="不限">不限</a-select-option>
                                                <a-select-option value="应届生">应届生</a-select-option>
                                                <a-select-option value="1-3年">1-3年</a-select-option>
                                                <a-select-option value="3-5年">3-5年</a-select-option>
                                                <a-select-option value="5年以上">5年以上</a-select-option>
                                            </a-select>
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                                <a-row :gutter="24">
                                    <a-col :span="12">
                                        <a-form-item label="薪资下限 (K)">
                                            <a-input-number v-model:value="jobForm.salary_min" :min="0" :max="100"
                                                style="width: 100%" size="large" />
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="薪资上限 (K)">
                                            <a-input-number v-model:value="jobForm.salary_max" :min="0" :max="100"
                                                style="width: 100%" size="large" />
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                                <a-form-item label="技能要求">
                                    <a-select v-model:value="jobForm.skills" mode="tags" placeholder="输入技能后回车添加"
                                        size="large" />
                                </a-form-item>
                                <a-form-item label="职位描述" required>
                                    <a-textarea v-model:value="jobForm.description" :rows="6"
                                        placeholder="详细描述岗位职责和任职要求..." />
                                </a-form-item>
                                <a-form-item>
                                    <a-space>
                                        <a-button type="primary" html-type="submit" :loading="savingJob" size="large">
                                            <CheckOutlined /> {{ editingJob ? '保存修改' : '发布职位' }}
                                        </a-button>
                                        <a-button v-if="editingJob" @click="cancelEdit" size="large">取消编辑</a-button>
                                    </a-space>
                                </a-form-item>
                            </a-form>
                        </a-card>
                    </div>

                </a-layout-content>
            </a-layout>
        </a-layout>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { message } from 'ant-design-vue'
import {
    BankOutlined, IdcardOutlined, FileTextOutlined, PlusCircleOutlined, TeamOutlined,
    MenuFoldOutlined, MenuUnfoldOutlined, EditOutlined, DeleteOutlined, SaveOutlined,
    EnvironmentOutlined, PhoneOutlined, DollarOutlined, BookOutlined, ClockCircleOutlined,
    PlusOutlined, CheckOutlined, PauseCircleOutlined, PlayCircleOutlined
} from '@ant-design/icons-vue'
import axios from 'axios'

const API_BASE = 'http://localhost:8002'

const userInfo = computed(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}') } catch { return {} }
})

const collapsed = ref(false)
const selectedKeys = ref(['profile'])
const saving = ref(false)
const loadingJobs = ref(false)
const savingJob = ref(false)
const editingJob = ref(null)

const profile = ref({ company_name: '', industry: '', company_scale: '', city: '', contact_info: '', description: '' })
const jobs = ref([])
const jobForm = ref({ title: '', description: '', education: '不限', experience: '不限', salary_min: 0, salary_max: 0, skills: [] })

const fetchProfile = async () => {
    try {
        const { data } = await axios.get(`${API_BASE}/api/enterprise/profile`, { params: { user_id: userInfo.value.user_id } })
        if (data.code === 200) profile.value = data.data
    } catch (err) { console.error(err) }
}

const saveProfile = async () => {
    saving.value = true
    try {
        const { data } = await axios.put(`${API_BASE}/api/enterprise/profile`, profile.value, { params: { user_id: userInfo.value.user_id } })
        if (data.code === 200) message.success('资料保存成功')
    } catch (err) { message.error('保存失败') }
    finally { saving.value = false }
}

const fetchJobs = async () => {
    loadingJobs.value = true
    try {
        const { data } = await axios.get(`${API_BASE}/api/enterprise/jobs`, { params: { user_id: userInfo.value.user_id } })
        if (data.code === 200) jobs.value = data.data
    } catch (err) { console.error(err) }
    finally { loadingJobs.value = false }
}

const editJob = (job) => { editingJob.value = job; jobForm.value = { ...job }; selectedKeys.value = ['publish'] }
const cancelEdit = () => { editingJob.value = null; resetJobForm(); selectedKeys.value = ['jobs'] }

const saveJob = async () => {
    if (!jobForm.value.title) { message.warning('请输入职位名称'); return }
    savingJob.value = true
    try {
        if (editingJob.value) {
            await axios.put(`${API_BASE}/api/enterprise/jobs/${editingJob.value.job_id}`, jobForm.value)
            message.success('职位更新成功')
        } else {
            await axios.post(`${API_BASE}/api/enterprise/jobs`, jobForm.value, { params: { user_id: userInfo.value.user_id } })
            message.success('职位发布成功')
        }
        editingJob.value = null; resetJobForm(); fetchJobs(); selectedKeys.value = ['jobs']
    } catch (err) { message.error(err.response?.data?.detail || '操作失败') }
    finally { savingJob.value = false }
}

const toggleJobStatus = async (job) => {
    try {
        await axios.put(`${API_BASE}/api/enterprise/jobs/${job.job_id}`, { status: job.status === 'active' ? 'inactive' : 'active' })
        message.success('状态已更新'); fetchJobs()
    } catch { message.error('操作失败') }
}

const deleteJob = async (jobId) => {
    try {
        await axios.delete(`${API_BASE}/api/enterprise/jobs/${jobId}`, { params: { user_id: userInfo.value.user_id } })
        message.success('职位已删除'); fetchJobs()
    } catch (err) { message.error('删除失败') }
}

const resetJobForm = () => { jobForm.value = { title: '', description: '', education: '不限', experience: '不限', salary_min: 0, salary_max: 0, skills: [] } }

onMounted(() => { fetchProfile(); fetchJobs() })
</script>

<style scoped>
.enterprise-center {
    position: fixed;
    top: 64px;
    left: 0;
    right: 0;
    bottom: 0;
    background: #ffffff;
    overflow: hidden;
}

.center-layout {
    height: 100%;
    background: #ffffff;
}

/* 固定侧边栏 - 浅色主题 */
.fixed-sidebar {
    position: fixed !important;
    left: 0;
    top: 64px;
    bottom: 0;
    z-index: 100;
    background: #ffffff !important;
    border-right: 1px solid #f0f0f0;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
    overflow: hidden;
}

.sidebar-logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #3B82F6 0%, #6366F1 100%);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-content {
    display: flex;
    align-items: center;
    gap: 10px;
    color: white;
}

.logo-icon {
    font-size: 26px;
}

.logo-text {
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
}

.sidebar-menu {
    background: transparent !important;
    border: none !important;
    padding: 12px 0;
}

:deep(.sidebar-menu .ant-menu-item) {
    color: #555 !important;
    margin: 2px 8px !important;
    border-radius: 6px !important;
    height: 40px !important;
    line-height: 40px !important;
}

:deep(.sidebar-menu .ant-menu-item:hover) {
    background: #EFF6FF !important;
    color: #1E3A5F !important;
}

:deep(.sidebar-menu .ant-menu-item-selected) {
    background: #EFF6FF !important;
    color: #1E3A5F !important;
    font-weight: 500;
}

:deep(.sidebar-menu .ant-menu-item-selected::after) {
    display: none !important;
}


.collapse-trigger {
    position: absolute;
    bottom: 20px;
    left: 0;
    right: 0;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    cursor: pointer;
    transition: all 0.2s;
}

.collapse-trigger:hover {
    color: #1E3A5F;
    background: #EFF6FF;
}

/* 内容区 */
.content-wrapper {
    transition: margin-left 0.2s;
    height: 100%;
    background: #ffffff;
}

.main-content {
    padding: 24px;
    height: 100%;
    overflow-y: auto;
    background: #ffffff;
}

.page-container {
    max-width: 900px;
}

.page-header {
    margin-bottom: 24px;
}

.page-header h1 {
    font-size: 26px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: #1f1f1f;
    display: flex;
    align-items: center;
    gap: 10px;
}

.page-header p {
    color: #666;
    margin: 0;
    font-size: 14px;
}

.content-card {
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

/* 职位网格 */
.jobs-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
}

.job-item {
    border-radius: 12px;
}

.job-item:hover {
    box-shadow: 0 4px 20px rgba(30, 58, 95, 0.12);
}

.job-info {
    display: flex;
    gap: 16px;
    color: #666;
    margin-bottom: 12px;
    font-size: 13px;
}

.job-tags {
    margin-top: 8px;
}

.empty-box {
    padding: 80px 0;
    background: white;
    border-radius: 12px;
}

/* 主题按钮 */
:deep(.ant-btn-primary) {
    background: linear-gradient(135deg, #3B82F6 0%, #6366F1 100%) !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

:deep(.ant-btn-primary:hover) {
    background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
