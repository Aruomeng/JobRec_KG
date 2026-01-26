<template>
    <div class="login-container">
        <!-- 背景层 - 使用opacity过渡实现渐变切换 -->
        <div class="bg-layer student-bg" :class="{ active: role === 'student' }"></div>
        <div class="bg-layer enterprise-bg" :class="{ active: role === 'enterprise' }"></div>
        <div class="bg-layer university-bg" :class="{ active: role === 'university' }"></div>

        <!-- 动态六边形背景 -->
        <div class="hexagons-container">
            <div v-for="n in 25" :key="n" class="hexagon" :style="hexagonStyle(n)"></div>
        </div>

        <!-- 登录卡片 -->
        <div class="login-card">
            <!-- 头部 -->
            <div class="login-header" :style="{ background: themeGradient }">
                <transition name="content-fade" mode="out-in">
                    <div class="header-content" :key="role">
                        <div class="logo-icon">{{ roleIcon }}</div>
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
                            <span v-if="!loading">登录</span>
                        </a-button>
                    </a-form-item>
                </a-form>

                <!-- 切换入口 -->
                <div class="role-switch">
                    <div class="role-tabs">
                        <div v-for="r in roles" :key="r.key" @click="switchRole(r.key)"
                            :class="['role-tab', { active: role === r.key }]"
                            :style="role === r.key ? { background: themeColor, color: '#fff' } : {}">
                            <span class="tab-icon">{{ r.icon }}</span>
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
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const role = computed(() => route.params.role || 'student')

const roles = [
    { key: 'student', label: '学生', icon: '📚' },
    { key: 'enterprise', label: '企业', icon: '🏢' },
    { key: 'university', label: '高校', icon: '🎓' }
]

const themeConfig = {
    student: {
        color: '#667eea',
        gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        icon: '📚',
        title: '学生就业服务平台',
        bg: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)'
    },
    enterprise: {
        color: '#f093fb',
        gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        icon: '🏢',
        title: '企业人才招聘平台',
        bg: 'linear-gradient(135deg, #1e1e2f 0%, #2d132c 50%, #4a1942 100%)'
    },
    university: {
        color: '#4facfe',
        gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        icon: '🎓',
        title: '高校就业管理平台',
        bg: 'linear-gradient(135deg, #0c1618 0%, #1c3334 50%, #1d4e5f 100%)'
    }
}

const themeColor = computed(() => themeConfig[role.value]?.color)
const themeGradient = computed(() => themeConfig[role.value]?.gradient)
const roleIcon = computed(() => themeConfig[role.value]?.icon)
const roleTitle = computed(() => themeConfig[role.value]?.title)
const dynamicBackground = computed(() => themeConfig[role.value]?.bg)

// 六边形样式生成器 - 使用固定种子避免切换时重新生成
const hexagonSeeds = Array.from({ length: 25 }, (_, i) => ({
    left: ((i * 37 + 13) % 100),
    delay: ((i * 23 + 7) % 50) / 10,
    duration: 18 + ((i * 31 + 11) % 20),
    size: 8 + ((i * 17 + 5) % 72), // 8px - 80px 更大的尺寸差异
    opacity: 0.1 + ((i * 19 + 3) % 25) / 100
}))

const hexagonStyle = (n) => {
    const seed = hexagonSeeds[n - 1]
    return {
        left: `${seed.left}%`,
        animationDelay: `${seed.delay}s`,
        animationDuration: `${seed.duration}s`,
        '--hex-size': `${seed.size}px`,
        '--hex-opacity': seed.opacity
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
            localStorage.setItem('user', JSON.stringify(res.data.data))
            localStorage.setItem('token', 'session-' + (res.data.data.student_id || res.data.data.user_id))
            localStorage.setItem('role', currentRole)
            if (currentRole === 'student') {
                localStorage.setItem('studentId', res.data.data.student_id)
            }
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
    background: linear-gradient(135deg, #1e1e2f 0%, #2d132c 50%, #4a1942 100%);
}

.university-bg {
    background: linear-gradient(135deg, #0c1618 0%, #1c3334 50%, #1d4e5f 100%);
}

/* 六边形科技背景 */
.hexagons-container {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
    z-index: 1;
}

.hexagon {
    position: absolute;
    bottom: -60px;
    width: var(--hex-size, 30px);
    height: var(--hex-size, 30px);
    background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.2) 0%,
            rgba(255, 255, 255, 0.05) 100%);
    clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
    opacity: var(--hex-opacity, 0.2);
    animation: hex-float linear infinite;
    box-shadow:
        0 0 10px rgba(255, 255, 255, 0.1),
        inset 0 0 15px rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.15);
}

.hexagon::before {
    content: '';
    position: absolute;
    inset: 2px;
    background: transparent;
    clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

/* 部分六边形添加发光效果 */
.hexagon:nth-child(3n) {
    box-shadow:
        0 0 20px rgba(102, 126, 234, 0.3),
        0 0 40px rgba(102, 126, 234, 0.1);
}

.hexagon:nth-child(5n) {
    box-shadow:
        0 0 20px rgba(79, 172, 254, 0.3),
        0 0 40px rgba(79, 172, 254, 0.1);
}

.hexagon:nth-child(7n) {
    box-shadow:
        0 0 20px rgba(240, 147, 251, 0.3),
        0 0 40px rgba(240, 147, 251, 0.1);
}

@keyframes hex-float {
    0% {
        transform: translateY(0) scale(0.9);
        opacity: 0;
    }

    5% {
        opacity: var(--hex-opacity, 0.2);
    }

    50% {
        transform: translateY(-50vh) scale(1);
    }

    95% {
        opacity: var(--hex-opacity, 0.2);
    }

    100% {
        transform: translateY(-110vh) scale(0.9);
        opacity: 0;
    }
}

/* 登录卡片 */
.login-card {
    width: 100%;
    max-width: 400px;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(10px);
    z-index: 10;
}

.login-header {
    padding: 40px 30px 30px;
    text-align: center;
    color: white;
}

.logo-icon {
    font-size: 56px;
    margin-bottom: 12px;
    display: inline-block;
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
}

.login-btn {
    height: 48px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 8px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s, box-shadow 0.2s;
}

.login-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
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
    gap: 6px;
    padding: 10px 16px;
    border-radius: 20px;
    background: #f0f2f5;
    color: #666;
    font-size: 14px;
    text-decoration: none;
    transition: all 0.3s ease;
}

.role-tab:hover {
    background: #e6e8eb;
    transform: translateY(-2px);
}

.role-tab.active {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
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

/* 去掉Ant Design输入框边框 */
:deep(.ant-input-affix-wrapper) {
    border-radius: 8px;
    border: 1px solid #e8e8e8;
}

:deep(.ant-input-affix-wrapper:hover),
:deep(.ant-input-affix-wrapper:focus) {
    border-color: v-bind(themeColor);
}
</style>
