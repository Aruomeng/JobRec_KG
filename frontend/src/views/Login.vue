<template>
    <div class="login-container">
        <!-- 背景层 - 使用opacity过渡实现渐变切换 -->
        <div class="bg-layer student-bg" :class="{ active: role === 'student' }"></div>
        <div class="bg-layer enterprise-bg" :class="{ active: role === 'enterprise' }"></div>
        <div class="bg-layer university-bg" :class="{ active: role === 'university' }"></div>

        <!-- 太空网格前进效果 -->
        <div class="space-grid-container">
            <div class="grid-plane"></div>
            <div class="stars-layer">
                <div v-for="n in 50" :key="n" class="star" :style="starStyle(n)"></div>
            </div>
        </div>

        <!-- 登录卡片 -->
        <div class="login-card">
            <!-- 头部 -->
            <div class="login-header" :style="{ background: themeGradient }">
                <transition name="content-fade" mode="out-in">
                    <div class="header-content" :key="role">
                        <component :is="roleIconComponent" class="logo-icon-svg" />
                        <h1>智途 AI</h1>
                        <p>{{ roleTitle }}</p>
                    </div>
                </transition>
            </div>

            <!-- 表单 -->
            <div class="login-body">
                <a-form :model="loginForm" @finish="handleLogin">
                    <a-form-item name="username" :rules="[{ required: true, message: '请输入用户名' }]">
                        <a-input v-model:value="loginForm.username" size="large" placeholder="用户名 / 手机号">
                            <template #prefix>
                                <UserOutlined style="color: #999" />
                            </template>
                        </a-input>
                    </a-form-item>
                    <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
                        <a-input-password v-model:value="loginForm.password" size="large" placeholder="密码">
                            <template #prefix>
                                <LockOutlined style="color: #999" />
                            </template>
                        </a-input-password>
                    </a-form-item>
                    <a-form-item>
                        <a-button type="primary" html-type="submit" size="large" block :loading="loading"
                            class="login-btn" :style="{ background: themeGradient, border: 'none' }">
                            {{ loading ? '登录中...' : '登录' }}
                        </a-button>
                    </a-form-item>
                </a-form>

                <!-- 切换入口 -->
                <div class="role-switch">
                    <div class="role-tabs">
                        <div v-for="r in roles" :key="r.key" @click="switchRole(r.key)"
                            :class="['role-tab', { active: role === r.key }]"
                            :style="role === r.key ? { background: themeColor, color: '#fff' } : {}">
                            <component :is="getRoleIconComponent(r.key)" class="tab-icon-svg" />
                            <span class="tab-text">{{ r.label }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, ReadOutlined, BankOutlined, BookOutlined } from '@ant-design/icons-vue'
import axios from 'axios'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const role = computed(() => route.params.role || 'student')

const roles = [
    { key: 'student', label: '学生', iconComponent: ReadOutlined },
    { key: 'enterprise', label: '企业', iconComponent: BankOutlined },
    { key: 'university', label: '高校', iconComponent: BookOutlined }
]

const themeConfig = {
    student: {
        color: '#667eea',
        gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        iconComponent: ReadOutlined,
        title: '学生就业服务平台',
        bg: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)'
    },
    enterprise: {
        color: '#3B82F6',
        gradient: 'linear-gradient(135deg, #3B82F6 0%, #6366F1 100%)',
        iconComponent: BankOutlined,
        title: '企业人才招聘平台',
        bg: 'linear-gradient(135deg, #1E293B 0%, #334155 50%, #3B82F6 100%)'
    },
    university: {
        color: '#4facfe',
        gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        iconComponent: BookOutlined,
        title: '高校就业管理平台',
        bg: 'linear-gradient(135deg, #0c1618 0%, #1c3334 50%, #1d4e5f 100%)'
    }
}

const themeColor = computed(() => themeConfig[role.value]?.color)
const themeGradient = computed(() => themeConfig[role.value]?.gradient)
const roleIconComponent = computed(() => themeConfig[role.value]?.iconComponent)
const roleTitle = computed(() => themeConfig[role.value]?.title)
const dynamicBackground = computed(() => themeConfig[role.value]?.bg)

