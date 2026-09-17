from abc import ABC, abstractmethod


class ICategory(ABC):
    @abstractmethod
    async def create_category(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_category(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_category_by_title(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_categories_by_ids(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def list_categories(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def update_category(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def delete_category(self, *args, **kwargs):
        raise NotImplementedError
