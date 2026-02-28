"""
Catalog Service - manages product catalog (cakes and desserts).
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import CatalogCake


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_items_by_type(self, item_type: str, limit: Optional[int] = None) -> List[CatalogCake]:
        """Get catalog items by type (cake or dessert)"""
        query = select(CatalogCake).where(
            CatalogCake.type == item_type
        ).order_by(CatalogCake.title)
        
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_item_by_id(self, item_id: int) -> Optional[CatalogCake]:
        """Get catalog item by ID"""
        result = await self.session.execute(
            select(CatalogCake).where(CatalogCake.id == item_id)
        )
        return result.scalar_one_or_none()
    
    async def get_item_by_title(self, title: str) -> Optional[CatalogCake]:
        """Get catalog item by title (case-insensitive)"""
        result = await self.session.execute(
            select(CatalogCake).where(CatalogCake.title.ilike(f"%{title}%"))
        )
        return result.scalar_one_or_none()
    
    async def search_items(self, query: str, item_type: Optional[str] = None) -> List[CatalogCake]:
        """Search catalog items by query"""
        stmt = select(CatalogCake).where(
            CatalogCake.title.ilike(f"%{query}%")
        )
        
        if item_type:
            stmt = stmt.where(CatalogCake.type == item_type)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