const getRoleIconComponent = (key) => themeConfig[key]?.iconComponent

// 星星样式生成器
const starStyle = (n) => {
    const left = ((n * 37 + 13) % 100)
    const top = ((n * 23 + 7) % 100)
    const delay = ((n * 19 + 3) % 30) / 10
    const duration = 2 + ((n * 17 + 11) % 30) / 10
    const size = 1 + ((n * 13 + 5) % 3)
    return {
        left: `${left}%`,
        top: `${top}%`,
        width: `${size}px`,
        height: `${size}px`,
        animationDelay: `${delay}s`,
        animationDuration: `${duration}s`
    }
}

// API配置
const apiPorts = { student: 8001, enterprise: 8002, university: 8003 }
const getApiBaseUrl = () => `http://localhost:${apiPorts[role.value]}`

const loading = ref(false)
const loginForm = ref({ username: '', password: '' })

// 无刷新切换端
const switchRole = (newRole) => {
    if (newRole !== role.value) {
        router.push(`/login/${newRole}`)
    }
}

const handleLogin = async () => {
    loading.value = true
    try {
        const currentRole = role.value
        const baseUrl = getApiBaseUrl()
        const apiPath = currentRole === 'student'
            ? '/api/student/login'
            : currentRole === 'enterprise'
                ? '/api/enterprise/login'
                : '/api/university/login'

        const res = await axios.post(`${baseUrl}${apiPath}`, {
            username: loginForm.value.username,
            password: loginForm.value.password
        })

        if (res.data.code === 200) {
            // 使用 Pinia store 设置用户状态
            userStore.login(res.data.data, currentRole)
            message.success('登录成功')
            window.location.href = `/${currentRole}`
        }
    } catch (e) {
        message.error(e.response?.data?.detail || '登录失败')
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    margin: 0;
    position: relative;
    overflow: hidden;
    background: #1a1a2e;
}

/* 背景层 - 使用opacity实现渐变过渡 */
.bg-layer {
    position: absolute;
    inset: 0;
    opacity: 0;
    transition: opacity 0.8s ease-in-out;
    z-index: 0;
}

.bg-layer.active {
    opacity: 1;
}

.student-bg {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.enterprise-bg {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #1E40AF 100%);
}

.university-bg {
    background: linear-gradient(135deg, #0c1618 0%, #1c3334 50%, #1d4e5f 100%);
}

/* 太空隧道前进效果 */
.space-grid-container {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
    z-index: 1;
}

.grid-plane {
    position: absolute;
    inset: 0;
    background:
        repeating-linear-gradient(0deg,
            transparent,
            transparent 100px,
            rgba(255, 255, 255, 0.06) 100px,
            rgba(255, 255, 255, 0.06) 102px);
    animation: tunnel-move 2.5s linear infinite;
}

.grid-plane::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 80% 50% at 50% 50%, transparent 30%, rgba(0, 0, 0, 0.6) 100%);
}

.grid-plane::after {
    content: '';
    position: absolute;
    inset: 0;
    background:
        repeating-linear-gradient(90deg,
            transparent,
            transparent 100px,
            rgba(255, 255, 255, 0.04) 100px,
            rgba(255, 255, 255, 0.04) 102px);
}

@keyframes tunnel-move {
    0% {
        background-position: 0 0;
    }

    100% {
        background-position: 0 102px;
    }
}

/* 星星层 */
.stars-layer {
    position: absolute;
    inset: 0;
}

.star {
    position: absolute;
    background: white;
    border-radius: 50%;
    opacity: 0;
    animation: star-twinkle ease-in-out infinite;
}

.star:nth-child(3n) {
    background: #a5b4fc;
}

.star:nth-child(5n) {
    background: #93c5fd;
}

.star:nth-child(7n) {
    background: #c4b5fd;
}

@keyframes star-twinkle {

    0%,
    100% {
        opacity: 0.2;
        transform: scale(0.8);
    }

    50% {
        opacity: 1;
        transform: scale(1.2);
    }
}

/* 登录卡片 - Glassmorphism */
.login-card {
    width: 100%;
    max-width: 420px;
    background: rgba(15, 23, 42, 0.75);
    border-radius: 24px;
    overflow: hidden;
    box-shadow:
        0 25px 80px rgba(0, 0, 0, 0.5),
        0 8px 32px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    z-index: 10;
    transition: transform 0.3s ease-out, box-shadow 0.3s ease-out;
}

.login-card:hover {
    transform: translateY(-4px);
    box-shadow:
        0 32px 100px rgba(0, 0, 0, 0.6),
        0 12px 40px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.15);
}

