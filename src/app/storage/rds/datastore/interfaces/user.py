import abc
from typing import Any, Dict, List, Optional


class IUser(abc.ABC):
    @abc.abstractmethod
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def get_users(self, page_index: int, max_result: int) -> List[Dict[str, Any]]:
        pass
