import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// ==================== 学生端 API ====================
export const studentApi = {
  // 热门职位
  getHotJobs: (limit = 20) =>
    api.get("/student/hot-jobs", { params: { limit } }),

  // 职位推荐
  recommendJobs: (studentId, topK = 10) =>
    api.post("/student/recommend-jobs", { student_id: studentId, top_k: topK }),

  // 基于技能推荐 (支持深度学习开关)
  recommendBySkills: (
    skills,
    topK = 20,
    city = null,
    studentId = null,
    useModel = false
  ) =>
    api.post("/student/recommend-by-skills", {
      skills,
      top_k: topK,
      city,
      student_id: studentId,
      use_model: useModel,
    }),

  // 学生登录
  login: (username, password) => api.post('/student/login', { username, password }),

  // 上传简历解析
  uploadResume: (formData) =>
    api.post("/student/parse-resume", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  // 课程规划
  planCoursePath: (studentId, targetJobId) =>
    api.post("/student/course-path", {
      student_id: studentId,
      target_job_id: targetJobId,
    }),

  // 技能诊断
  diagnoseSkills: (studentId, skills = []) =>
    api.post('/student/skill-diagnosis', {
      student_id: studentId,
      skills: skills
    }),

  // 获取可选课程列表（支持专业参数）
  getCourses: (major = null) => api.get('/student/get-courses', { params: { major } }),

  // 保存学生课程选择
  saveCourses: (studentId, courses) =>
    api.post('/student/save-courses', {
      student_id: studentId,
      courses: courses
    }),

  // 更新个人信息 (Name, Education, Major, Expected Position, Skills)
  updateProfile: (profileData) => 
    api.post('/student/update-profile', profileData),

  // 获取用户完整信息（包括技能和课程）
  getProfile: (studentId) => api.get(`/student/get-profile/${studentId}`),

  // 获取职位详情
  getJobDetail: (jobId) => api.get(`/job/detail/${encodeURIComponent(jobId)}`),

  // 获取职位知识图谱
  getJobGraph: (jobId, userSkills = [], displayCity = null) =>
    api.post(`/job/${encodeURIComponent(jobId)}/graph`, {
      user_skills: userSkills,
      display_city: displayCity,
    }),

  // 三层漏斗混合推荐
  hybridRecommend: (
    studentId,
    finalK = 20,
    recallK = 500,
    rankK = 50,
    weights = null,
    city = null,
    salary = null,
    includeInsight = false
  ) =>
    api.post("/student/hybrid-recommend", {
      student_id: studentId,
      recall_k: recallK,
      rank_k: rankK,
      final_k: finalK,
      weights: weights,
      city: city,
      salary: salary,
      include_insight: includeInsight
    }),

  // ==================== 收藏职位 ====================
  // 收藏职位
  addFavorite: (userId, jobId, jobTitle, company, salary, city) =>
    api.post("/student/favorites", {
      user_id: userId,
      job_id: jobId,
      job_title: jobTitle,
      company: company,
      salary: salary,
      city: city,
    }),

  // 取消收藏
  removeFavorite: (jobId, userId) =>
    api.delete(`/student/favorites/${encodeURIComponent(jobId)}`, {
      params: { user_id: userId }
    }),

  // 获取收藏列表
  getFavorites: (userId) =>
    api.get("/student/favorites", { params: { user_id: userId } }),

  // 检查收藏状态
  checkFavoriteStatus: (jobId, userId) =>
    api.get(`/student/favorites/${encodeURIComponent(jobId)}/status`, {
      params: { user_id: userId }
    }),
};

export const commonApi = {
  getCities: () => api.get("/common/cities"),
};

// ==================== 企业端 API ====================
export const enterpriseApi = {
  // 人才召回
  scoutTalents: (jobId, topK = 20, educationFilter = null) =>
    api.post("/enterprise/scout-talents", {
      job_id: jobId,
      top_k: topK,
      education_filter: educationFilter,
    }),

  // 简历透视
  xrayResume: (studentId, jobId) =>
    api.post("/enterprise/resume-xray", {
      student_id: studentId,
      job_id: jobId,
    }),
};

// ==================== 高校端 API ====================
export const universityApi = {
  // Gap分析
  analyzeSkillGap: (topK = 20) =>
    api.get("/university/skill-gap", { params: { top_k: topK } }),

  // 课程健康度
  evaluateCourses: (limit = 30) =>
    api.get("/university/course-health", { params: { limit } }),

  // 改革建议
  getReformSuggestions: () => api.get("/university/reform-suggestions"),
};

export default api;