.login-header {
    padding: 40px 30px 30px;
    text-align: center;
    color: white;
}

.logo-icon-svg {
    font-size: 56px;
    margin-bottom: 12px;
    display: block;
    color: white;
}

.tab-icon-svg {
    font-size: 18px;
}

.login-header h1 {
    font-size: 28px;
    font-weight: 700;
    margin: 0;
    letter-spacing: 3px;
}

.login-header p {
    font-size: 14px;
    opacity: 0.9;
    margin-top: 8px;
}

.login-body {
    padding: 30px;
    background: rgba(255, 255, 255, 0.95);
}

.login-btn {
    height: 52px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(3, 105, 161, 0.3);
    transition: all 0.25s ease-out;
    position: relative;
    overflow: hidden;
}

.login-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, transparent 50%, rgba(255, 255, 255, 0.1) 100%);
    opacity: 0;
    transition: opacity 0.25s ease-out;
}

.login-btn:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(3, 105, 161, 0.4);
}

.login-btn:hover::after {
    opacity: 1;
}

.login-btn:active {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(3, 105, 161, 0.3);
}

/* 角色切换 */
.role-switch {
    margin-top: 24px;
}

.role-tabs {
    display: flex;
    gap: 8px;
    justify-content: center;
}

.role-tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    border-radius: 24px;
    background: rgba(240, 249, 255, 0.8);
    color: #64748B;
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    transition: all 0.25s ease-out;
    cursor: pointer;
    border: 1px solid rgba(3, 105, 161, 0.1);
}

.role-tab:hover {
    background: rgba(224, 242, 254, 0.9);
    border-color: rgba(3, 105, 161, 0.2);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(3, 105, 161, 0.1);
}

.role-tab.active {
    box-shadow: 0 4px 16px rgba(3, 105, 161, 0.25);
    border-color: transparent;
}

.tab-icon {
    font-size: 16px;
}

/* 动画 - 内容淡入淡出 */
.content-fade-enter-active,
.content-fade-leave-active {
    transition: opacity 0.3s ease, transform 0.3s ease;
}

.content-fade-enter-from {
    opacity: 0;
    transform: translateY(-10px);
}

.content-fade-leave-to {
    opacity: 0;
    transform: translateY(10px);
}

.icon-bounce-enter-active {
    animation: bounce-in 0.5s;
}

@keyframes bounce-in {
    0% {
        transform: scale(0);
    }

    50% {
        transform: scale(1.2);
    }

    100% {
        transform: scale(1);
    }
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

/* 输入框样式增强 */
:deep(.ant-input-affix-wrapper) {
    border-radius: 12px;
    border: 1px solid rgba(100, 116, 139, 0.2);
    background: transparent !important;
    transition: all 0.25s ease-out;
}

:deep(.ant-input-affix-wrapper:hover) {
    border-color: rgba(100, 116, 139, 0.4);
    background: rgba(248, 250, 252, 0.5) !important;
}

:deep(.ant-input-affix-wrapper-focused),
:deep(.ant-input-affix-wrapper:focus) {
    border-color: #3B82F6;
    background: rgba(248, 250, 252, 0.8) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

:deep(.ant-input) {
    font-family: 'Poppins', sans-serif;
    background: transparent !important;
}

:deep(.ant-input-password) {
    background: transparent !important;
}
</style>
