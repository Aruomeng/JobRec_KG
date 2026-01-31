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
  {
    path: '/student/center',
    name: 'studentCenter',
    component: () => import('@/views/student/StudentCenter.vue'),
    meta: { title: '个人中心', theme: 'blue', requiresAuth: true, role: 'student' }
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
  {
    path: '/enterprise/center',
    name: 'enterpriseCenter',
    component: () => import('@/views/enterprise/EnterpriseCenter.vue'),
    meta: { title: '企业中心', theme: 'purple', requiresAuth: true, role: 'enterprise' }
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

// 认证守卫 (使用 Pinia store)
router.beforeEach((to, from, next) => {
  // 动态导入 store (避免循环依赖)
  import('@/stores/user').then(({ useUserStore }) => {
    const userStore = useUserStore()
    
    // 需要认证的页面
    if (to.meta.requiresAuth && !userStore.isLoggedIn) {
      const role = to.meta.role || 'student'
      next(`/login/${role}`)
      return
    }
    
    // 已登录用户访问登录页，跳转到对应端
    if (to.name === 'login' && userStore.isLoggedIn) {
      const role = userStore.role || to.params.role || 'student'
      next(`/${role}`)
      return
    }
    
    next()
  })
})

export default router

