import uuid

class MemberService:
    @staticmethod
    def generate_member_id() -> str:
        return str(uuid.uuid4())
    
    @staticmethod
    def validate_member_id(member_id: str) -> bool:
        try:
            uuid.UUID(member_id, version=4)
            return True
        except ValueError:
            return False