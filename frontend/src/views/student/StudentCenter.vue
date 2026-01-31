<template>
    <div class="student-center">
        <a-layout class="center-layout">
            <!-- 固定左侧边栏 -->
            <a-layout-sider v-model:collapsed="collapsed" :trigger="null" collapsible class="fixed-sidebar" :width="180"
                :collapsed-width="56">
                <!-- Logo区域 -->
                <div class="sidebar-logo">
                    <div class="logo-content">
                        <ReadOutlined class="logo-icon" />
                        <transition name="fade">
                            <span v-show="!collapsed" class="logo-text">个人中心</span>
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
                        <span>个人资料</span>
                    </a-menu-item>
                    <a-menu-item key="favorites">
                        <template #icon>
                            <StarOutlined />
                        </template>
                        <span>收藏职位</span>
                    </a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="home" @click="$router.push('/student')">
                        <template #icon>
                            <HomeOutlined />
                        </template>
                        <span>返回首页</span>
                    </a-menu-item>
                </a-menu>

                <!-- 折叠按钮 -->
                <div class="collapse-trigger" @click="collapsed = !collapsed">
                    <MenuFoldOutlined v-if="!collapsed" />
                    <MenuUnfoldOutlined v-else />
                </div>
            </a-layout-sider>

            <!-- 右侧内容区 -->
            <a-layout class="content-wrapper" :style="{ marginLeft: collapsed ? '56px' : '200px' }">
                <a-layout-content class="main-content">

                    <!-- 个人资料 -->
                    <div v-show="selectedKeys[0] === 'profile'" class="page-container">
                        <div class="page-header">
                            <h1>
                                <IdcardOutlined /> 个人资料
                            </h1>
                            <p>管理您的个人信息</p>
                        </div>
                        <a-card class="content-card">
                            <a-form :model="profile" layout="vertical" @finish="saveProfile">
                                <a-row :gutter="24">
                                    <a-col :span="12">
                                        <a-form-item label="姓名" required>
                                            <a-input v-model:value="profile.name" placeholder="请输入姓名" size="large">
                                                <template #prefix>
                                                    <UserOutlined />
                                                </template>
                                            </a-input>
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="学号">
                                            <a-input v-model:value="profile.student_id" disabled size="large">
                                                <template #prefix>
                                                    <IdcardOutlined />
                                                </template>
                                            </a-input>
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                                <a-row :gutter="24">
                                    <a-col :span="12">
                                        <a-form-item label="学历">
                                            <a-select v-model:value="profile.education" placeholder="选择学历" size="large">
                                                <a-select-option value="本科">本科</a-select-option>
                                                <a-select-option value="硕士">硕士</a-select-option>
                                                <a-select-option value="博士">博士</a-select-option>
                                            </a-select>
                                        </a-form-item>
                                    </a-col>
                                    <a-col :span="12">
                                        <a-form-item label="专业">
                                            <a-input v-model:value="profile.major" placeholder="请输入专业" size="large">
                                                <template #prefix>
                                                    <BookOutlined />
                                                </template>
                                            </a-input>
                                        </a-form-item>
                                    </a-col>
                                </a-row>
                                <a-row :gutter="24">
                                    <a-col :span="24">
                                        <a-form-item label="期望职位">
                                            <a-input v-model:value="profile.expected_position" placeholder="请输入期望职位"
                                                size="large">
                                                <template #prefix>
                                                    <AimOutlined />
                                                </template>
                                            </a-input>
                                        </a-form-item>
                                    </a-col>
                                </a-row>

                                <!-- 技能选择 -->
                                <a-form-item label="掌握的技能（输入并回车添加）">
                                    <a-select v-model:value="profile.skills" mode="tags" placeholder="输入并回车添加技能"
                                        :options="commonSkills" size="large" />
                                </a-form-item>

                                <!-- 课程选择 -->
                                <a-form-item label="已修课程（用于更精准的推荐）">
                                    <a-select v-model:value="profile.courses" mode="multiple" placeholder="选择已修课程"
                                        :options="courseOptions" :loading="coursesLoading" show-search
                                        :filter-option="filterCourse" size="large" style="width: 100%">
                                        <template #option="{ label, skills }">
                                            <div>
                                                <span>{{ label }}</span>
                                                <span style="color: #999; font-size: 12px; margin-left: 8px">{{
                                                    skills?.join(', ') }}</span>
                                            </div>
                                        </template>
                                    </a-select>
                                    <div style="margin-top: 8px; color: #666; font-size: 12px">
                                        已选 {{ profile.courses?.length || 0 }} 门课程
                                    </div>
                                </a-form-item>

                                <a-form-item>
                                    <a-button type="primary" html-type="submit" size="large" :loading="saving"
                                        class="save-btn">
                                        <SaveOutlined /> 保存修改
                                    </a-button>
                                </a-form-item>
                            </a-form>
                        </a-card>
                    </div>

                    <!-- 收藏职位 -->
                    <div v-show="selectedKeys[0] === 'favorites'" class="page-container">
                        <div class="page-header">
                            <h1>
                                <StarOutlined /> 收藏职位
                            </h1>
                            <p>您收藏的所有职位</p>
                        </div>

                        <a-spin :spinning="loadingFavorites">
                            <div v-if="favorites.length === 0" class="empty-state">
                                <a-empty description="暂无收藏的职位">
                                    <a-button type="primary" @click="$router.push('/student')">
                                        去发现职位
                                    </a-button>
                                </a-empty>
                            </div>
                            <div v-else class="favorites-grid">
                                <div v-for="job in favorites" :key="job.id" class="favorite-card"
                                    @click="viewJobDetail(job)">
                                    <div class="card-header">
                                        <h3 class="job-title">{{ job.job_title || '未知职位' }}</h3>
                                        <a-button type="text" danger size="small" class="remove-btn"
                                            @click.stop="removeFavorite(job)">
                                            <DeleteOutlined />
                                        </a-button>
                                    </div>
                                    <div class="job-company">
                                        <BankOutlined /> {{ job.company || '未知公司' }}
                                    </div>
                                    <div class="job-meta">
                                        <span class="salary" v-if="job.salary">{{ job.salary }}</span>
                                        <span class="city" v-if="job.city">
                                            <EnvironmentOutlined /> {{ job.city }}
                                        </span>
                                    </div>
                                    <div class="card-footer">
                                        <span class="time">收藏于 {{ formatTime(job.created_at) }}</span>
                                    </div>
                                </div>
                            </div>
                        </a-spin>
                    </div>

                </a-layout-content>
            </a-layout>
        </a-layout>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
    ReadOutlined, IdcardOutlined, StarOutlined, HomeOutlined,
    MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined, BookOutlined,
    AimOutlined, SaveOutlined, DeleteOutlined, BankOutlined, EnvironmentOutlined
} from '@ant-design/icons-vue'
import { studentApi } from '@/api'

