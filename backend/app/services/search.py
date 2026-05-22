from __future__ import annotations

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.core.config import settings

INDEX_NAME = "marketplace_products"

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
    return _client


class ElasticsearchService:
    index_name = INDEX_NAME

    @classmethod
    async def setup_index(cls, es_client: AsyncElasticsearch) -> None:
        exists = await es_client.indices.exists(index=cls.index_name)
        if exists:
            return
        await es_client.indices.create(
            index=cls.index_name,
            mappings={
                "properties": {
                    "title": {"type": "text", "analyzer": "standard"},
                    "description": {"type": "text", "analyzer": "standard"},
                    "tags": {"type": "keyword"},
                    "category_name": {"type": "keyword"},
                    "seller_name": {"type": "text"},
                    "price": {"type": "double"},
                    "stock": {"type": "integer"},
                    "status": {"type": "keyword"},
                    "rating": {"type": "float"},
                    "created_at": {"type": "date"},
                }
            },
        )

    @classmethod
    async def index_product(cls, es_client: AsyncElasticsearch, product) -> None:
        reviews = getattr(product, "reviews", []) or []
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0.0

        doc = {
            "id": str(product.id),
            "title": product.title,
            "description": product.description or "",
            "tags": product.tags or [],
            "category_name": product.category.name if product.category else "",
            "seller_name": product.seller.full_name if product.seller else "",
            "price": float(product.price),
            "stock": product.stock,
            "status": product.status,
            "rating": avg_rating,
            "created_at": product.created_at.isoformat() if product.created_at else None,
        }
        await es_client.index(index=cls.index_name, id=str(product.id), document=doc)

    @classmethod
    async def remove_product(cls, es_client: AsyncElasticsearch, product_id: str) -> None:
        try:
            await es_client.delete(index=cls.index_name, id=product_id)
        except NotFoundError:
            pass

    @classmethod
    async def search(
        cls,
        es_client: AsyncElasticsearch,
        q: str,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str = "newest",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict], int]:
        filters: list[dict] = [
            {"term": {"status": "active"}},
            {"range": {"stock": {"gt": 0}}},
        ]
        if category:
            filters.append({"term": {"category_name": category}})
        if min_price is not None or max_price is not None:
            price_range: dict = {}
            if min_price is not None:
                price_range["gte"] = min_price
            if max_price is not None:
                price_range["lte"] = max_price
            filters.append({"range": {"price": price_range}})

        sort_options: dict[str, list] = {
            "newest": [{"created_at": "desc"}],
            "price_asc": [{"price": "asc"}],
            "price_desc": [{"price": "desc"}],
            "rating": [{"rating": "desc"}],
        }
        sort_clause = sort_options.get(sort, [{"created_at": "desc"}])

        body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": q,
                                "fields": ["title^3", "description", "tags^2"],
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            "sort": sort_clause,
            "from": (page - 1) * per_page,
            "size": per_page,
        }
        response = await es_client.search(index=cls.index_name, body=body)
        hits = response["hits"]
        return [h["_source"] for h in hits["hits"]], hits["total"]["value"]


# Module-level helpers used by main.py lifespan
async def setup_index() -> None:
    await ElasticsearchService.setup_index(get_es_client())


async def close_es_client() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None
