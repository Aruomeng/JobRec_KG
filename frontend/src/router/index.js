import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/login/student'
  },
  // 登录路由
  {
    path: '/login/:role',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  // 学生端
  {
    path: '/student',
    name: 'student',
    component: () => import('@/views/student/Dashboard.vue'),
    meta: { title: '学生端', theme: 'blue', requiresAuth: true, role: 'student' }
  },
  {
    path: '/student/job/:id',
    name: 'jobDetail',
    component: () => import('@/views/student/JobDetail.vue'),
    meta: { title: '职位详情', theme: 'blue', requiresAuth: true, role: 'student' }
  },
  // 企业端
  {
    path: '/enterprise',
    name: 'enterprise',
    component: () => import('@/views/enterprise/TalentScout.vue'),
    meta: { title: '企业端', theme: 'purple', requiresAuth: true, role: 'enterprise' }
  },
  {
    path: '/enterprise/candidate/:id',
    name: 'candidateDetail',
    component: () => import('@/views/enterprise/CandidateDetail.vue'),
    meta: { title: '候选人详情', theme: 'purple', requiresAuth: true, role: 'enterprise' }
  },
  // 高校端
  {
    path: '/university',
    name: 'university',
    component: () => import('@/views/university/GapAnalysis.vue'),
    meta: { title: '高校端', theme: 'orange', requiresAuth: true, role: 'university' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 认证守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  
  // 需要认证的页面
  if (to.meta.requiresAuth && !token) {
    const role = to.meta.role || 'student'
    next(`/login/${role}`)
    return
  }
  
  // 已登录用户访问登录页，跳转到对应端
  if (to.name === 'login' && token) {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    const role = user.role || to.params.role || 'student'
    next(`/${role}`)
    return
  }
  
  next()
})

export default router
