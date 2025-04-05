from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pymilvus import connections, Collection, utility
from services.embedding_service import EmbeddingService
from utils.config import VectorDBProvider, MILVUS_CONFIG
import os
import json
from services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)

class SearchService:
    """
    搜索服务类，负责向量数据库的连接和向量搜索功能
    提供集合列表查询、向量相似度搜索和搜索结果保存等功能
    """
    def __init__(self):
        """
        初始化搜索服务
        创建嵌入服务实例，设置Milvus连接URI，初始化搜索结果保存目录
        """
        self.embedding_service = EmbeddingService()
        self.milvus_uri = MILVUS_CONFIG["uri"]
        self.search_results_dir = "04-search-results"
        os.makedirs(self.search_results_dir, exist_ok=True)
        self.vector_store_service = VectorStoreService()
        self.logger = logging.getLogger(__name__)

    def get_providers(self) -> List[Dict[str, str]]:
        """
        获取支持的向量数据库列表
        
        Returns:
            List[Dict[str, str]]: 支持的向量数据库提供商列表
        """
        return [
            {"id": VectorDBProvider.MILVUS.value, "name": "Milvus"}
        ]

    def list_collections(self, provider: str) -> List[Dict[str, Any]]:
        """
        列出指定提供商的所有集合
        """
        try:
            vector_store = VectorStoreService()
            return vector_store.list_collections(provider)
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []

    def save_search_results(self, query: str, collection_id: str, results: List[Dict[str, Any]]) -> str:
        """
        保存搜索结果到JSON文件
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 集合ID
            results (List[Dict[str, Any]]): 搜索结果列表
            
        Returns:
            str: 保存文件的路径
            
        Raises:
            Exception: 保存文件时发生错误
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # 使用集合ID的基础名称（去掉路径相关字符）
            collection_base = os.path.basename(collection_id)
            filename = f"search_{collection_base}_{timestamp}.json"
            filepath = os.path.join(self.search_results_dir, filename)
            
            search_data = {
                "query": query,
                "collection_id": collection_id,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            logger.info(f"Saving search results to: {filepath}")
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(search_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved search results to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving search results: {str(e)}")
            raise

    async def search(self, search_params: Dict) -> Dict:
        """执行向量搜索"""
        try:
            # 从 search_params 中获取参数
            query = search_params.get("query")
            collection_id = search_params.get("collection_id")
            top_k = search_params.get("top_k", 3)
            threshold = search_params.get("threshold", 0.7)
            word_count_threshold = search_params.get("word_count_threshold", 100)
            save_results = search_params.get("save_results", False)
            provider = search_params.get("provider", "milvus")

            self.logger.info("Search parameters:")
            self.logger.info(f"- Query: {query}")
            self.logger.info(f"- Collection ID: {collection_id}")
            self.logger.info(f"- Top K: {top_k}")
            self.logger.info(f"- Threshold: {threshold}")
            self.logger.info(f"- Word Count Threshold: {word_count_threshold}")
            self.logger.info(f"- Save Results: {save_results}")
            self.logger.info(f"- Provider: {provider}")

            # 直接调用向量存储服务进行搜索
            search_results = await self.vector_store_service.search(search_params)

            # 如果需要保存结果
            if save_results and search_results.get("results"):
                saved_filepath = self.save_search_results(
                    query, 
                    collection_id, 
                    search_results["results"]
                )
                search_results["saved_filepath"] = saved_filepath

            return search_results

        except Exception as e:
            self.logger.error(f"Error performing search: {str(e)}")
            raise

    async def _save_search_results(self, query: str, collection_id: str, results: List[Dict]) -> str:
        """保存搜索结果到文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # 使用集合ID的基础名称（去掉路径相关字符）
            collection_base = os.path.basename(collection_id)
            filename = f"search_{collection_base}_{timestamp}.json"
            filepath = os.path.join(self.search_results_dir, filename)
            
            search_data = {
                "query": query,
                "collection_id": collection_id,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            logger.info(f"Saving search results to: {filepath}")
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(search_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved search results to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving search results: {str(e)}")
            raise