const router = useRouter()

const collapsed = ref(false)
const selectedKeys = ref(['profile'])
const saving = ref(false)
const loadingFavorites = ref(false)

// 个人资料
const profile = ref({
    name: '',
    student_id: '',
    education: '',
    major: '',
    expected_position: '',
    skills: [],
    courses: []
})

// 课程相关
const coursesLoading = ref(false)
const courseOptions = ref([])
const commonSkills = [
    { value: 'Python', label: 'Python' },
    { value: 'Java', label: 'Java' },
    { value: 'JavaScript', label: 'JavaScript' },
    { value: 'Vue', label: 'Vue' },
    { value: 'React', label: 'React' },
    { value: 'Spring', label: 'Spring' },
    { value: 'MySQL', label: 'MySQL' },
    { value: 'Redis', label: 'Redis' },
    { value: 'Docker', label: 'Docker' },
    { value: '机器学习', label: '机器学习' },
    { value: '深度学习', label: '深度学习' },
    { value: '数据分析', label: '数据分析' },
]

// 收藏列表
const favorites = ref([])

// 获取用户ID
const getUserId = () => {
    const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
    return userProfile.student_id || ''
}

// 加载个人资料
const loadProfile = () => {
    const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
    profile.value = {
        name: userProfile.name || '',
        student_id: userProfile.student_id || '',
        education: userProfile.education || '',
        major: userProfile.major || '',
        expected_position: userProfile.expected_position || '',
        skills: userProfile.skills || [],
        courses: userProfile.courses || []
    }
}

// 加载课程列表
const loadCourses = async () => {
    coursesLoading.value = true
    try {
        const { data } = await studentApi.getCourses(profile.value.major)
        courseOptions.value = (data.courses || []).map(c => ({
            value: c.name,
            label: c.name,
            skills: c.skills
        }))
    } catch (e) {
        console.error('加载课程失败', e)
    } finally {
        coursesLoading.value = false
    }
}

// 课程搜索过滤
const filterCourse = (input, option) => {
    return option.label.toLowerCase().includes(input.toLowerCase())
}

