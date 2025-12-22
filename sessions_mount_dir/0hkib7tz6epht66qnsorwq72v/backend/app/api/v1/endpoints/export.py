from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from ....core.database import get_db
from ....crud.member import get_members
from ....core.rbac import get_current_user, require_permission
from ....models.user import User
from ....core.audit import log_audit
import csv
import io
from datetime import datetime

router = APIRouter()

@router.get("/members")
def export_members(
    background_tasks: BackgroundTasks,
    level: Optional[str] = Query(None, description="会员等级筛选"),
    is_active: Optional[bool] = Query(None, description="是否激活筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(1000, ge=1, le=10000, description="导出记录数限制"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出会员信息为CSV格式
    """
    # 检查导出权限
    require_permission(current_user, "member:export")
    
    # 获取会员数据
    members = get_members(
        db=db,
        skip=skip,
        limit=limit,
        level=level,
        is_active=is_active
    )
    
    if not members:
        raise HTTPException(status_code=404, detail="没有找到符合条件的会员数据")
    
    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow([
        "ID",
        "姓名",
        "手机号",
        "邮箱",
        "会员等级",
        "积分",
        "剩余会籍(月)",
        "是否激活",
        "创建时间",
        "更新时间",
        "备注"
    ])
    
    # 写入数据
    for member in members:
        writer.writerow([
            member.id,
            member.name,
            member.phone,
            member.email,
            member.level,
            member.points,
            member.remaining_membership,
            "是" if member.is_active else "否",
            member.created_at.strftime("%Y-%m-%d %H:%M:%S") if member.created_at else "",
            member.updated_at.strftime("%Y-%m-%d %H:%M:%S") if member.updated_at else "",
            member.notes or ""
        ])
    
    # 记录审计日志
    background_tasks.add_task(
        log_audit,
        user_id=current_user.id,
        action="export",
        resource_type="member",
        details=f"导出会员数据，条件: level={level}, is_active={is_active}, 数量: {len(members)}"
    )
    
    # 准备响应
    output.seek(0)
    filename = f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
