/**
 * 用户状态管理 (Pinia Store)
 * 集中管理用户登录状态、用户信息、角色等
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // ==================== State ====================
  const token = ref(localStorage.getItem('token') || null)
  const role = ref(localStorage.getItem('role') || null)
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const userProfile = ref(JSON.parse(localStorage.getItem('userProfile') || '{}'))

  // ==================== Getters ====================
  const isLoggedIn = computed(() => !!token.value)
  
  const studentId = computed(() => {
    return userInfo.value?.student_id || userProfile.value?.student_id || null
  })

  const displayName = computed(() => {
    return userInfo.value?.name || userInfo.value?.display_name || userProfile.value?.name || '用户'
  })

  const skills = computed(() => {
    return userProfile.value?.skills || userInfo.value?.skills || []
  })

  const courses = computed(() => {
    return userProfile.value?.courses || userInfo.value?.courses || []
  })

  // ==================== Actions ====================
  
  /**
   * 登录成功后设置用户信息
   */
  function login(data, userRole = 'student') {
    token.value = 'session-' + (data.student_id || data.user_id)
    role.value = userRole
    userInfo.value = data
    
    // 同步到 localStorage
    localStorage.setItem('token', token.value)
    localStorage.setItem('role', userRole)
    localStorage.setItem('user', JSON.stringify(data))
    
    if (data.student_id) {
      localStorage.setItem('studentId', data.student_id)
    }

    // 合并到 userProfile
    if (userRole === 'student') {
      const localSkills = Array.isArray(userProfile.value.skills) ? userProfile.value.skills : []
      const localCourses = Array.isArray(userProfile.value.courses) ? userProfile.value.courses : []
      const remoteSkills = Array.isArray(data.skills) ? data.skills : []
      const remoteCourses = Array.isArray(data.courses) ? data.courses : []

      userProfile.value = {
        ...userProfile.value,
        student_id: data.student_id,
        name: data.name,
        education: data.education || userProfile.value.education,
        major: data.major || userProfile.value.major,
        expectedJob: data.expected_position || userProfile.value.expectedJob,
        skills: Array.from(new Set([...localSkills, ...remoteSkills])),
        courses: Array.from(new Set([...localCourses, ...remoteCourses]))
      }
      localStorage.setItem('userProfile', JSON.stringify(userProfile.value))
    }
  }

  /**
   * 退出登录
   */
  function logout() {
    token.value = null
    role.value = null
    userInfo.value = null
    userProfile.value = {}

    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('user')
    localStorage.removeItem('studentId')
    localStorage.removeItem('userProfile')
  }

  /**
   * 更新用户资料
   */
  function updateProfile(profileData) {
    userProfile.value = {
      ...userProfile.value,
      ...profileData
    }
    localStorage.setItem('userProfile', JSON.stringify(userProfile.value))
  }

  /**
   * 更新技能列表
   */
  function updateSkills(newSkills) {
    userProfile.value.skills = newSkills
    localStorage.setItem('userProfile', JSON.stringify(userProfile.value))
  }

  /**
   * 更新课程列表
   */
  function updateCourses(newCourses) {
    userProfile.value.courses = newCourses
    localStorage.setItem('userProfile', JSON.stringify(userProfile.value))
  }

  return {
    // State
    token,
    role,
    userInfo,
    userProfile,
    // Getters
    isLoggedIn,
    studentId,
    displayName,
    skills,
    courses,
    // Actions
    login,
    logout,
    updateProfile,
    updateSkills,
    updateCourses
  }
})
