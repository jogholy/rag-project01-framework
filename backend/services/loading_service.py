from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf
import pdfplumber
import fitz  # PyMuPDF
import logging
import os
from datetime import datetime
import json
import pandas as pd
from langchain_community.document_loaders import TextLoader, JSONLoader, WebBaseLoader
from langchain_community.document_loaders import CSVLoader
from langchain_community.document_loaders import UnstructuredMarkdownLoader, UnstructuredImageLoader
from unstructured.partition.ppt import partition_ppt

logger = logging.getLogger(__name__)
"""
PDF文档加载服务类
    这个服务类提供了多种PDF文档加载方法，支持不同的加载策略和分块选项。
    主要功能：
    1. 支持多种PDF解析库：
        - PyMuPDF (fitz): 适合快速处理大量PDF文件，性能最佳
        - PyPDF: 适合简单的PDF文本提取，依赖较少
        - pdfplumber: 适合需要处理表格或需要文本位置信息的场景
        - unstructured: 适合需要更好的文档结构识别和灵活分块策略的场景
    
    2. 文档加载特性：
        - 保持页码信息
        - 支持文本分块
        - 提供元数据存储
        - 支持不同的加载策略（使用unstructured时）
 """
class LoadingService:
    """
    PDF文档加载服务类，提供多种PDF文档加载和处理方法。
    
    属性:
        total_pages (int): 当前加载PDF文档的总页数
        current_page_map (list): 存储当前文档的页面映射信息，每个元素包含页面文本和页码
    """
    
    def __init__(self):
        self.total_pages = 0
        self.current_page_map = []
    
    def load_file(self, file_path: str, loading_type: str, loading_method: str, strategy: str = None, chunking_strategy: str = None, chunking_options: dict = None) -> str:
        """
        加载文件的主方法，支持多种文件类型和加载策略。

        参数:
            file_path (str): 文件路径
            loading_type (str): 文件类型 ('simple_text', 'structured_text', 'image', 'pdf', 'table')
            loading_method (str): 加载方法
            strategy (str, optional): 使用unstructured方法时的策略
            chunking_strategy (str, optional): 文本分块策略
            chunking_options (dict, optional): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            if loading_type == 'pdf':
                return self._load_pdf(file_path, loading_method, strategy, chunking_strategy, chunking_options)
            # elif loading_type == 'simple_text':
            #     return self._load_simple_text(file_path, loading_method)
            elif loading_type == 'structured_text':
                return self._load_structured_text(file_path, loading_method)
            elif loading_type == 'image':
                return self._load_image(file_path, loading_method)
            elif loading_type == 'table':
                return self._load_table(file_path, loading_method)
            else:
                raise ValueError(f"Unsupported loading type: {loading_type}")
        except Exception as e:
            logger.error(f"Error loading file with {loading_method}: {str(e)}")
            raise

    def _load_other_file(self, file_path: str, loading_method: str) -> dict:
        """加载简单文本文件，返回标准化的文档格式"""
        try:
            if loading_method == 'textloader':
                loader = TextLoader(file_path)
            elif loading_method == 'jsonloader':
                loader = JSONLoader(file_path, 
                                    jq_schema='.main_characters[] | select(has("abilities")) | "姓名：" + .name + "，角色：" + .role + "，技能：" + (.abilities | join(", "))', 
                                    text_content=True)
            else:
                raise ValueError(f"Unsupported loading method for simple text: {loading_method}")

            documents = loader.load()
            content = "\n".join(doc.page_content for doc in documents)
            
            # 创建标准化的chunks格式
            chunks = [{
                "content": content,
                "metadata": {
                    "chunk_id": 1,
                    "page_number": 1,
                    "page_range": "1",
                    "word_count": len(content.split())
                }
            }]
            
            # 返回标准化的文档格式
            return {
                "filename": os.path.basename(file_path),
                "total_chunks": 1,
                "total_pages": 1,
                "loading_method": loading_method,
                "loading_strategy": None,
                "chunking_strategy": None,
                "chunking_method": "loaded",
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks
            }
        except Exception as e:
            logger.error(f"Error loading simple text: {str(e)}")
            raise

    def _load_structured_text(self, file_path: str, loading_method: str) -> str:
        """加载结构化文本文件"""
        try:
            if loading_method == 'jsonloader':
                loader = JSONLoader(file_path, 
                                    jq_schema='.main_characters[] | select(has("abilities")) | "姓名：" + .name + "，角色：" + .role + "，技能：" + (.abilities | join(", "))', 
                                    text_content=True)
            elif loading_method == 'webbaseloader':
                loader = WebBaseLoader(file_path)
            elif loading_method == 'markdownloader':
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                raise ValueError(f"Unsupported loading method for structured text: {loading_method}")
            
            documents = loader.load()

            print(documents)
            content = "\n".join(doc.page_content for doc in documents)
                
            # 创建标准化的chunks格式
            chunks = [{
                "content": content,
                "metadata": {
                    "chunk_id": 1,
                    "page_number": 1,
                    "page_range": "1",
                    "word_count": len(content.split())
                }
            }]
            
            print(chunks)

            # 返回标准化的文档格式
            return {
                "filename": os.path.basename(file_path),
                "total_chunks": 1,
                "total_pages": 1,
                "loading_method": loading_method,
                "loading_strategy": None,
                "chunking_strategy": None,
                "chunking_method": "loaded",
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks
            }
                
            # return "\n".join(doc.page_content for doc in documents)
        except Exception as e:
            logger.error(f"Error loading structured text: {str(e)}")
            raise

    def _load_image(self, file_path: str, loading_method: str) -> str:
        """加载图片文件"""
        try:
            if loading_method == 'imageloader':
                loader = UnstructuredImageLoader(file_path)
            elif loading_method == 'pptloader':
                loader = partition_ppt(file_path)
            else:
                raise ValueError(f"Unsupported loading method for image: {loading_method}")
            
            documents = loader.load()
            return "\n".join(doc.page_content for doc in documents)
        except Exception as e:
            logger.error(f"Error loading image: {str(e)}")
            raise

    def _load_table(self, file_path: str, loading_method: str) -> str:
        """加载表格文件"""
        try:
            if loading_method == 'csvloader':
                loader = CSVLoader(file_path)
            elif loading_method == 'databaseloader':
                pass # loader = DatabaseLoader(file_path)
            else:
                raise ValueError(f"Unsupported loading method for table: {loading_method}")
            
            documents = loader.load()
            return "\n".join(doc.page_content for doc in documents)
        except Exception as e:
            logger.error(f"Error loading table: {str(e)}")
            raise

    def _load_pdf(self, file_path: str, method: str, strategy: str = None, chunking_strategy: str = None, chunking_options: dict = None) -> str:
        """
        加载PDF文档的主方法，支持多种加载策略。

        参数:
            file_path (str): PDF文件路径
            method (str): 加载方法，支持 'pymupdf', 'pypdf', 'pdfplumber', 'unstructured'
            strategy (str, optional): 使用unstructured方法时的策略，可选 'fast', 'hi_res', 'ocr_only'
            chunking_strategy (str, optional): 文本分块策略，可选 'basic', 'by_title'
            chunking_options (dict, optional): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            if method == "pymupdf":
                return self._load_with_pymupdf(file_path)
            elif method == "pypdf":
                return self._load_with_pypdf(file_path)
            elif method == "pdfplumber":
                return self._load_with_pdfplumber(file_path)
            elif method == "unstructured":
                return self._load_with_unstructured(
                    file_path, 
                    strategy=strategy,
                    chunking_strategy=chunking_strategy,
                    chunking_options=chunking_options
                )
            else:
                raise ValueError(f"Unsupported loading method for PDF: {method}")
        except Exception as e:
            logger.error(f"Error loading PDF with {method}: {str(e)}")
            raise
    
    def get_total_pages(self) -> int:
        """
        获取当前加载文档的总页数。

        返回:
            int: 文档总页数
        """
        return max(page_data['page'] for page_data in self.current_page_map) if self.current_page_map else 0
    
    def get_page_map(self) -> list:
        """
        获取当前文档的页面映射信息。

        返回:
            list: 包含每页文本内容和页码的列表
        """
        return self.current_page_map
    
    def _load_with_pymupdf(self, file_path: str) -> str:
        """
        使用PyMuPDF库加载PDF文档。
        适合快速处理大量PDF文件，性能最佳。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        text_blocks = []
        try:
            with fitz.open(file_path) as doc:
                self.total_pages = len(doc)
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text("text")
                    if text.strip():
                        text_blocks.append({
                            "text": text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"PyMuPDF error: {str(e)}")
            raise
    
    def _load_with_pypdf(self, file_path: str) -> str:
        """
        使用PyPDF库加载PDF文档。
        适合简单的PDF文本提取，依赖较少。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        try:
            text_blocks = []
            with open(file_path, "rb") as file:
                pdf = PdfReader(file)
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"PyPDF error: {str(e)}")
            raise
    
    def _load_with_unstructured(self, file_path: str, strategy: str = "fast", chunking_strategy: str = "basic", chunking_options: dict = None) -> str:
        """
        使用unstructured库加载PDF文档。
        适合需要更好的文档结构识别和灵活分块策略的场景。

        参数:
            file_path (str): PDF文件路径
            strategy (str): 加载策略，默认'fast'
            chunking_strategy (str): 分块策略，默认'basic'
            chunking_options (dict): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            strategy_params = {
                "fast": {"strategy": "fast"},
                "hi_res": {"strategy": "hi_res"},
                "ocr_only": {"strategy": "ocr_only"}
            }            
         
            # Prepare chunking parameters based on strategy
            chunking_params = {}
            if chunking_strategy == "basic":
                chunking_params = {
                    "max_characters": chunking_options.get("maxCharacters", 4000),
                    "new_after_n_chars": chunking_options.get("newAfterNChars", 3000),
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "overlap": chunking_options.get("overlap", 200),
                    "overlap_all": chunking_options.get("overlapAll", False)
                }
            elif chunking_strategy == "by_title":
                chunking_params = {
                    "chunking_strategy": "by_title",
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "multipage_sections": chunking_options.get("multiPageSections", False)
                }
            
            # Combine strategy parameters with chunking parameters
            params = {**strategy_params.get(strategy, {"strategy": "fast"}), **chunking_params}
            
            elements = partition_pdf(file_path, **params)
            
            # Add debug logging
            for elem in elements:
                logger.debug(f"Element type: {type(elem)}")
                logger.debug(f"Element content: {str(elem)}")
                logger.debug(f"Element dir: {dir(elem)}")
            
            text_blocks = []
            pages = set()
            
            for elem in elements:
                metadata = elem.metadata.__dict__
                page_number = metadata.get('page_number')
                
                if page_number is not None:
                    pages.add(page_number)
                    
                    # Convert element to a serializable format
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if key == '_known_field_names':
                            continue
                        
                        try:
                            # Try JSON serialization to test if value is serializable
                            json.dumps({key: value})
                            cleaned_metadata[key] = value
                        except (TypeError, OverflowError):
                            # If not serializable, convert to string
                            cleaned_metadata[key] = str(value)
                    
                    # Add additional element information
                    cleaned_metadata['element_type'] = elem.__class__.__name__
                    cleaned_metadata['id'] = str(getattr(elem, 'id', None))
                    cleaned_metadata['category'] = str(getattr(elem, 'category', None))
                    
                    text_blocks.append({
                        "text": str(elem),
                        "page": page_number,
                        "metadata": cleaned_metadata
                    })
            
            self.total_pages = max(pages) if pages else 0
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"Unstructured error: {str(e)}")
            raise
    
    def _load_with_pdfplumber(self, file_path: str) -> str:
        """
        使用pdfplumber库加载PDF文档。
        适合需要处理表格或需要文本位置信息的场景。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        text_blocks = []
        try:
            with pdfplumber.open(file_path) as pdf:
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"pdfplumber error: {str(e)}")
            raise
    
    def save_document(self, filename: str, content: dict, loading_method: str, strategy: str = None, chunking_strategy: str = None) -> str:
        """
        保存处理后的文档数据。

        参数:
            filename (str): 原文件名
            content (dict): 文档内容和元数据
            loading_method (str): 使用的加载方法
            strategy (str, optional): 使用的加载策略
            chunking_strategy (str, optional): 使用的分块策略

        返回:
            str: 保存的文件路径
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            base_name = os.path.splitext(filename)[0]
            
            # 构建文档名称
            if loading_method == "unstructured" and strategy:
                doc_name = f"{base_name}_{loading_method}_{strategy}_{chunking_strategy}_{timestamp}"
            else:
                doc_name = f"{base_name}_{loading_method}_{timestamp}"
            
            # 保存到文件
            filepath = os.path.join("01-loaded-docs", f"{doc_name}.json")
            os.makedirs("01-loaded-docs", exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise
