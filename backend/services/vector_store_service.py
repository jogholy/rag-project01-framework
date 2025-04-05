import os
from datetime import datetime
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
from pymilvus import connections, utility
from pymilvus import Collection, DataType, FieldSchema, CollectionSchema
import chromadb
from chromadb.config import Settings
from utils.config import VectorDBProvider, MILVUS_CONFIG  # Updated import
import warnings
import sys
import re

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 忽略 pydantic 的警告
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

class VectorDBConfig:
    """
    向量数据库配置类，用于存储和管理向量数据库的配置信息
    """
    def __init__(self, provider: str, index_mode: str):
        """
        初始化向量数据库配置
        
        参数:
            provider: 向量数据库提供商名称
            index_mode: 索引模式
        """
        self.provider = provider
        self.index_mode = index_mode
        self.milvus_uri = MILVUS_CONFIG["uri"]
        # 修改 Chroma 配置路径
        self.chroma_persist_directory = os.path.join("03-vector-store", "chroma_db")

    def _get_milvus_index_type(self, index_mode: str) -> str:
        """
        根据索引模式获取Milvus索引类型
        
        参数:
            index_mode: 索引模式
            
        返回:
            对应的Milvus索引类型
        """
        return MILVUS_CONFIG["index_types"].get(index_mode, "FLAT")
    
    def _get_milvus_index_params(self, index_mode: str) -> Dict[str, Any]:
        """
        根据索引模式获取Milvus索引参数
        
        参数:
            index_mode: 索引模式
            
        返回:
            对应的Milvus索引参数字典
        """
        return MILVUS_CONFIG["index_params"].get(index_mode, {})

