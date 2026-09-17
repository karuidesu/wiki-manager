import abc
from typing import List, Optional

from app.models import Article, ArticleReaction, Comment


class IArticle(abc.ABC):
    @abc.abstractmethod
    async def create_article(self, article: Article) -> Article:
        pass

    @abc.abstractmethod
    async def update_article(self, article: Article) -> Article:
        pass

    @abc.abstractmethod
    async def get_article(self, article_id: str) -> Optional[Article]:
        pass

    @abc.abstractmethod
    async def get_article_by_title(self, title: str) -> Optional[Article]:
        pass

    @abc.abstractmethod
    async def get_all_articles(
        self, page_index: int, max_result: int, direction: str
    ) -> List[Article]:
        pass

    @abc.abstractmethod
    async def count_articles(self) -> int:
        pass

    @abc.abstractmethod
    async def delete_article(self, article_id: str):
        pass

    @abc.abstractmethod
    async def get_reaction(
        self, article_id: str, user_id: str
    ) -> Optional[ArticleReaction]:
        pass

    @abc.abstractmethod
    async def save_reaction(
        self,
        reaction: ArticleReaction,
        like: int = 0,
        dislike: int = 0,
        is_update: bool = False,
    ) -> ArticleReaction:
        pass

    @abc.abstractmethod
    async def cancel_reaction(
        self, reaction: ArticleReaction, like: int, dislike: int
    ) -> None:
        pass

    @abc.abstractmethod
    async def load_reactions(
        self, article_id: str, page_index: int, max_result: int, direction: str
    ) -> List[ArticleReaction]:
        pass

    @abc.abstractmethod
    async def count_reactions(self, article_id: str) -> int:
        pass

    @abc.abstractmethod
    async def add_comment(self, comment: Comment) -> Comment:
        pass

    @abc.abstractmethod
    async def get_comment(self, comment_id: str) -> Optional[Comment]:
        pass

    @abc.abstractmethod
    async def update_comment(self, comment: Comment) -> Comment:
        pass

    @abc.abstractmethod
    async def load_comments(
        self, article_id: str, page_index: int, max_result: int, direction: str
    ) -> List[Comment]:
        pass

    @abc.abstractmethod
    async def count_comments(self, article_id: str) -> int:
        pass