// 保存个人资料
const saveProfile = async () => {
    saving.value = true
    try {
        // 保存个人资料
        await studentApi.updateProfile({
            student_id: profile.value.student_id,
            name: profile.value.name,
            education: profile.value.education,
            major: profile.value.major,
            expected_position: profile.value.expected_position,
            skills: profile.value.skills
        })

        // 保存课程选择
        if (profile.value.courses?.length > 0) {
            await studentApi.saveCourses(profile.value.student_id, profile.value.courses)
        }

        // 更新本地存储
        const userProfile = JSON.parse(localStorage.getItem('userProfile') || '{}')
        Object.assign(userProfile, profile.value)
        localStorage.setItem('userProfile', JSON.stringify(userProfile))
        message.success('保存成功')
    } catch (e) {
        message.error('保存失败: ' + (e.response?.data?.detail || e.message))
    } finally {
        saving.value = false
    }
}

// 加载收藏列表
const loadFavorites = async () => {
    loadingFavorites.value = true
    try {
        const userId = getUserId()
        if (!userId) {
            favorites.value = []
            return
        }
        const { data } = await studentApi.getFavorites(userId)
        favorites.value = data.data || []
    } catch (e) {
        console.error('加载收藏失败', e)
        favorites.value = []
    } finally {
        loadingFavorites.value = false
    }
}

// 取消收藏
const removeFavorite = async (job) => {
    try {
        const userId = getUserId()
        await studentApi.removeFavorite(job.job_id, userId)
        favorites.value = favorites.value.filter(f => f.id !== job.id)
        message.success('已取消收藏')
    } catch (e) {
        message.error('取消收藏失败')
    }
}

// 查看职位详情
const viewJobDetail = (job) => {
    router.push({
        path: `/student/job/${encodeURIComponent(job.job_id)}`,
        query: { title: job.job_title, company: job.company, salary: job.salary, city: job.city }
    })
}

// 格式化时间
const formatTime = (isoString) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
    loadProfile()
    loadFavorites()
    loadCourses()
})
</script>

<style scoped>
.student-center {
    height: 100vh;
    overflow: hidden;
    background: #ffffff;
}

.center-layout {
    min-height: 100vh;
}

:deep(.center-layout.ant-layout) {
    background: #ffffff !important;
}

:deep(.center-layout .ant-layout) {
    background: #ffffff !important;
}

:deep(.center-layout .ant-layout-content) {
    background: #ffffff !important;
}

/* 左侧边栏 */
.fixed-sidebar {
    position: fixed !important;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    background: #ffffff !important;
    border-right: 1px solid #f0f0f0;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

:deep(.fixed-sidebar.ant-layout-sider) {
    background: #ffffff !important;
}

:deep(.fixed-sidebar .ant-layout-sider-children) {
    background: #ffffff !important;
}

.sidebar-logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

/* 菜单样式 */
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
    color: #667eea !important;
}

:deep(.sidebar-menu .ant-menu-item-selected) {
    background: #EFF6FF !important;
    color: #667eea !important;
    font-weight: 500;
}

:deep(.sidebar-menu .ant-menu-item-selected::after) {
    display: none !important;
}

:deep(.sidebar-menu .ant-menu-item .anticon) {
    font-size: 18px;
}

/* 折叠按钮 */
.collapse-trigger {
    position: absolute;
    bottom: 20px;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 40px;
    cursor: pointer;
    color: #666;
    transition: all 0.2s;
}

.collapse-trigger:hover {
    color: #667eea;
}

/* 内容区 */
.content-wrapper {
    transition: margin-left 0.2s;
    height: 100vh;
}

.main-content {
    height: 100vh;
    padding: 24px;
    overflow-y: auto;
}

.page-container {
    max-width: 1200px;
    margin: 0 auto;
}

.page-header {
    margin-bottom: 24px;
}

.page-header h1 {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0;
}

.page-header p {
    color: #666;
    margin-top: 4px;
}

.content-card {
    border-radius: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.save-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    height: 48px;
    padding: 0 32px;
    border-radius: 10px;
}

/* 收藏列表 */
.empty-state {
    padding: 80px 0;
    text-align: center;
}

.favorites-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
}

.favorite-card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    cursor: pointer;
    transition: all 0.2s;
    border: 1px solid #f0f0f0;
}

.favorite-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    border-color: #667eea;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}

.job-title {
    font-size: 17px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0;
    flex: 1;
}

.remove-btn {
    opacity: 0.6;
}

.remove-btn:hover {
    opacity: 1;
}

.job-company {
    color: #666;
    font-size: 14px;
    margin-bottom: 8px;
}

.job-meta {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
}

.salary {
    color: #667eea;
    font-weight: 600;
}

.city {
    color: #999;
    font-size: 13px;
}

.card-footer {
    border-top: 1px solid #f0f0f0;
    padding-top: 12px;
}

.time {
    color: #999;
    font-size: 12px;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