class VectorStoreService:
    """
    向量存储服务类，提供向量数据的索引、查询和管理功能
    """
    def __init__(self):
        """
        初始化向量存储服务
        """
        self.initialized_dbs = {}
        # 确保存储目录存在
        os.makedirs("03-vector-store", exist_ok=True)
        
        # 修改 Chroma 客户端初始化
        try:
            chroma_persist_dir = os.path.join("03-vector-store", "chroma_db")
            os.makedirs(chroma_persist_dir, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(
                path=chroma_persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info("Successfully initialized Chroma client")
        except Exception as e:
            logger.error(f"Error initializing Chroma client: {str(e)}")
            self.chroma_client = None
    
    def _get_milvus_index_type(self, config: VectorDBConfig) -> str:
        """
        从配置对象获取Milvus索引类型
        
        参数:
            config: 向量数据库配置对象
            
        返回:
            Milvus索引类型
        """
        return config._get_milvus_index_type(config.index_mode)
    
    def _get_milvus_index_params(self, config: VectorDBConfig) -> Dict[str, Any]:
        """
        从配置对象获取Milvus索引参数
        
        参数:
            config: 向量数据库配置对象
            
        返回:
            Milvus索引参数字典
        """
        return config._get_milvus_index_params(config.index_mode)
    
    def index_embeddings(self, embedding_file: str, config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到向量数据库
        
        参数:
            embedding_file: 嵌入向量文件路径
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        start_time = datetime.now()
        
        try:
            # 读取embedding文件
            embeddings_data = self._load_embeddings(embedding_file)
            
            # 根据不同的数据库进行索引
            if config.provider.lower() == "milvus":  # 使用字符串比较而不是枚举
                result = self._index_to_milvus(embeddings_data, config)
            elif config.provider.lower() == "chroma":  # 使用字符串比较而不是枚举
                result = self._index_to_chroma(embeddings_data, config)
            else:
                raise ValueError(f"Unsupported vector database provider: {config.provider}")
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                "database": config.provider,
                "index_mode": config.index_mode,
                "total_vectors": len(embeddings_data["embeddings"]),
                "index_size": result.get("index_size", "N/A"),
                "processing_time": processing_time,
                "collection_name": result.get("collection_name", "N/A")
            }
        except Exception as e:
            logger.exception(f"Error in index_embeddings: {str(e)}")
            raise
    
    def _load_embeddings(self, file_path: str) -> Dict[str, Any]:
        """
        加载embedding文件，返回配置信息和embeddings
        
        参数:
            file_path: 嵌入向量文件路径
            
        返回:
            包含嵌入向量和元数据的字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loading embeddings from {file_path}")
                
                if not isinstance(data, dict) or "embeddings" not in data:
                    raise ValueError("Invalid embedding file format: missing 'embeddings' key")
                    
                # 返回完整的数据，包括顶层配置
                logger.info(f"Found {len(data['embeddings'])} embeddings")
                return data
                
        except Exception as e:
            logger.error(f"Error loading embeddings from {file_path}: {str(e)}")
            raise
    
    def _index_to_milvus(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到Milvus数据库
        
        参数:
            embeddings_data: 嵌入向量数据
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        try:
            # 使用 filename 作为 collection 名称前缀
            filename = embeddings_data.get("filename", "")
            # 如果有 .pdf 后缀，移除它
            base_name = filename.replace('.pdf', '') if filename else "doc"
            
            # Ensure the collection name starts with a letter or underscore
            if not base_name[0].isalpha() and base_name[0] != '_':
                base_name = f"_{base_name}"
            
            # Get embedding provider
            embedding_provider = embeddings_data.get("embedding_provider", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            collection_name = f"{base_name}_{embedding_provider}_{timestamp}"
            
            # 连接到Milvus
            connections.connect(
                alias="default", 
                uri=config.milvus_uri
            )
            
            # 从顶层配置获取向量维度
            vector_dim = int(embeddings_data.get("vector_dimension"))
            if not vector_dim:
                raise ValueError("Missing vector_dimension in embedding file")
            
            logger.info(f"Creating collection with dimension: {vector_dim}")
            
            # 定义字段
            fields = [
                {"name": "id", "dtype": "INT64", "is_primary": True, "auto_id": True},
                {"name": "content", "dtype": "VARCHAR", "max_length": 5000},
                {"name": "document_name", "dtype": "VARCHAR", "max_length": 255},
                {"name": "chunk_id", "dtype": "INT64"},
                {"name": "total_chunks", "dtype": "INT64"},
                {"name": "word_count", "dtype": "INT64"},
                {"name": "page_number", "dtype": "VARCHAR", "max_length": 10},
                {"name": "page_range", "dtype": "VARCHAR", "max_length": 10},
                # {"name": "chunking_method", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_provider", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_model", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_timestamp", "dtype": "VARCHAR", "max_length": 50},
                {
                    "name": "vector",
                    "dtype": "FLOAT_VECTOR",
                    "dim": vector_dim,
                    "params": self._get_milvus_index_params(config)
                }
            ]
            
            # 准备数据为列表格式
            entities = []
            for emb in embeddings_data["embeddings"]:
                entity = {
                    "content": str(emb["metadata"].get("content", "")),
                    "document_name": embeddings_data.get("filename", ""),  # 使用 filename 而不是 document_name
                    "chunk_id": int(emb["metadata"].get("chunk_id", 0)),
                    "total_chunks": int(emb["metadata"].get("total_chunks", 0)),
                    "word_count": int(emb["metadata"].get("word_count", 0)),
                    "page_number": str(emb["metadata"].get("page_number", 0)),
                    "page_range": str(emb["metadata"].get("page_range", "")),
                    # "chunking_method": str(emb["metadata"].get("chunking_method", "")),
                    "embedding_provider": embeddings_data.get("embedding_provider", ""),  # 从顶层配置获取
                    "embedding_model": embeddings_data.get("embedding_model", ""),  # 从顶层配置获取
                    "embedding_timestamp": str(emb["metadata"].get("embedding_timestamp", "")),
                    "vector": [float(x) for x in emb.get("embedding", [])]
                }
                entities.append(entity)
            
            logger.info(f"Creating Milvus collection: {collection_name}")
            
            # 创建collection
            # field_schemas = [
            #     FieldSchema(name=field["name"], 
            #                dtype=getattr(DataType, field["dtype"]),
            #                is_primary="is_primary" in field and field["is_primary"],
            #                auto_id="auto_id" in field and field["auto_id"],
            #                max_length=field.get("max_length"),
            #                dim=field.get("dim"),
            #                params=field.get("params"))
            #     for field in fields
            # ]

            field_schemas = []
            for field in fields:
                extra_params = {}
                if field.get('max_length') is not None:
                    extra_params['max_length'] = field['max_length']
                if field.get('dim') is not None:
                    extra_params['dim'] = field['dim']
                if field.get('params') is not None:
                    extra_params['params'] = field['params']
                field_schema = FieldSchema(
                    name=field["name"], 
                    dtype=getattr(DataType, field["dtype"]),
                    is_primary=field.get("is_primary", False),
                    auto_id=field.get("auto_id", False),
                    **extra_params
                )
                field_schemas.append(field_schema)

            schema = CollectionSchema(fields=field_schemas, description=f"Collection for {collection_name}")
            collection = Collection(name=collection_name, schema=schema)
            
            # 插入数据
            logger.info(f"Inserting {len(entities)} vectors")
            insert_result = collection.insert(entities)
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": self._get_milvus_index_type(config),
                "params": self._get_milvus_index_params(config)
            }
            collection.create_index(field_name="vector", index_params=index_params)
            collection.load()
            
            return {
                "index_size": len(insert_result.primary_keys),
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Error indexing to Milvus: {str(e)}")
            raise
        
        finally:
            connections.disconnect("default")

    def _index_to_chroma(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到 Chroma 数据库
        """
        if self.chroma_client is None:
            logger.error("Chroma client not initialized")
            raise RuntimeError("Chroma client not initialized")

        try:
            # 处理文件名，移除中文字符和其他非法字符
            filename = embeddings_data.get("filename", "")
            # 移除 .pdf 后缀
            base_name = filename.replace('.pdf', '')
            
            # 将中文文件名转换为拼音或仅保留英文数字
            # 只保留字母、数字、下划线和连字符
            safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '', base_name)
            
            # 如果处理后的名称为空，使用默认名称
            if not safe_name:
                safe_name = "doc"
            
            # 确保名称以字母开头
            if not safe_name[0].isalpha():
                safe_name = "doc_" + safe_name
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            collection_name = f"{safe_name}_{timestamp}"
            
            # 确保集合名称长度不超过63个字符
            if len(collection_name) > 63:
                collection_name = collection_name[:59] + timestamp[-4:]

            logger.info(f"Creating collection with name: {collection_name}")

            # 检查并打印第一个嵌入向量的信息
            first_emb = embeddings_data["embeddings"][0]
            logger.info(f"First embedding type: {type(first_emb['embedding'])}")
            logger.info(f"First embedding sample: {str(first_emb['embedding'][:5])}")
            logger.info(f"First embedding metadata: {first_emb['metadata']}")

            # 获取向量维度
            vector = self._process_single_embedding(first_emb)
            vector_dim = len(vector)
            logger.info(f"Vector dimension: {vector_dim}")

            # 创建新集合，指定维度
            try:
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=None,  # 使用原始向量
                    metadata={"dimension": vector_dim}
                )
                logger.info("Collection created successfully")
            except Exception as e:
                logger.exception("Failed to create collection")
                raise

            # 分批处理数据
            batch_size = 100
            total_processed = 0

            try:
                for i in range(0, len(embeddings_data["embeddings"]), batch_size):
                    batch = embeddings_data["embeddings"][i:i + batch_size]
                    
                    # 准备批次数据
                    batch_ids = [str(i + idx) for idx in range(len(batch))]
                    batch_embeddings = [self._process_single_embedding(emb) for emb in batch]
                    batch_metadatas = [{
                        "document_name": str(embeddings_data.get("filename", "")),
                        "chunk_id": str(emb["metadata"].get("chunk_id", 0)),
                        "content": str(emb["metadata"].get("content", ""))[:500]  # 限制内容长度
                    } for emb in batch]
                    batch_documents = [str(emb["metadata"].get("content", ""))[:500] for emb in batch]  # 限制内容长度

                    # 添加批次数据
                    collection.add(
                        ids=batch_ids,
                        embeddings=batch_embeddings,
                        metadatas=batch_metadatas,
                        documents=batch_documents
                    )
                    
                    total_processed += len(batch)
                    logger.info(f"Processed {total_processed}/{len(embeddings_data['embeddings'])} vectors")

                return {
                    "index_size": total_processed,
                    "collection_name": collection_name
                }

            except Exception as e:
                logger.exception("Error processing vectors")
                logger.error(f"Last batch info - size: {len(batch_embeddings)}, vector_dim: {len(batch_embeddings[0])}")
                raise

        except Exception as e:
            logger.exception("Error in _index_to_chroma")
            raise RuntimeError(f"Failed to index to Chroma: {str(e)}")

    def _process_single_embedding(self, emb: Dict) -> List[float]:
        """
        处理单个嵌入向量，确保返回浮点数列表
        """
        try:
            embedding = emb.get("embedding")
            if embedding is None:
                raise ValueError("Missing 'embedding' key in vector data")

            if isinstance(embedding, list):
                return [float(x) for x in embedding]
            elif isinstance(embedding, str):
                try:
                    vector = json.loads(embedding)
                    return [float(x) for x in vector]
                except json.JSONDecodeError:
                    vector = [float(x) for x in embedding.split()]
                    return vector
            else:
                raise ValueError(f"Unsupported embedding type: {type(embedding)}")
        except Exception as e:
            logger.exception(f"Error processing embedding")
            logger.error(f"Embedding data: {emb}")
            raise

    def list_collections(self, provider: str) -> List[Dict[str, Any]]:
        """
        列出指定提供商的所有集合
        """
        try:
            logger.info(f"Listing collections for provider: {provider}")
            
            if provider.lower() == "chroma":
                if self.chroma_client is None:
                    logger.error("Chroma client not initialized")
                    return []
                
                try:
                    collections = self.chroma_client.list_collections()
                    logger.info(f"Found {len(collections)} collections in Chroma")
                    
                    # 返回格式化的集合列表
                    result = [
                        {
                            "id": collection.name,
                            "name": collection.name,
                            "count": collection.count()
                        }
                        for collection in collections
                    ]
                    logger.info(f"Formatted Chroma collections: {result}")
                    return result
                    
                except Exception as e:
                    logger.error(f"Error getting Chroma collections: {str(e)}")
                    return []
                    
            elif provider.lower() == "milvus":
                # Windows 系统下不支持 Milvus
                if sys.platform.startswith('win'):
                    logger.warning("Milvus is not supported on Windows")
                    return []
                    
                try:
                    from pymilvus import connections, utility, Collection
                    connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                    collections = utility.list_collections()
                    return [{"id": name, "name": name, "count": Collection(name).num_entities} for name in collections]
                except ImportError:
                    logger.warning("Milvus is not installed")
                    return []
                except Exception as e:
                    logger.error(f"Error getting Milvus collections: {str(e)}")
                    return []
                finally:
                    try:
                        connections.disconnect("default")
                    except:
                        pass
                    
            logger.warning(f"Unsupported provider: {provider}")
            return []
            
        except Exception as e:
            logger.exception(f"Error listing collections for {provider}")
            return []

    def delete_collection(self, provider: str, collection_name: str) -> bool:
        """
        删除指定的集合
        
        参数:
            provider: 向量数据库提供商
            collection_name: 集合名称
            
        返回:
            是否删除成功
        """
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                utility.drop_collection(collection_name)
                return True
            finally:
                connections.disconnect("default")
        elif provider == VectorDBProvider.CHROMA:
            try:
                self.chroma_client.delete_collection(collection_name)
                return True
            except Exception as e:
                logger.error(f"Error deleting Chroma collection: {str(e)}")
                return False
        return False

    def get_collection_info(self, provider: str, collection_name: str) -> Dict[str, Any]:
        """
        获取指定集合的信息
        
        参数:
            provider: 向量数据库提供商
            collection_name: 集合名称
            
        返回:
            集合信息字典
        """
        if provider == VectorDBProvider.MILVUS:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                collection = Collection(collection_name)
                return {
                    "name": collection_name,
                    "num_entities": collection.num_entities,
                    "schema": collection.schema.to_dict()
                }
            finally:
                connections.disconnect("default")
        elif provider == VectorDBProvider.CHROMA:
            try:
                collection = self.chroma_client.get_collection(collection_name)
                return {
                    "name": collection_name,
                    "num_entities": collection.count(),
                    "schema": {
                        "fields": [
                            {"name": "vector", "index_params": {"index_type": "hnsw"}}
                        ]
                    }
                }
            except Exception as e:
                logger.error(f"Error getting Chroma collection info: {str(e)}")
                return {}
        return {}