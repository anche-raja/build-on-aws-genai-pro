"""
Phase 1 & 3: Amazon OpenSearch Service Manager
Handles vector database operations with hierarchical indexing
"""

import boto3
import requests
from requests_aws4auth import AWS4Auth
import json
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenSearchManager:
    """Manages Amazon OpenSearch Service for vector search"""
    
    def __init__(self, domain_endpoint: str, region: str = 'us-east-1'):
        """
        Initialize OpenSearch manager
        
        Args:
            domain_endpoint: OpenSearch domain endpoint URL
            region: AWS region
        """
        self.host = domain_endpoint
        self.region = region
        
        # Setup AWS authentication
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',
            session_token=credentials.token
        )
    
    def create_index(self, index_name: str, embedding_dimension: int = 1536) -> Dict:
        """
        Create an OpenSearch index with vector (KNN) support
        
        Args:
            index_name: Name of the index
            embedding_dimension: Dimension of embedding vectors
            
        Returns:
            Response from OpenSearch
        """
        url = f"{self.host}/{index_name}"
        
        index_mapping = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100,
                    "number_of_shards": 3,
                    "number_of_replicas": 2
                }
            },
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "parent_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "metadata": {
                        "properties": {
                            "author": {"type": "keyword"},
                            "created_date": {"type": "date"},
                            "last_updated": {"type": "date"},
                            "document_type": {"type": "keyword"},
                            "department": {"type": "keyword"},
                            "tags": {"type": "keyword"},
                            "source": {"type": "keyword"}
                        }
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": embedding_dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 16
                            }
                        }
                    },
                    "hierarchy": {
                        "type": "nested",
                        "properties": {
                            "level": {"type": "keyword"},
                            "path": {"type": "keyword"},
                            "position": {"type": "integer"}
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.put(
                url,
                auth=self.awsauth,
                json=index_mapping,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.info(f"Created index: {index_name}")
            return response.json()
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise
    
    def index_document(self, index_name: str, doc_id: str, document: Dict) -> Dict:
        """
        Index a document with embedding
        
        Args:
            index_name: Name of the index
            doc_id: Document ID
            document: Document to index (must include embedding)
            
        Returns:
            Response from OpenSearch
        """
        url = f"{self.host}/{index_name}/_doc/{doc_id}"
        
        try:
            response = requests.put(
                url,
                auth=self.awsauth,
                json=document,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            raise
    
    def bulk_index_documents(self, index_name: str, documents: List[Dict]) -> Dict:
        """
        Bulk index multiple documents
        
        Args:
            index_name: Name of the index
            documents: List of documents (each must have 'id' and document data)
            
        Returns:
            Response from OpenSearch
        """
        url = f"{self.host}/_bulk"
        
        # Build bulk request body
        bulk_data = []
        for doc in documents:
            doc_id = doc.pop('id')
            bulk_data.append(json.dumps({"index": {"_index": index_name, "_id": doc_id}}))
            bulk_data.append(json.dumps(doc))
        
        bulk_body = '\n'.join(bulk_data) + '\n'
        
        try:
            response = requests.post(
                url,
                auth=self.awsauth,
                data=bulk_body,
                headers={"Content-Type": "application/x-ndjson"}
            )
            response.raise_for_status()
            logger.info(f"Bulk indexed {len(documents)} documents")
            return response.json()
        except Exception as e:
            logger.error(f"Error bulk indexing: {str(e)}")
            raise
    
    def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        k: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Perform vector similarity search
        
        Args:
            index_name: Name of the index to search
            query_vector: Query embedding vector
            k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            Search results
        """
        url = f"{self.host}/{index_name}/_search"
        
        search_query = {
            "size": k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": k
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        # Add filters if provided
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {key: value}})
                else:
                    filter_clauses.append({"term": {key: value}})
            
            if filter_clauses:
                search_query["query"]["bool"]["filter"] = filter_clauses
        
        try:
            response = requests.post(
                url,
                auth=self.awsauth,
                json=search_query,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error performing vector search: {str(e)}")
            raise
    
    def hybrid_search(
        self,
        index_name: str,
        query_text: str,
        query_vector: List[float],
        k: int = 10,
        text_weight: float = 0.3,
        vector_weight: float = 0.7
    ) -> Dict:
        """
        Perform hybrid search combining keyword and vector search
        
        Args:
            index_name: Name of the index
            query_text: Text query for keyword search
            query_vector: Query embedding for vector search
            k: Number of results
            text_weight: Weight for text search score
            vector_weight: Weight for vector search score
            
        Returns:
            Combined search results
        """
        url = f"{self.host}/{index_name}/_search"
        
        search_query = {
            "size": k,
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "match": {
                                "content": {
                                    "query": query_text,
                                    "boost": text_weight
                                }
                            }
                        },
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": k,
                                    "boost": vector_weight
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        try:
            response = requests.post(
                url,
                auth=self.awsauth,
                json=search_query,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error performing hybrid search: {str(e)}")
            raise
    
    def multi_index_search(
        self,
        indices: List[str],
        query_vector: List[float],
        k: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Search across multiple indices
        
        Args:
            indices: List of index names
            query_vector: Query embedding vector
            k: Number of results per index
            filters: Optional metadata filters
            
        Returns:
            Combined search results from all indices
        """
        url = f"{self.host}/{','.join(indices)}/_search"
        
        search_query = {
            "size": k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": k
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                filter_clauses.append({"term": {key: value}})
            
            if filter_clauses:
                search_query["query"]["bool"]["filter"] = filter_clauses
        
        try:
            response = requests.post(
                url,
                auth=self.awsauth,
                json=search_query,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error performing multi-index search: {str(e)}")
            raise
    
    def delete_index(self, index_name: str) -> Dict:
        """
        Delete an index
        
        Args:
            index_name: Name of the index to delete
            
        Returns:
            Response from OpenSearch
        """
        url = f"{self.host}/{index_name}"
        
        try:
            response = requests.delete(url, auth=self.awsauth)
            response.raise_for_status()
            logger.info(f"Deleted index: {index_name}")
            return response.json()
        except Exception as e:
            logger.error(f"Error deleting index: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage (requires actual OpenSearch endpoint)
    # manager = OpenSearchManager("https://your-domain.us-east-1.es.amazonaws.com")
    # manager.create_index("technical_docs")
    print("OpenSearch Manager initialized")





