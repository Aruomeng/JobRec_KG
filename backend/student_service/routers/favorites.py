"""
学生服务 - 收藏相关路由
包含：添加收藏、删除收藏、获取收藏列表、检查收藏状态
"""
from fastapi import APIRouter, HTTPException

from ..models import FavoriteRequest
from ..dependencies import get_neon_connection

router = APIRouter(prefix="/api/student", tags=["favorites"])


@router.post("/favorites")
def add_favorite(request: FavoriteRequest):
    """收藏职位"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO favorites (user_id, job_id, job_title, company, salary, city)
            VALUES (
                (SELECT id FROM users WHERE neo4j_id = %s OR username = %s LIMIT 1),
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (user_id, job_id) DO NOTHING
            RETURNING id
        """, (request.user_id, request.user_id, request.job_id, 
              request.job_title, request.company, request.salary, request.city))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if result:
            return {"code": 200, "message": "收藏成功", "data": {"id": str(result[0])}}
        else:
            return {"code": 200, "message": "已收藏过该职位"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"收藏失败: {str(e)}")


@router.delete("/favorites/{job_id}")
def remove_favorite(job_id: str, user_id: str):
    """取消收藏"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            DELETE FROM favorites 
            WHERE job_id = %s 
            AND user_id = (SELECT id FROM users WHERE neo4j_id = %s OR username = %s LIMIT 1)
        """, (job_id, user_id, user_id))
        
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        if deleted > 0:
            return {"code": 200, "message": "已取消收藏"}
        else:
            return {"code": 404, "message": "未找到该收藏"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消收藏失败: {str(e)}")


@router.get("/favorites")
def get_favorites(user_id: str):
    """获取收藏列表"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT f.id, f.job_id, f.job_title, f.company, f.salary, f.city, f.created_at
            FROM favorites f
            JOIN users u ON f.user_id = u.id
            WHERE u.neo4j_id = %s OR u.username = %s
            ORDER BY f.created_at DESC
        """, (user_id, user_id))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        favorites = []
        for row in rows:
            favorites.append({
                "id": str(row[0]),
                "job_id": row[1],
                "job_title": row[2],
                "company": row[3],
                "salary": row[4],
                "city": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            })
        
        return {"code": 200, "data": favorites}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取收藏列表失败: {str(e)}")


@router.get("/favorites/{job_id}/status")
def check_favorite_status(job_id: str, user_id: str):
    """检查收藏状态"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 1 FROM favorites f
            JOIN users u ON f.user_id = u.id
            WHERE f.job_id = %s AND (u.neo4j_id = %s OR u.username = %s)
        """, (job_id, user_id, user_id))
        
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        
        return {"code": 200, "is_favorited": exists}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查收藏状态失败: {str(e)}")
