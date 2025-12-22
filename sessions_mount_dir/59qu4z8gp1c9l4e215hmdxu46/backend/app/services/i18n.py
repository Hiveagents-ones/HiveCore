from typing import Dict, Optional
from fastapi import Request
from fastapi.templating import Jinja2Templates

class I18nService:
    """
    多语言资源管理服务
    
    提供多语言支持，包括文本翻译和本地化功能
    """
    
    def __init__(self):
        self._translations: Dict[str, Dict[str, str]] = {
            "en": {
                "member_management": "Member Management",
                "member_id": "Member ID",
                "member_name": "Name",
                "member_phone": "Phone",
                "member_email": "Email",
                "join_date": "Join Date",
                "member_card_status": "Card Status",
                "member_level": "Member Level"
            },
            "zh": {
                "member_management": "会员管理",
                "member_id": "会员ID",
                "member_name": "姓名",
                "member_phone": "电话",
                "member_email": "邮箱",
                "join_date": "加入日期",
                "member_card_status": "卡片状态",
                "member_level": "会员等级"
            }
        }
        self.templates = Jinja2Templates(directory="backend/app/templates")
    
    async def get_translation(self, key: str, lang: str = "en") -> str:
        """
        获取指定键的翻译文本
        
        Args:
            key: 翻译键
            lang: 语言代码 (默认: en)
            
        Returns:
            翻译后的文本
        """
        return self._translations.get(lang, {}).get(key, key)
    
    async def render_template(
        self, 
        request: Request, 
        template_name: str, 
        context: Optional[dict] = None,
        lang: str = "en"
    ):
        """
        渲染带有国际化支持的模板
        
        Args:
            request: FastAPI 请求对象
            template_name: 模板文件名
            context: 模板上下文
            lang: 语言代码 (默认: en)
            
        Returns:
            渲染后的模板响应
        """
        if context is None:
            context = {}
            
        # 添加翻译文本到上下文
        translations = self._translations.get(lang, {})
        context.update({"trans": translations, "lang": lang})
        
        return self.templates.TemplateResponse(
            template_name, 
            {"request": request, **context}
        )
    
    def add_translation(self, lang: str, translations: Dict[str, str]):
        """
        添加或更新翻译文本
        
        Args:
            lang: 语言代码
            translations: 翻译字典
        """
        if lang not in self._translations:
            self._translations[lang] = {}
        self._translations[lang].update(translations)